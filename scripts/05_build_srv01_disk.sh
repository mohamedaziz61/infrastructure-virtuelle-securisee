#!/bin/bash
# Builds a minimal Ubuntu 25.04 (plucky) server directly onto srv01's VMDK (debootstrap), because the
# Ubuntu *desktop* ISO installer waits for GUI confirmation of autoinstall (needs 'autoinstall' kernel arg).
# Runs inside a privileged Docker container:  /vm = VMs/srv01-ubuntu, /seed = ISO/seed/ubuntu-cidata
# Result: EFI + ext4 root, static IP lan0 192.168.20.10, user sysadmin (key-only SSH), open-vm-tools.
set -euxo pipefail
MIRROR=http://archive.ubuntu.com/ubuntu
export DEBIAN_FRONTEND=noninteractive
apt-get update -q && apt-get install -y -q qemu-utils debootstrap gdisk dosfstools e2fsprogs >/dev/null
DISK=/vm/srv01-ubuntu-disk0.vmdk
qemu-nbd --disconnect /dev/nbd0 || true
qemu-nbd --connect=/dev/nbd0 --format=vmdk "$DISK"
sleep 2
sgdisk --zap-all /dev/nbd0
sgdisk -n1:1M:+512M -t1:ef00 -c1:EFI -n2:0:0 -t2:8304 -c2:root /dev/nbd0
partprobe /dev/nbd0 2>/dev/null || blockdev --rereadpt /dev/nbd0; sleep 2
# Docker's /dev may not get the partition nodes automatically
for n in 1 2; do [ -b /dev/nbd0p$n ] || mknod /dev/nbd0p$n b 43 $n; done
mkfs.vfat -F32 -n EFI /dev/nbd0p1
mkfs.ext4 -q -F -L root /dev/nbd0p2
T=/target; mkdir -p $T; mount /dev/nbd0p2 $T; mkdir -p $T/boot/efi; mount /dev/nbd0p1 $T/boot/efi
debootstrap --arch=amd64 --components=main,restricted,universe \
  --include=ca-certificates,locales,sudo,gnupg \
  plucky $T $MIRROR /usr/share/debootstrap/scripts/gutsy
cat > $T/etc/apt/sources.list.d/ubuntu.sources <<EOF
Types: deb
URIs: $MIRROR
Suites: plucky plucky-updates
Components: main restricted universe
Signed-By: /usr/share/keyrings/ubuntu-archive-keyring.gpg

Types: deb
URIs: http://security.ubuntu.com/ubuntu
Suites: plucky-security
Components: main restricted universe
Signed-By: /usr/share/keyrings/ubuntu-archive-keyring.gpg
EOF
rm -f $T/etc/apt/sources.list
for d in dev dev/pts proc sys; do mount --bind /$d $T/$d; done
HASH=$(grep -o "password: '[^']*'" /seed/user-data | sed "s/password: '//; s/'$//")
PUBKEY=$(grep -o "ssh-ed25519 [^ ']* admin@projet-cloud" /seed/user-data)
ROOTUUID=$(blkid -s UUID -o value /dev/nbd0p2); EFIUUID=$(blkid -s UUID -o value /dev/nbd0p1)
cat > $T/etc/fstab <<EOF
UUID=$ROOTUUID / ext4 defaults,errors=remount-ro 0 1
UUID=$EFIUUID /boot/efi vfat umask=0077 0 1
EOF
echo srv01 > $T/etc/hostname
printf '127.0.0.1 localhost\n127.0.1.1 srv01.lab.local srv01\n' > $T/etc/hosts
mkdir -p $T/etc/netplan
cat > $T/etc/netplan/01-lan0.yaml <<'EOF'
network:
  version: 2
  ethernets:
    lan0:
      match: {macaddress: "00:50:56:2a:20:10"}
      set-name: lan0
      addresses: [192.168.20.10/24]
      routes: [{to: default, via: 192.168.20.1}]
      nameservers: {addresses: [192.168.20.1], search: [lab.local]}
EOF
chmod 600 $T/etc/netplan/01-lan0.yaml
chroot $T /bin/bash -euxc "
  apt-get update -q
  apt-get install -y -q --no-install-recommends linux-image-generic initramfs-tools grub-efi-amd64 shim-signed \
     openssh-server netplan.io systemd-resolved systemd-timesyncd open-vm-tools iproute2 iputils-ping \
     curl nano less bash-completion cron logrotate rsyslog kbd console-setup
  locale-gen fr_FR.UTF-8 en_US.UTF-8 && update-locale LANG=fr_FR.UTF-8
  ln -sf /usr/share/zoneinfo/Africa/Tunis /etc/localtime
  sed -i 's/^XKBLAYOUT=.*/XKBLAYOUT=\"fr\"/' /etc/default/keyboard || true
  useradd -m -s /bin/bash -G sudo -p '$HASH' sysadmin
  install -d -m 700 -o sysadmin -g sysadmin /home/sysadmin/.ssh
  echo '$PUBKEY' > /home/sysadmin/.ssh/authorized_keys
  chown sysadmin:sysadmin /home/sysadmin/.ssh/authorized_keys && chmod 600 /home/sysadmin/.ssh/authorized_keys
  echo 'sysadmin ALL=(ALL) NOPASSWD:ALL' > /etc/sudoers.d/90-sysadmin-automation && chmod 440 /etc/sudoers.d/90-sysadmin-automation
  passwd -l root
  systemctl enable ssh systemd-networkd systemd-resolved systemd-timesyncd open-vm-tools
  sed -i 's/^GRUB_CMDLINE_LINUX_DEFAULT=.*/GRUB_CMDLINE_LINUX_DEFAULT=\"\"/; s/^GRUB_TIMEOUT=.*/GRUB_TIMEOUT=2/' /etc/default/grub
  grub-install --target=x86_64-efi --efi-directory=/boot/efi --removable --no-nvram --uefi-secure-boot
  update-initramfs -u -k all
  update-grub
  apt-get clean
"
ln -sf /run/systemd/resolve/stub-resolv.conf $T/etc/resolv.conf
for d in sys proc dev/pts dev; do umount $T/$d; done
umount $T/boot/efi; umount $T
sync; qemu-nbd --disconnect /dev/nbd0
echo "BUILD_OK"
