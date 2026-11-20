# Déploiement et sécurisation d'une infrastructure virtuelle

Laboratoire de sécurité des infrastructures construit sur **VMware Workstation 17.5.2** (hôte Windows 11) et
**Docker**, simulant l'environnement d'une petite organisation : pare-feu central, segmentation VLAN,
serveur durci, stockage chiffré, supervision et accès distant VPN.

> ⚠️ **Secrets non versionnés.** Les mots de passe, clés PKI, clés VPN et la communauté SNMP ne sont pas dans
> le dépôt (voir `.gitignore`). Ils sont régénérés par `scripts/03_generate_seed_configs.py` et stockés dans
> `secrets/` (local uniquement). Les images ISO et les disques de VM (~32 Go) sont également exclus.

## Architecture

| Composant | VM / Hôte | Réseau | Rôle |
|---|---|---|---|
| pfSense 2.7.2 | fw01 | passerelle de tous les VLAN | Pare-feu, routage inter-VLAN, NAT, DHCP, DNS, OpenVPN |
| Ubuntu 25.04 | srv01 | VLAN 20 (192.168.20.10) | SSH par clé, Docker Engine, application, supervision |
| Windows 7 Pro | cli01 | VLAN 10 (192.168.10.50) | Client ; pare-feu, audit, windows_exporter |
| TrueNAS 25.10 | nas01 | VLAN 30 (192.168.30.10) | Pool ZFS miroir, dataset chiffré, SMB, snapshots |
| Poste admin | hôte | VLAN 99 (192.168.99.10) | Administration (GUI/SSH) |

Diagramme : `documentation/architecture/diagramme_reseau.svg`.

## Arborescence

```
scripts/        Automatisation (création VM, configs, durcissement, outillage hors ligne)
docker/         Application conteneurisée (Flask + PostgreSQL) + images utilitaires
monitoring/     Pile Prometheus / Grafana / exporters
documentation/  Inventaire, architecture, tests, rapport final PDF, guide de test
logs/           Journal des opérations
```

## Démarrage

```powershell
# 1. Déconnecter Proton VPN (son kill-switch bloque le lab)
# 2. Régénérer les secrets si absents :
python scripts\03_generate_seed_configs.py
# 3. Démarrer le lab (pfSense d'abord) :
powershell -ExecutionPolicy Bypass -File scripts\00_start_lab.ps1
```

Guide de test complet : `documentation/GUIDE_TEST.md`. Rapport final : `documentation/final_report.pdf`.

## Sécurité — points clés

- Segmentation réelle : tout trafic inter-VLAN traverse pfSense (politique « refus par défaut »).
- Authentification forte : SSH par clé, VPN par certificat X.509 + tls-crypt.
- Chiffrement : dataset TrueNAS AES-256-GCM, tunnels TLS 1.3.
- Durcissement : UFW + DOCKER-USER, auditd, fail2ban, conteneurs non-root en lecture seule.
