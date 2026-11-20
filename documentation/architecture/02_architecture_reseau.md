# Phase 2 — Architecture réseau

## 1. Choix d'implémentation de la segmentation

VMware Workstation ne fournit pas de vSwitch avec *port groups* 802.1Q, et le pilote e1000 de Windows 7
ne sait pas étiqueter les trames sans outil Intel PROSet. La segmentation est donc réalisée par
**un segment L2 isolé par VLAN**, chacun relié à une interface dédiée de pfSense
(équivalent fonctionnel d'un port d'accès par VLAN) :

| VLAN | Rôle | Support VMware | Adaptateur hôte | Sous-réseau | Passerelle pfSense |
|---|---|---|---|---|---|
| WAN | Internet (NAT) | VMnet8 (NAT existant) | 192.168.101.1 | 192.168.101.0/24 | IP statique 192.168.101.10, gw .2 |
| 10 | Clients Windows | LAN Segment `VLAN10-CLIENTS` | **aucun** | 192.168.10.0/24 | 192.168.10.1 |
| 20 | Serveurs / applications | LAN Segment `VLAN20-SERVERS` | **aucun** | 192.168.20.0/24 | 192.168.20.1 |
| 30 | Stockage TrueNAS | LAN Segment `VLAN30-STORAGE` | **aucun** | 192.168.30.0/24 | 192.168.30.1 |
| 99 | Management | VMnet5 host-only, DHCP VMware désactivé | 192.168.99.10 (poste admin) | 192.168.99.0/24 | 192.168.99.1 |
| VPN | OpenVPN | tunnel pfSense | — | 10.8.0.0/24 | 10.8.0.1 |

Les LAN Segments n'ont aucune interface sur l'hôte : le seul chemin entre segments passe par pfSense.
Ils sont locaux au portable et ne sont pas reliés au Wi-Fi physique.

## 2. Plan d'adressage

| Machine | Interface | Adresse | Mode |
|---|---|---|---|
| pfSense (fw01) | em0 WAN / em1 CLIENTS / em2 SERVERS / em3 STORAGE / em4 MGMT | .101.10 / .10.1 / .20.1 / .30.1 / .99.1 | statique |
| Ubuntu (srv01) | ens33 | 192.168.20.10 | statique |
| TrueNAS (nas01) | ens33 | 192.168.30.10 | statique |
| Windows 7 (cli01) | LAN | 192.168.10.100–199 | DHCP pfSense (réservation .10.50) |
| Poste admin (hôte) | VMnet5 | 192.168.99.10 | statique |

DNS : résolveur Unbound de pfSense sur chaque passerelle, domaine `lab.local`.

## 3. Flux autorisés (politique par défaut : refus)

| Source | Destination | Port | Justification |
|---|---|---|---|
| VLAN 10 | srv01 192.168.20.10 | TCP 8080 | application métier |
| VLAN 10 | nas01 192.168.30.10 | TCP 445 | partage SMB |
| VLAN 10 / 20 / 30 | passerelle de leur VLAN | UDP/TCP 53, UDP 123 | DNS, NTP |
| VLAN 10 / 20 / 30 | Internet (hors RFC1918) | TCP 80/443 | mises à jour |
| srv01 (Prometheus) | cli01 :9182, nas01 :9100/ICMP, fw01 :161 UDP | supervision |
| MGMT 99 | tout | tout | administration |
| VPN 10.8.0.0/24 | srv01 :8080, :3000 ; nas01 :445 | accès distant |
| WAN | fw01 | UDP 1194 | OpenVPN uniquement |
| tout sauf MGMT | interfaces d'admin pfSense (443/22) | — | **bloqué** |

## 4. Schéma

Voir `diagramme_reseau.svg`.
