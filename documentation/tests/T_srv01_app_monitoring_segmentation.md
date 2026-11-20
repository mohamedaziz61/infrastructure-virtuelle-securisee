# Tests — srv01 (Ubuntu 25.04, VLAN 20) — 2026-11-19

Preuves brutes : `T_srv01_*.txt`, `T_app_srv01_*.txt`, `T_segmentation_vlan20_*.txt`, `logs/srv01_harden.log`.

## Sécurité Ubuntu

| # | Objectif | Procédure | Attendu | Résultat réel | Statut |
|---|---|---|---|---|---|
| U1 | Authentification SSH par clé | `ssh -i projet_cloud_ed25519 sysadmin@192.168.20.10` | connexion sans mot de passe | connexion OK | PASS |
| U2 | Mot de passe SSH désactivé (après vérification de la clé) | `sshd -T` | passwordauthentication no | `passwordauthentication no`, `permitrootlogin no`, `maxauthtries 3`, `allowusers sysadmin`, `x11forwarding no` | PASS |
| U3 | Pare-feu hôte UFW | `ufw status verbose` | refus entrant par défaut | deny (incoming) ; 22 seulement depuis 192.168.99.0/24 et 10.8.0.0/24 | PASS |
| U4 | Ports Docker publiés filtrés (contournent UFW) | `iptables -S DOCKER-USER` | 8080 : VLAN10/VPN/MGMT ; 3000 : VPN/MGMT ; reste DROP+LOG | chaîne conforme | PASS |
| U5 | fail2ban | `fail2ban-client status sshd` | jail actif | jail sshd actif, 0 banni | PASS |
| U6 | auditd | `auditctl -l`, `ausearch -k …` | règles chargées, événements | 12 règles ; événements : identity 13, sshd 7, docker 12, root_cmd 129 | PASS |
| U7 | rsyslog | journaux dédiés | `/var/log/lab-security.log`, `/var/log/lab-firewall.log` | présents et alimentés (sudo, UFW) | PASS |
| U8 | Surface d'écoute minimale | `ss -tlnp` | 22, 8080/3000 sur 192.168.20.10, 9090 en loopback | 22, 192.168.20.10:3000/8080, 127.0.0.1:9090, 9100 (filtré UFW) | PASS |
| U9 | Moindre privilège | sudoers, conteneurs | — | `sysadmin` sudo NOPASSWD (automatisation, clé obligatoire) ; root verrouillé | PASS (compromis documenté) |

## Application Docker (Flask + PostgreSQL) — Docker Engine 29.2.1 / Compose 5.0.2 sur srv01

| # | Objectif | Résultat réel | Statut |
|---|---|---|---|
| A1 | Santé de l'application depuis MGMT | `/health` → `{"db":"ok","status":"ok"}` HTTP 200 | PASS |
| A2 | Écriture de données | 3 POST → HTTP 303, `labapp_assets_total 3` | PASS |
| A3 | Redémarrage automatique après crash | `kill 1` → running, healthy, restarts=2 | PASS |
| A4 | Persistance (`compose down` + `up`) | volume `labapp_db_data` conservé, 3 enregistrements présents | PASS |
| A5 | Base non exposée | 192.168.20.10:5432 inaccessible ; réseau `backend` internal=true | PASS |
| A6 | Durcissement conteneur | user 10001, rootfs read-only, cap_drop ALL, no-new-privileges | PASS |
| A7 | Secrets | fichiers en répertoire 700 ; lecture refusée pour un autre utilisateur | PASS |

## Supervision Prometheus / Grafana

| # | Objectif | Résultat réel | Statut |
|---|---|---|---|
| M1 | Cibles Prometheus | 12 cibles `up` : node-srv01, windows-cli01, pfsense-snmp (10 interfaces), labapp, blackbox | PASS |
| M2 | Métriques réelles | `windows_os_info{version="6.1.7600"}`, `node_memory_MemAvailable_bytes`, `ifHCInOctets{instance="fw01"}` | PASS |
| M3 | Disponibilité des services (blackbox) | gw 192.168.20.1 et app :8080 = 1 ; NAS = 0 (TrueNAS pas encore installé) | PASS / en attente NAS |
| M4 | Prometheus non exposé | 192.168.20.10:9090 inaccessible (127.0.0.1 uniquement) | PASS |
| M5 | Grafana protégé | `/login` HTTP 200 depuis MGMT ; API sans authentification → 401 ; datasource + tableau de bord provisionnés | PASS |
| M6 | Redémarrage après coupure | 6/7 conteneurs relancés ; **Prometheus non relancé** car `docker compose kill -s SIGHUP` le marque « arrêté manuellement ». Corrigé : rechargement par `docker exec … kill -HUP 1` | FAIL → corrigé |

## Segmentation depuis VLAN 20 (srv01)

| Flux | Attendu | Réel | Statut |
|---|---|---|---|
| srv01 → cli01:9182 (Prometheus) | autorisé | OPEN | PASS |
| srv01 → cli01:445 / :3389 | bloqué | BLOCKED | PASS |
| srv01 → pfSense 443 / 22 | bloqué | BLOCKED | PASS |
| srv01 → MGMT 192.168.99.1:443, poste admin :22 | bloqué | BLOCKED | PASS |
| srv01 → réseau WAN 192.168.101.1 | bloqué | BLOCKED | PASS |
| srv01 → Internet HTTPS | autorisé | OPEN | PASS |
| srv01 → DNS externe direct 1.1.1.1:53 | bloqué (DNS via pfSense) | BLOCKED | PASS |
| srv01 → ping MGMT | bloqué | **OPEN** au 1er test (règle ICMP trop large vers RFC1918) → règle restreinte à l'alias `MONITORED_HOSTS` → BLOCKED | FAIL → corrigé |
