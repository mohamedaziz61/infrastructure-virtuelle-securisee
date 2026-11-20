# Guide de test du projet — Infrastructure virtuelle sécurisée

Ce guide permet de démarrer le laboratoire, de retrouver les mots de passe et de **tester chaque composant**.
Toutes les commandes hôte se lancent dans **PowerShell** sur le portable. Les commandes Linux se lancent par SSH.

---

## 0. Prérequis

1. **Déconnecter Proton VPN** (son kill-switch bloque les réseaux du lab).
2. Portable branché au secteur.
3. Démarrer tout le lab dans le bon ordre (pfSense d'abord, puis routes, puis les autres VM) :
   ```powershell
   powershell -ExecutionPolicy Bypass -File "C:\Users\azizb\Desktop\projet cloud\scripts\00_start_lab.ps1"
   ```
   (accepter l'invite UAC pour les routes). Ajouter `-WithNas` pour démarrer aussi TrueNAS.
4. Patienter ~2 min que les VM finissent de démarrer.

---

## 1. Où sont les mots de passe

Tous les mots de passe générés sont dans **`secrets\credentials.json`** (ne pas partager ce fichier).
Pour afficher un mot de passe précis, par ex. pfSense :
```powershell
python -c "import json;print(json.load(open(r'C:\Users\azizb\Desktop\projet cloud\secrets\credentials.json'))['pfsense_admin'])"
```

| Clé dans credentials.json | Service / compte | Utilisé pour |
|---|---|---|
| `pfsense_admin` | pfSense — utilisateur **admin** | Interface web + SSH pfSense |
| `grafana_admin` | Grafana — utilisateur **admin** | Interface Grafana |
| `truenas_admin` | TrueNAS — utilisateur **truenas_admin** | Interface web TrueNAS (⚠ voir note) |
| `smb_user1` | SMB — utilisateur **smbuser1** | Montage du partage `lab_share` |
| `win7_labadmin` / `win7_user1` | Windows 7 — **labadmin** / **user1** | Console cli01 — mot de passe : voir `secrets/credentials.json` (clé `win7_labadmin`) |
| `snmp_community` | Communauté SNMP pfSense | Supervision |
| `nas_dataset_key` | Clé de chiffrement du dataset | Déverrouillage ZFS (auto au boot) |
| `app_db` | Mot de passe PostgreSQL (interne) | Base de l'application |

> ⚠ **TrueNAS** : le mot de passe web est celui que **vous avez saisi** pendant l'installation. S'il diffère
> de la valeur `truenas_admin` du fichier, utilisez celui que vous avez tapé.

**Clé SSH** (pas de mot de passe) : `C:\Users\azizb\.ssh\projet_cloud_ed25519`. Toutes les connexions SSH
ci-dessous l'utilisent (`-i`).

---

## 2. Tester pfSense (pare-feu)

**Interface web** (depuis le navigateur du portable) : <https://192.168.99.1>
→ utilisateur `admin`, mot de passe = clé `pfsense_admin`.
Vérifier : Status › Dashboard (5 interfaces), Firewall › Rules, VPN › OpenVPN, Services › DHCP.

**En ligne de commande :**
```powershell
ssh -i $HOME\.ssh\projet_cloud_ed25519 admin@192.168.99.1 "pfctl -sr | grep -c USER_RULE"   # nb de regles
ssh -i $HOME\.ssh\projet_cloud_ed25519 admin@192.168.99.1 "ping -c2 9.9.9.9"                  # NAT/Internet
ssh -i $HOME\.ssh\projet_cloud_ed25519 admin@192.168.99.1 "drill @127.0.0.1 srv01.lab.local A | grep srv01"  # DNS interne
```

---

## 3. Tester le serveur Ubuntu (srv01)

```powershell
ssh -i $HOME\.ssh\projet_cloud_ed25519 sysadmin@192.168.20.10 "hostname; uptime -p"
# SSH par mot de passe doit etre REFUSE :
ssh -o PubkeyAuthentication=no -o PreferredAuthentications=password sysadmin@192.168.20.10   # -> Permission denied (attendu)
# Pare-feu, fail2ban, conteneurs :
ssh -i $HOME\.ssh\projet_cloud_ed25519 sysadmin@192.168.20.10 "sudo ufw status; sudo fail2ban-client status sshd; docker ps --format '{{.Names}} {{.Status}}'"
```

---

## 4. Tester l'application conteneurisée

Depuis le navigateur du portable : <http://192.168.20.10:8080>
(ajouter un équipement dans le formulaire, il s'enregistre en base.)

```powershell
curl http://192.168.20.10:8080/health      # {"db":"ok","status":"ok"}
curl http://192.168.20.10:8080/metrics      # metriques de l'app
```
**Test de persistance** (les données survivent au redémarrage des conteneurs) :
```powershell
ssh -i $HOME\.ssh\projet_cloud_ed25519 sysadmin@192.168.20.10 "cd /opt/lab/docker && docker compose restart && sleep 10 && curl -s localhost:8080/metrics | grep assets_total"
```

---

## 5. Tester la supervision (Prometheus / Grafana)

**Grafana** : <http://192.168.20.10:3000> → utilisateur `admin`, mot de passe = clé `grafana_admin`.
Ouvrir le tableau de bord **« Projet Cloud — Vue d'ensemble infrastructure »**.

**Prometheus** (cibles) :
```powershell
ssh -i $HOME\.ssh\projet_cloud_ed25519 sysadmin@192.168.20.10 "curl -s localhost:9090/api/v1/targets | python3 -c 'import json,sys;[print(t[\"labels\"][\"job\"],t[\"health\"]) for t in json.load(sys.stdin)[\"data\"][\"activeTargets\"]]'"
```
Toutes les cibles doivent être `up` (12 cibles).

---

## 6. Tester TrueNAS (stockage)

**Interface web** : <https://192.168.30.10> → `truenas_admin` / votre mot de passe.
Vérifier : Storage (pool **tank**, miroir), Datasets (**tank/share** chiffré 🔒), Shares › SMB (**lab_share**),
Data Protection › Periodic Snapshot Tasks.

**En ligne de commande :**
```powershell
ssh -i $HOME\.ssh\projet_cloud_ed25519 truenas_admin@192.168.30.10 "midclt call pool.query | python3 -c 'import json,sys;p=json.load(sys.stdin)[0];print(p[\"name\"],p[\"status\"])'"
```

**Test du partage SMB** (depuis le portable — réseau MGMT autorisé). Dans l'Explorateur Windows, taper
dans la barre d'adresse : `\\192.168.30.10\lab_share` → utilisateur `smbuser1`, mot de passe = clé `smb_user1`.
Ou en PowerShell :
```powershell
$pw = python -c "import json;print(json.load(open(r'C:\Users\azizb\Desktop\projet cloud\secrets\credentials.json'))['smb_user1'])"
net use Z: \\192.168.30.10\lab_share /user:smbuser1 $pw
dir Z:\ ; net use Z: /delete
```

---

## 7. Tester Windows 7 (cli01)

Dans VMware, onglet **cli01-win7** → se connecter **labadmin** (mot de passe = clé `win7_labadmin`).
Vérifier : pare-feu actif, Observateur d'événements (journaux Sécurité).
Les métriques Windows sont déjà collectées par Prometheus (voir §5, cible `windows-cli01`).

> Limite connue : le montage SMB échoue depuis Windows 7 RTM (serveur SMB durci) — c'est documenté (§17 du rapport).

---

## 8. Tester la segmentation VLAN (pare-feu)

But : prouver qu'un client ne peut joindre QUE ce qui est autorisé.
```powershell
# Depuis srv01 (VLAN20), l'admin pfSense doit etre BLOQUE :
ssh -i $HOME\.ssh\projet_cloud_ed25519 sysadmin@192.168.20.10 "timeout 4 bash -c '</dev/tcp/192.168.99.1/443' && echo OUVERT || echo BLOQUE"   # attendu : BLOQUE
# Depuis srv01, l'application doit etre JOIGNABLE :
ssh -i $HOME\.ssh\projet_cloud_ed25519 sysadmin@192.168.20.10 "timeout 4 bash -c '</dev/tcp/192.168.20.10/8080' && echo OUVERT || echo BLOQUE"   # attendu : OUVERT
```
Les résultats complets des tests de segmentation sont dans `documentation/tests/T_segmentation_*` et `T_win7_cli01.md`.

---

## 9. Tester OpenVPN

Le profil client est `secrets\generated\vpnuser1.ovpn`. Test automatisé (client dans un conteneur, entre par le WAN) :
```powershell
cd "C:\Users\azizb\Desktop\projet cloud"
docker run --rm --cap-add NET_ADMIN --device /dev/net/tun -v "${PWD}\secrets\generated\vpnuser1.ovpn:/vpn/client.ovpn:ro" labvpnclient:1 bash -c "openvpn --config /vpn/client.ovpn --log /tmp/o.log --daemon; sleep 12; grep 'Initialization Sequence Completed' /tmp/o.log; timeout 4 bash -c '</dev/tcp/192.168.20.10/8080' && echo 'VPN->app OUVERT'"
```
(Avec un vrai client OpenVPN GUI : importer `vpnuser1.ovpn` ; aucune saisie de mot de passe, authentification par certificat.)

---

## 10. Test de récupération par snapshot (TrueNAS)

```powershell
$pw = python -c "import json;print(json.load(open(r'C:\Users\azizb\Desktop\projet cloud\secrets\credentials.json'))['smb_user1'])"
# écrire un fichier, snapshot, supprimer, restaurer :
ssh -i $HOME\.ssh\projet_cloud_ed25519 truenas_admin@192.168.30.10 "midclt call zfs.snapshot.create '{\"dataset\":\"tank/share\",\"name\":\"test-$(Get-Date -Format HHmmss)\"}'"
ssh -i $HOME\.ssh\projet_cloud_ed25519 truenas_admin@192.168.30.10 "midclt call zfs.snapshot.query '[[\"dataset\",\"=\",\"tank/share\"]]' | python3 -c 'import json,sys;[print(s[\"name\"]) for s in json.load(sys.stdin)]'"
```

---

## 11. Arrêter le lab proprement

```powershell
$vr = "C:\Program Files (x86)\VMware\VMware Workstation\vmrun.exe"
# arrêter les VM avec outils invités (srv01, nas01) proprement, pfSense/Win7 en dernier
ssh -i $HOME\.ssh\projet_cloud_ed25519 truenas_admin@192.168.30.10 "sudo shutdown -h now" 2>$null
& $vr -T ws stop "C:\Users\azizb\Desktop\projet cloud\VMs\srv01-ubuntu\srv01-ubuntu.vmx" soft
& $vr -T ws stop "C:\Users\azizb\Desktop\projet cloud\VMs\fw01-pfsense\fw01-pfsense.vmx" hard
```
(Windows 7 : menu Démarrer › Arrêter dans la VM.)

---

## Récapitulatif des accès

| Service | Adresse | Compte | Mot de passe (clé) |
|---|---|---|---|
| pfSense | https://192.168.99.1 | admin | `pfsense_admin` |
| Application | http://192.168.20.10:8080 | — | — |
| Grafana | http://192.168.20.10:3000 | admin | `grafana_admin` |
| TrueNAS | https://192.168.30.10 | truenas_admin | (saisi à l'install) |
| Partage SMB | \\192.168.30.10\lab_share | smbuser1 | `smb_user1` |
| SSH (tous) | 192.168.99.1 / .20.10 / .30.10 | admin / sysadmin / truenas_admin | clé `projet_cloud_ed25519` |
| Windows 7 | console VMware | labadmin / user1 | clé `win7_labadmin` (secrets/credentials.json) |
