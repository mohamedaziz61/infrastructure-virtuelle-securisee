# Tests — cli01 (Windows 7) — 2026-11-19

Preuves brutes : `documentation/tests/cli01_evidence/` (collectées hors ligne, disque monté en lecture seule).

| # | Objectif | Procédure | Attendu | Résultat réel | Statut |
|---|---|---|---|---|---|
| W1 | Installation non assistée | autounattend.xml (ISO seed) | OS installé sans interaction | Windows 7 Professionnel x64 **6.1.7600 (RTM, sans SP1)** installé | PASS |
| W2 | DHCP + réservation | bail pfSense (MAC 00:50:56:2a:10:50) | IP 192.168.10.50 | ping 192.168.10.50 OK (TTL 128) depuis pfSense | PASS |
| W3 | Pare-feu Windows | `netsh advfirewall show allprofiles` | 3 profils actifs, entrant bloqué | Domaine/Privé/Public : Actif, BlockInbound,AllowOutbound | PASS |
| W4 | Audit de sécurité | `auditpol /get /category:*` | Succès+échec sur toutes catégories | Toutes catégories « Succès et échec » (dont Création du processus) | PASS |
| W5 | Événements de sécurité | `wevtutil qe Security` | événements générés | 4688 (création processus), 5156 (connexion WFP), 4656… | PASS |
| W6 | Politique de mots de passe | `net accounts` | ≥12 car., verrouillage | 12 car. min, 90 j max, verrouillage 5 essais / 15 min | PASS |
| W7 | Comptes locaux | `net user` | Invité désactivé, admin dédié + utilisateur standard | Administrateur, Invité (désactivé), labadmin (admin), user1 (utilisateur) | PASS |
| W8 | Sysmon | `Sysmon64.exe -i sysmon-lab.xml` (v15.22, signée Microsoft) | service Sysmon64 | **code 0xC0000139 (point d'entrée introuvable)** : Sysmon 15 ne supporte plus Windows 7 RTM ; aucune version antérieure disponible de source officielle | **FAIL (limitation documentée)** |
| W9 | windows_exporter | MSI v0.18.1 (dernière version documentée pour Windows 7), port 9182 restreint à 192.168.20.10 | service RUNNING, métriques depuis srv01 | RUNNING ; `curl http://192.168.10.50:9182/metrics` depuis srv01 → HTTP 200, `windows_os_info{version="6.1.7600"}` | PASS |
| W10 | Isolation | pas d'accès entrant hors règles | seul srv01 → 9182 et passerelle → ICMP | règles pare-feu Windows `windows_exporter from srv01`, `ICMP from gateway` | PASS |

## Limites constatées
- **Windows 7 RTM sans Service Pack 1** : de nombreux correctifs et la prise en charge SHA-2 manquent. Le média MLF fourni
  ne contient pas le SP1 ; l'installer (KB976932) est recommandé mais Windows 7 reste hors support depuis janvier 2020.
- Sysmon remplacé par l'audit natif (4688, 5156…) ; la ligne de commande des processus (4688) n'est pas journalisée sur Windows 7.

## Segmentation depuis VLAN 10 (exécuté sur cli01 en tant que NT AUTHORITY\SYSTEM, 19/11/2026 18:21)

Preuve : `cli01_evidence/segmentation_vlan10.txt`, `cli01_evidence/nettest_trace.txt`.

| Flux | Attendu | Réel | Statut |
|---|---|---|---|
| cli01 → app srv01:8080 (+ GET /health) | autorisé | OPEN, `{"db":"ok","status":"ok"}` | PASS |
| cli01 → Grafana srv01:3000 | bloqué (MGMT/VPN uniquement) | BLOCKED | PASS |
| cli01 → SSH srv01:22, node_exporter :9100 | bloqué | BLOCKED | PASS |
| cli01 → pfSense 443 / 22 (sa propre passerelle) | bloqué | BLOCKED | PASS |
| cli01 → MGMT 192.168.99.1:443 | bloqué | BLOCKED | PASS |
| cli01 → interface TrueNAS 192.168.30.10:443 | bloqué | BLOCKED | PASS |
| cli01 → Internet HTTPS | autorisé | OPEN | PASS |
| cli01 → DNS externe direct 1.1.1.1:53 | bloqué | BLOCKED | PASS |
| cli01 → réseau WAN 192.168.101.2 | bloqué | BLOCKED | PASS |
| DNS interne srv01.lab.local / externe via pfSense | résolu | 192.168.20.10 / 130.89.148.77 | PASS |
| cli01 → NAS 445 (couche réseau) | autorisé | TCP 445 **OPEN** (pare-feu pfSense OK) | PASS |
| cli01 → montage SMB nas01 | montage réussi | **échec (erreur 67)** : Windows 7 RTM sans SP1 ne négocie pas avec le serveur SMB durci (SMB1 off, NTLMv1 off, min SMB2.1) | **FAIL (limitation legacy documentée)** |

## Incidents de mise en œuvre (transparence)
- Arrêts forcés répétés + démontage NTFS non propre (script interrompu) → **chkdsk** au démarrage (récupération de fichiers orphelins), sans perte de données utiles.
- Premier script de test : chemins corrompus par `printf` (`\e`, `\n` interprétés) → aucun résultat ; corrigé en écrivant le fichier sans `printf`.
- Le script de test se termine désormais par `shutdown /s` : plus d'arrêt forcé avant la collecte des preuves.

## SMB depuis Windows 7 (constat de sécurité)
- **Couche réseau** : TCP 445 vers 192.168.30.10 **ouvert** depuis VLAN 10 (règle pfSense « Clients -> NAS SMB ») → segmentation conforme.
- **Couche applicative** : `net use` échoue (erreur système 67). TrueNAS durci (SMB1 désactivé, NTLMv1 désactivé,
  protocole minimum SMB 2.1) ; Windows 7 **RTM 6.1.7600 sans SP1** ne parvient pas à établir la session SMB2.
- **Décision** : ne PAS affaiblir le serveur (réactiver SMB1/NTLMv1) pour un client obsolète — cela contredirait
  l'objectif de sécurité. Le partage est accessible depuis srv01 (SMB3) et le VPN. Correctif recommandé : SP1 (KB976932)
  ou client SMB3. Illustre le coût d'un système d'exploitation hors support.
