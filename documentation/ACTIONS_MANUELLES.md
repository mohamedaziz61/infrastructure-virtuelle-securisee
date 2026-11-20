# Actions manuelles requises (console VMware)

Les installateurs des OS n'acceptent pas de frappes scriptées : ces étapes demandent ~25 min de clics.
Tout le reste (configuration, durcissement, Docker, supervision, tests) est automatisé ensuite par SSH.
Mots de passe : `secrets/credentials.json` (ne pas committer / partager).

## 1. pfSense — fw01 (VM déjà démarrée)
1. Accepter la licence → **Install** → partitionnement **Auto (UFS)** ou ZFS par défaut.
2. Disque cible : choisir **da0 — 16 GB** (ne PAS choisir le disque de 16 MB `ecl-config`).
3. Fin → **Reboot**. Après le redémarrage, pfSense importe automatiquement `config.xml`
   depuis le disque `ecl-config` (External Config Loader).
4. Vérification console : le menu doit afficher `WAN em0 192.168.101.10`, `LAN em1 192.168.10.1`,
   `OPT1 em2 192.168.20.1`, `OPT2 em3 192.168.30.1`, `OPT3 em4 192.168.99.1`.
   **Si ce n'est pas le cas** : depuis l'hôte, ouvrir https://192.168.99.1 n'est pas encore possible —
   choisir l'option console `1) Assign Interfaces` (em0..em4 dans cet ordre) puis
   `2) Set interface IP` pour em4 = 192.168.99.1/24, ensuite https://192.168.99.1 →
   Diagnostics › Backup & Restore › Restore → `secrets/generated/pfsense/config.xml`.
5. Me prévenir : je vérifie l'accès SSH par clé (`ssh admin@192.168.99.1`) et je continue.

## 2. Ubuntu — srv01 (après pfSense)
Démarrer la VM `VMs/srv01-ubuntu`. L'installateur lit l'autoinstall du CD `CIDATA`.
S'il demande de confirmer l'installation automatique, répondre **oui** ; s'il affiche
l'assistant graphique, choisir **Installation automatisée** — fichier `autoinstall.yaml` sur le CD CIDATA.

### 2b. Activer SSH sur srv01 (l'installateur *desktop* ignore la section `ssh:` de l'autoinstall)
Console srv01 → se connecter `sysadmin` (mot de passe `ubuntu_sysadmin` de `secrets/credentials.json`),
ouvrir un Terminal (Ctrl+Alt+T si session graphique) et taper :

```
sudo sed -i 's#http://[a-z.]*ubuntu.com#http://old-releases.ubuntu.com#g' /etc/apt/sources.list.d/ubuntu.sources
sudo apt-get update && sudo apt-get install -y openssh-server
sudo mount -o ro LABEL=CIDATA /mnt
mkdir -p ~/.ssh && grep -o 'ssh-ed25519 [^ ]* admin@projet-cloud' /mnt/user-data >> ~/.ssh/authorized_keys
chmod 700 ~/.ssh && chmod 600 ~/.ssh/authorized_keys && sudo systemctl enable --now ssh
```

## 3. Windows 7 — cli01
Démarrer `VMs/cli01-win7` : installation entièrement automatique (autounattend.xml), ~20 min.
Si une clé produit est demandée (média MLF), cliquer **Ignorer**.

## 4. TrueNAS — nas01 (8 Go RAM : arrêter Docker Desktop si la RAM libre < 9 Go)
1. Démarrer `VMs/nas01-truenas` → **Install/Upgrade** → disque **sda 20 GiB** uniquement.
2. Mot de passe `truenas_admin` : valeur `truenas_admin` de `secrets/credentials.json`.
3. Après reboot, console : `1) Configure network interfaces` → ens* : 192.168.30.10/24 ;
   `2) Configure network settings` → passerelle 192.168.30.1, DNS 192.168.30.1.
4. Depuis le PC (réseau MGMT), ouvrir **http://192.168.30.10** et se connecter en `truenas_admin`.
5. **Credentials › Users › truenas_admin › Edit** → *Authorized Keys* : coller la clé publique
   (contenu de `C:\Users\azizb\.ssh\projet_cloud_ed25519.pub`, une seule ligne `ssh-ed25519 AAAA… admin@projet-cloud`) → Save.
6. **System › Services › SSH** → activer *Running* + *Start Automatically*
   (laisser « Allow Password Authentication » **désactivé**).
7. Me prévenir : je crée ensuite par SSH (clé uniquement) le pool ZFS miroir, le dataset chiffré,
   le partage SMB, les utilisateurs, les ACL et les snapshots, puis je restreins l'accès SSH.
