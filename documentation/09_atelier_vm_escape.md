# Phase 9 — Atelier pédagogique : isolation hyperviseur et « VM escape »

> Atelier **défensif et contrôlé**. Aucune exploitation d'hyperviseur n'est tentée : on observe la surface
> d'attaque, on mesure l'effet des contre-mesures, et on distingue clairement *évasion de VM* et *trafic réseau normal*.

## 1. Notions

| Notion | Définition |
|---|---|
| Isolation hyperviseur | Chaque VM ne voit que du matériel virtuel (vCPU, vRAM, vNIC, vDisk) émulé par l'hyperviseur (VMware Workstation 17.5.2, type 2, ici au-dessus de Windows 11 + Windows Hypervisor Platform). |
| VM escape | Exécution de code **hors** de la VM (dans le processus `vmware-vmx.exe` de l'hôte ou dans le noyau hôte) en exploitant une faille de l'hyperviseur ou d'un périphérique virtuel. |
| VM-to-VM | Accès d'une VM aux ressources d'une autre VM **sans passer par le réseau** (mémoire, disque, canal hôte), en général via une évasion vers l'hôte. |
| Ce qui n'est PAS une évasion | Un ping, un partage SMB, une connexion SSH entre VMs : c'est du **trafic réseau**, contrôlé par pfSense et les pare-feu hôtes. |

## 2. Surface d'attaque d'une VM VMware

| Composant | Risque | Exemples publics (CVE) |
|---|---|---|
| Contrôleurs USB virtuels (UHCI/EHCI/XHCI) | Corruption mémoire dans `vmx` → exécution sur l'hôte | CVE-2024-22252/22253 (use-after-free XHCI/UHCI, mars 2024) |
| Périphériques virtuels partagés (Bluetooth, EHCI) | Débordements dans l'émulation | CVE-2023-20869 (partage Bluetooth, VMSA-2023-0008), CVE-2022-31705 (EHCI, GeekPwn 2022) |
| Dossiers partagés HGFS | Accès aux fichiers hôte depuis l'invité | fonctionnalité à désactiver par principe (moindre privilège) |
| Presse-papiers / glisser-déposer (canal RPC « backdoor », `vmtoolsd`) | Canal de données VM ↔ hôte, fuite d'informations | risque de conception, pas de CVE précis retenu |
| VMware Tools | Code privilégié dans l'invité | CVE-2023-20900 / CVE-2023-34058 (contournement SAML), CVE-2023-34059 (élévation open-vm-tools) |
| Hôte non patché | Toute faille ci-dessus exploitable | — |

Version auditée : **17.5.2 build-23775571** — vérifier les avis de sécurité VMware/Broadcom (VMSA) et appliquer
la dernière 17.x (mise à jour gratuite) ; voir « Limites ».

## 3. Contre-mesures appliquées dans ce projet (vérifiables dans chaque `.vmx`)

```ini
isolation.tools.hgfs.disable = "TRUE"     # pas de dossiers partagés
sharedFolder.maxNum = "0"
isolation.tools.copy.disable = "TRUE"     # pas de copier
isolation.tools.paste.disable = "TRUE"    # pas de coller
isolation.tools.dnd.disable = "TRUE"      # pas de glisser-déposer
isolation.tools.setGUIOptions.enable = "FALSE"
usb.present = "FALSE"                     # pas de contrôleur USB (surface CVE-2024-22252/3)
sound.present = "FALSE"                   # pas de carte son
floppy0.present = "FALSE"
```

Autres mesures : segments LAN isolés sans adaptateur hôte (VLAN 10/20/30), un seul réseau hôte (MGMT),
pare-feu par défaut « refus » sur pfSense, Windows 7 sans accès Internet entrant, mises à jour de l'hyperviseur.

## 4. Déroulé de l'atelier (60 min, VMs jetables)

Pré-requis : snapshot de `cli01-win7` et `srv01-ubuntu` **avant** l'atelier → retour à l'état initial après.

| # | Exercice | Commande / action | Résultat attendu |
|---|---|---|---|
| 1 | Inventorier les périphériques virtuels | `lspci; lsusb` (srv01) ; Gestionnaire de périphériques (cli01) | Pas de contrôleur USB ni carte son |
| 2 | Tester le presse-papiers | Copier un texte sur l'hôte, coller dans cli01 | Collage impossible (isolation.tools.paste.disable) |
| 3 | Tester les dossiers partagés | VM › Settings › Options › Shared Folders ; `vmware-hgfsclient` sur srv01 | Option désactivée / aucune ressource |
| 4 | Canal backdoor VMware Tools | `vmware-rpctool "info-get guestinfo.test"` (srv01) | Canal présent : il existe toujours, d'où l'importance de patcher les Tools |
| 5 | Différencier réseau et évasion | `ping 192.168.10.50` depuis srv01 → bloqué par pfSense (journal « Block other internal networks ») | Le blocage prouve que la communication VM-VM **réseau** est contrôlée ; ce n'est pas une évasion |
| 6 | Vérifier la version et les correctifs | Help › About ; comparer aux VMSA | Écart de version documenté |
| 7 | Restauration | Revenir au snapshot | VMs identiques à l'état initial |

## 5. Ce qu'il ne faut pas faire

- Ne jamais lancer d'exploit d'évasion sur un hôte personnel ou de production : une évasion réussie donne
  le contrôle du portable, de ses fichiers et de ses autres VMs.
- Les démonstrations d'exploitation réelle se font sur un hôte dédié, isolé, réinstallable, avec autorisation.

## 6. Limites constatées

- Hyperviseur de type 2 : une compromission de Windows 11 compromet toutes les VMs.
- VMware Workstation 17.5.2 n'est pas la dernière version 17.x : à mettre à jour.
- Windows 7 et Ubuntu 25.04 sont hors support : surfaces d'attaque invitées non corrigées.
