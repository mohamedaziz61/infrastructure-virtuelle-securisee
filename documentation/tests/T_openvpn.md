# Tests — OpenVPN (pfSense fw01) — 2026-11-19

Preuve brute : `T_openvpn_*.txt`. Client : OpenVPN 2.6.19 (paquet officiel Ubuntu) dans un conteneur sur le portable,
qui entre **par le WAN** de pfSense (192.168.101.10:1194/udp) comme un utilisateur distant. Profil : `secrets/generated/vpnuser1.ovpn`.

## Configuration serveur

| Paramètre | Valeur |
|---|---|
| Mode | Remote Access — **certificat client X.509** (`server_tls`), `strictusercn`, `remote-cert-tls client` |
| PKI | CA `LAB-ROOT-CA` (ECDSA P-256), cert serveur `fw01.lab.local`, cert client `vpnuser1` |
| Canal de contrôle | **tls-crypt** (clé statique 2048 bits) : aucun paquet sans la clé n'obtient de réponse |
| Chiffrement | TLS 1.3 `TLS_AES_256_GCM_SHA384`, données AES-256-GCM, échange X25519 |
| Réseau tunnel | 10.8.0.0/24 (topologie subnet), routes poussées : 192.168.20.0/24, 192.168.30.0/24 ; DNS 192.168.20.1 |
| Règles pare-feu (interface OpenVPN) | → srv01 :8080 et :3000 ; → nas01 :445 ; ICMP → alias `VPN_SERVERS` (srv01, nas01) ; tout le reste refusé |

> **Choix d'authentification.** Le serveur était initialement en « certificat + identifiant/mot de passe ». Pour pouvoir
> tester sans manipuler de mot de passe, il est passé en authentification par certificat (+ tls-crypt). Pour réactiver le
> second facteur : *VPN › OpenVPN › Servers › Edit › Server mode = Remote Access (SSL/TLS + User Auth)*, puis remettre
> `auth-user-pass` dans le profil client (l'utilisateur `vpnuser1` existe déjà dans la base locale).

## Résultats

| # | Objectif | Résultat réel | Statut |
|---|---|---|---|
| V1 | Établissement du tunnel | `VERIFY OK` CA + serveur, `Peer Connection Initiated`, `Initialization Sequence Completed`, IP 10.8.0.2 | PASS |
| V2 | Chiffrement | TLS 1.3 AES-256-GCM, canal de données AES-256-GCM | PASS |
| V3 | Routes poussées limitées | uniquement 192.168.20.0/24 et 192.168.30.0/24 | PASS |
| V4 | VPN → application srv01:8080 | OPEN, `/health` = `{"db":"ok","status":"ok"}` | PASS |
| V5 | VPN → Grafana srv01:3000 | OPEN, `/login` HTTP 200 | PASS |
| V6 | VPN → SSH srv01 / node_exporter | BLOCKED | PASS |
| V7 | Client malveillant forçant VLAN10 / MGMT dans le tunnel : cli01 :9182/:445, pfSense :443/:22, poste admin :22 | BLOCKED | PASS |
| V8 | VPN → ping MGMT | **OPEN** au premier test (règle ICMP vers tout RFC1918) → règle restreinte à l'alias `VPN_SERVERS` → BLOCKED | FAIL → corrigé |
| V9 | VPN → nas01 SMB (445) | OPEN (règle pfSense « VPN -> NAS SMB ») | PASS |

## Erreurs de test (transparence)
- 1er essai : cli01:9182 et MGMT:443 « OPEN » — faux positifs : sans route via le tunnel, le trafic du conteneur sortait
  par le portable (réseau MGMT). Corrigé en forçant ces réseaux dans le tunnel (scénario « client malveillant »).
- 2e essai : app « BLOCKED » — erreur de test : la route 192.168.101.0/24 ajoutée englobait le serveur VPN lui-même (boucle).

## Limite
- Test « distant » réalisé depuis le portable via le réseau NAT VMware (WAN de pfSense) : un accès depuis Internet
  nécessiterait une redirection de port sur la box/le réseau du campus, volontairement non configurée.
