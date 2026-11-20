# Tests — TrueNAS SCALE 25.10.7 (nas01, VLAN 30) — 2026-11-19

Preuves brutes : `T_truenas_*.txt`. Configuration réalisée **entièrement par l'API middleware (`midclt`)** via SSH
par clé, sans mot de passe console.

## Mise en service (transparence)

L'installateur TrueNAS exige la saisie manuelle d'un mot de passe `truenas_admin` à la console et VMware n'accepte
pas les frappes simulées. L'accès SSH par clé a donc été activé **hors ligne** :
1. Arrêt propre de la VM (open-vm-tools) et **sauvegarde du disque système** (`backups/nas01-boot-disk/`).
2. Disque système attaché temporairement à srv01 (qui dispose d'OpenZFS 2.3.1).
3. Import du `boot-pool`, ajout de la clé publique dans `/home/truenas_admin/.ssh/authorized_keys` (uid 950, 600),
   activation du service SSH (base `freenas-v1.db`) et ajout d'une tâche **POSTINIT** `midclt call service.start ssh`
   garantissant le démarrage du service à chaque boot. Authentification par mot de passe SSH désactivée.
4. Export propre du pool, détachement du disque, redémarrage. Connexion par clé vérifiée.

> Aucune donnée réelle n'est stockée : disques virtuels de test uniquement. Un miroir ZFS virtuel ne protège pas
> contre une panne du disque physique du portable (limitation documentée).

## Configuration et résultats

| # | Objectif | Résultat réel | Statut |
|---|---|---|---|
| N1 | Accès SSH par clé (sans mot de passe) | `truenas_admin@192.168.30.10`, `passwordauth=False`, port 22 | PASS |
| N2 | Pool ZFS **miroir** | `tank` ONLINE, type MIRROR, disques sdb+sdc, healthy=True | PASS |
| N3 | Dataset **chiffré** | `tank/share` encrypted=True, **AES-256-GCM**, clé chargée | PASS |
| N4 | Partage **SMB** | `lab_share` → /mnt/tank/share, enabled=True, service cifs RUNNING + au démarrage | PASS |
| N5 | **Comptes & contrôle d'accès** | utilisateur `smbuser1` (uid 3000, smb) + groupe `smbshare` ; ACL NFSv4 (owner/group FULL_CONTROL, everyone READ) | PASS |
| N6 | Accès SMB authentifié depuis VLAN 20 | `smbclient` : liste `lab_share`, écriture `proof.txt` OK | PASS |
| N7 | **Snapshots** | tâche horaire `auto-%Y%m%d-%H%M` (rétention 2 semaines) + snapshot `baseline-20261119` | PASS |
| N8 | **Récupération par snapshot** | snapshot → suppression SMB de proof.txt → `zfs rollback` → fichier restauré, contenu identique (`lab-secret-data-v1`) | PASS |
| N9 | Accès SMB depuis le VPN | `VPN → 192.168.30.10:445` OPEN (règle pfSense) | PASS |
| N10 | Supervision | sondes blackbox Prometheus : ICMP, TCP 445, TCP 443 = 1 (up) | PASS |
| N11 | Segmentation | interface web (443) **bloquée** depuis VLAN 10 (cli01) ; SMB (445) autorisé depuis VLAN 10/20 et VPN uniquement | PASS |

## Limites
- **Miroir ZFS virtuel** : protège contre la perte logique (snapshots, suppression) mais pas contre la panne du
  disque physique unique du portable. Une vraie redondance exige des disques physiques distincts.
- Interface web en HTTP/HTTPS auto-signé : certificat non approuvé par les navigateurs. À signer par la CA du lab.
- Clé de chiffrement du dataset conservée dans `secrets/credentials.json` (déverrouillage automatique au boot).

## N12 — Persistance après redémarrage (robustesse)
Après `system.reboot` : connexion SSH par clé rétablie (~65 s), pool `tank` ONLINE, dataset chiffré
**déverrouillé automatiquement** (locked=False), service SMB RUNNING, données SMB intactes
(`proof.txt` = `lab-secret-data-v1`). **PASS** — le lab survit à un redémarrage sans intervention.
