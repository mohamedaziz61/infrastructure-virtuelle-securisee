# Phase 1 — Inventaire de l'environnement physique

Date de l'audit : 2026-11-19 — audit en lecture seule (aucune modification).

## 1. Hôte physique

| Élément | Valeur constatée |
|---|---|
| OS | Microsoft Windows 11 Professionnel 10.0.26300 (build 26300) |
| CPU | Intel Core i7-11800H @ 2.30 GHz — 8 cœurs / 16 threads |
| RAM | 31,7 Go total — 16,5 Go libres au moment de l'audit |
| Disque C: | 374,2 Go utilisés — **101,7 Go libres** |
| Hyperviseur Windows | Présent (VBS actif, WSL2 + Docker Desktop) → `VirtualizationFirmwareEnabled=False` est normal : VMware fonctionne en mode *Windows Hypervisor Platform* (performances légèrement réduites) |
| VPN hôte | Proton VPN (adaptateur ProTUN, 10.2.0.2) actif |

## 2. VMware Workstation

- Version : **17.5.2 build-23775571** (`C:\Program Files (x86)\VMware\VMware Workstation\`)
- Outils disponibles : `vmrun.exe`, `vmware-vdiskmanager.exe`, `vnetlib64.exe`, `mkisofs.exe`
- Services : VMnetDHCP (Running), VMware NAT Service (Running)

### Réseaux virtuels existants (non modifiés)

| VMnet | Type / sous-réseau | Adaptateur hôte |
|---|---|---|
| VMnet0 | Bridged | — |
| VMnet1 | Host-only 192.168.22.0/24 | 192.168.22.1 |
| VMnet8 | NAT 192.168.101.0/24 (gw .2) | 192.168.101.1 |
| VMnet10 | 192.168.65.0/24 | 192.168.65.1 |
| VMnet11 | 192.168.11.0/24 | 192.168.11.100 |
| VMnet12 | 192.168.12.0/24 | 192.168.12.100 |
| VMnet2–7, 9, 13–19 | non configurés | — |

### Machines virtuelles existantes (conservées, non modifiées)

| VM | Emplacement | Notes |
|---|---|---|
| pfSense | Documents\Virtual Machines\pfSense | 2 vCPU/2 Go, NAT+VMnet11+VMnet12, 1,5 Go |
| Ubuntu server | Documents\Virtual Machines\Ubuntu server | 2 vCPU/4 Go, VMnet12, 15,7 Go + snapshot |
| Ubuntu | Documents\Virtual Machines\Ubuntu | coquille vide (0 Go) |
| windows10 | Documents\Virtual Machines\windows10 | — |
| Kali 2025 (zSecurity) | Desktop\CS\ | laboratoire universitaire |
| Metasploitable2 | Downloads\ | laboratoire universitaire |

Décision (validée par l'utilisateur) : **nouvelles VMs dédiées** dans `projet cloud\VMs`, les anciennes restent intactes.

## 3. Docker Desktop

| Élément | Valeur |
|---|---|
| Docker Desktop | 4.57.0 (215387) |
| Engine | 29.1.3 (linux/amd64, backend WSL2) |
| Compose | v5.0.1 |
| WSL | distributions `Ubuntu` et `docker-desktop` (WSL 2, Running) |
| Conteneurs existants | pile `focuskid-*` (caddy sur 80/443, mysql, adminer, mailpit, cloudflared) — **hors projet, non touchée** |

Décision (validée) : application + supervision dans **Docker Engine sur la VM Ubuntu (VLAN 20)**, derrière pfSense. Docker Desktop sert uniquement à valider la pile Compose avant déploiement.

## 4. Images ISO (réutilisées, non dupliquées)

| Fichier | Taille | SHA-256 | Vérification |
|---|---|---|---|
| pfSense-CE-2.7.2-RELEASE-amd64.iso | 834 Mo | 441005F7…5D51 | Netgate ne publie que le hash du `.iso.gz` → non vérifiable directement |
| SW_DVD5_Win_Pro_7_64BIT_French_Full_MLF_X15-71101.ISO | 2,84 Go | B8DE36D7…4860 | Média licence en volume (MLF) Windows 7 Pro x64 FR |
| TrueNAS-SCALE-25.10.7.iso | 2,18 Go | 54CE9441…7C8E | **Conforme** au `.sha256` officiel |
| ubuntu-25.04-desktop-amd64.iso | 5,85 Go | B87366B6…DEA4 | **Conforme** au SHA256SUMS officiel (old-releases) |

Hashes complets : `documentation/configurations/iso_sha256.txt`.

## 5. Points d'attention

1. **Ubuntu 25.04 est en fin de vie** (janvier 2026) : plus de correctifs de sécurité. Les sommes de contrôle de l'ISO sont publiées sur old-releases.ubuntu.com, mais les paquets `plucky` sont encore servis par archive.ubuntu.com (vérifié le 19/11/2026). Limitation documentée.
2. **Windows 7** : fin de support depuis 2020 → isolé en VLAN 10, sans exposition Internet.
3. RAM : les 4 VMs demandent 16 Go ; avec Docker Desktop actif il reste ~16,5 Go → déploiement échelonné obligatoire (arrêter Docker Desktop lors des démos complètes).
4. Disque : 101,7 Go libres ; disques fins, consommation réelle estimée 35–45 Go.
5. Proton VPN actif sur l'hôte : peut perturber le NAT VMware (VMnet8) ; à désactiver en cas de problème de connectivité WAN des VMs.
