#!/bin/bash
# srv01 post-install: updates, Docker Engine (official repo), UFW + DOCKER-USER, auditd, rsyslog, fail2ban, SSH hardening.
# Run as: ssh -i ~/.ssh/projet_cloud_ed25519 sysadmin@192.168.20.10 'sudo bash -s' < 10_ubuntu_harden.sh
# SSH password auth is disabled at the end ONLY because this script is itself running over a key-authenticated session.
set -euo pipefail
exec > >(tee -a /var/log/lab-harden.log) 2>&1
echo "=== lab hardening $(date -Is)"
export DEBIAN_FRONTEND=noninteractive

# ---- 1. APT updates (25.04 EOL since 01/2026; packages still served by archive.ubuntu.com)
apt-get update -q
apt-get -y -q full-upgrade
apt-get -y -q install ufw auditd audispd-plugins rsyslog fail2ban ca-certificates curl gnupg unattended-upgrades

# ---- 2. Docker Engine + Compose plugin from the official Docker repository
install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
chmod a+r /etc/apt/keyrings/docker.asc
. /etc/os-release
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu ${VERSION_CODENAME} stable" \
  > /etc/apt/sources.list.d/docker.list
apt-get update -q
apt-get -y -q install docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
cat > /etc/docker/daemon.json <<'EOF'
{ "log-driver": "json-file", "log-opts": {"max-size": "10m", "max-file": "3"},
  "live-restore": true, "userland-proxy": false, "no-new-privileges": true }
EOF
systemctl enable --now docker && systemctl restart docker

# ---- 3. UFW host firewall (default deny) + DOCKER-USER (published ports bypass UFW's INPUT chain)
ufw --force reset
ufw default deny incoming
ufw default allow outgoing
ufw allow from 192.168.99.0/24 to any port 22 proto tcp comment 'SSH from MGMT'
ufw allow from 10.8.0.0/24 to any port 22 proto tcp comment 'SSH from VPN'
ufw allow from 172.16.0.0/12 to any port 9100 proto tcp comment 'node_exporter from docker'
ufw allow from 172.16.0.0/12 to any port 8080 proto tcp comment 'blackbox/prometheus -> app'
ufw logging medium
if ! grep -q 'LAB DOCKER-USER' /etc/ufw/after.rules; then
cat >> /etc/ufw/after.rules <<'EOF'
# LAB DOCKER-USER: filter traffic to Docker-published ports arriving on lan0
*filter
:DOCKER-USER - [0:0]
-A DOCKER-USER -m conntrack --ctstate RELATED,ESTABLISHED -j RETURN
-A DOCKER-USER ! -i lan0 -j RETURN
-A DOCKER-USER -p tcp -m conntrack --ctorigdstport 8080 -s 192.168.10.0/24 -j RETURN
-A DOCKER-USER -p tcp -m conntrack --ctorigdstport 8080 -s 10.8.0.0/24 -j RETURN
-A DOCKER-USER -p tcp -m conntrack --ctorigdstport 8080 -s 192.168.99.0/24 -j RETURN
-A DOCKER-USER -p tcp -m conntrack --ctorigdstport 3000 -s 10.8.0.0/24 -j RETURN
-A DOCKER-USER -p tcp -m conntrack --ctorigdstport 3000 -s 192.168.99.0/24 -j RETURN
-A DOCKER-USER -m conntrack --ctstate NEW -j LOG --log-prefix "[DOCKER-USER DROP] "
-A DOCKER-USER -m conntrack --ctstate NEW -j DROP
-A DOCKER-USER -j RETURN
COMMIT
EOF
fi
ufw --force enable

# ---- 4. auditd rules
cat > /etc/audit/rules.d/50-lab.rules <<'EOF'
-w /etc/passwd -p wa -k identity
-w /etc/shadow -p wa -k identity
-w /etc/group -p wa -k identity
-w /etc/sudoers -p wa -k privilege
-w /etc/sudoers.d/ -p wa -k privilege
-w /etc/ssh/sshd_config -p wa -k sshd
-w /etc/ssh/sshd_config.d/ -p wa -k sshd
-w /etc/docker/ -p wa -k docker
-w /usr/bin/docker -p x -k docker
-w /var/log/auth.log -p wa -k authlog
-a always,exit -F arch=b64 -S execve -F euid=0 -F auid>=1000 -F auid!=unset -k root_cmd
-a always,exit -F arch=b64 -S sethostname,setdomainname -k system_locale
EOF
augenrules --load
systemctl enable --now auditd

# ---- 5. rsyslog: dedicated security log
cat > /etc/rsyslog.d/30-lab-security.conf <<'EOF'
auth,authpriv.*                      /var/log/lab-security.log
:msg, contains, "[UFW "              /var/log/lab-firewall.log
:msg, contains, "[DOCKER-USER DROP]" /var/log/lab-firewall.log
EOF
systemctl restart rsyslog

# ---- 6. fail2ban
cat > /etc/fail2ban/jail.d/lab.conf <<'EOF'
[DEFAULT]
bantime = 30m
findtime = 10m
maxretry = 4
backend = systemd
ignoreip = 127.0.0.1/8 192.168.99.10
[sshd]
enabled = true
EOF
systemctl enable --now fail2ban && systemctl restart fail2ban

# ---- 7. SSH hardening (key-only). We are running over a key-authenticated session = key access verified.
cat > /etc/ssh/sshd_config.d/10-lab-hardening.conf <<'EOF'
PasswordAuthentication no
KbdInteractiveAuthentication no
PermitRootLogin no
PubkeyAuthentication yes
MaxAuthTries 3
LoginGraceTime 30
X11Forwarding no
AllowTcpForwarding local
AllowUsers sysadmin
ClientAliveInterval 300
ClientAliveCountMax 2
EOF
sshd -t && systemctl reload ssh

# ---- 8. least privilege / misc
usermod -aG docker sysadmin
chmod 750 /home/sysadmin
sysctl -w net.ipv4.conf.all.send_redirects=0 net.ipv4.conf.all.accept_redirects=0 >/dev/null
printf 'net.ipv4.conf.all.send_redirects=0\nnet.ipv4.conf.all.accept_redirects=0\nkernel.dmesg_restrict=1\n' > /etc/sysctl.d/90-lab.conf
echo "=== done $(date -Is)"
docker --version; docker compose version; ufw status verbose | head -20; fail2ban-client status sshd | tail -3; auditctl -l | wc -l
