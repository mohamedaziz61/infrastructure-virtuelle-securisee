# -*- coding: utf-8 -*-
"""Generates documentation/final_report.pdf (French) from the real lab results."""
import os
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm, mm
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY
from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
                                PageBreak, Image, KeepTogether, ListFlowable, ListItem)
from reportlab.platypus.flowables import HRFlowable
from svglib.svglib import svg2rlg

ROOT = r"C:\Users\azizb\Desktop\projet cloud"
DOC = os.path.join(ROOT, "documentation")
SHOT = os.path.join(DOC, "screenshots")
OUT = os.path.join(DOC, "final_report.pdf")

NAVY = colors.HexColor("#1f3864")
BLUE = colors.HexColor("#2e5090")
LIGHT = colors.HexColor("#eef3fb")
GREEN = colors.HexColor("#1e7a46")
RED = colors.HexColor("#b5271a")
GREY = colors.HexColor("#555555")

ss = getSampleStyleSheet()
H1 = ParagraphStyle("H1", parent=ss["Heading1"], fontSize=15, textColor=NAVY, spaceBefore=14, spaceAfter=6)
H2 = ParagraphStyle("H2", parent=ss["Heading2"], fontSize=12, textColor=BLUE, spaceBefore=8, spaceAfter=4)
BODY = ParagraphStyle("BODY", parent=ss["BodyText"], fontSize=9.5, leading=13, alignment=TA_JUSTIFY, spaceAfter=5)
SMALL = ParagraphStyle("SMALL", parent=ss["BodyText"], fontSize=8, leading=10, textColor=GREY)
CELL = ParagraphStyle("CELL", parent=ss["BodyText"], fontSize=8, leading=10)
CELLH = ParagraphStyle("CELLH", parent=ss["BodyText"], fontSize=8, leading=10, textColor=colors.white, fontName="Helvetica-Bold")
CAP = ParagraphStyle("CAP", parent=ss["BodyText"], fontSize=8, leading=10, textColor=GREY, alignment=TA_CENTER, spaceBefore=3)

story = []

def h1(n, t): story.append(Paragraph(f"{n}. {t}", H1))
def h2(t): story.append(Paragraph(t, H2))
def p(t): story.append(Paragraph(t, BODY))
def sp(h=6): story.append(Spacer(1, h))
def bullets(items):
    story.append(ListFlowable([ListItem(Paragraph(i, BODY), leftIndent=10) for i in items],
                              bulletType="bullet", start="•", leftIndent=12))

def status_cell(s):
    s = s.strip()
    col = GREEN if s.upper().startswith("PASS") else (RED if "FAIL" in s.upper() else GREY)
    return Paragraph(f'<font color="{col.hexval()}"><b>{s}</b></font>', CELL)

def table(headers, rows, widths, statuscol=None):
    data = [[Paragraph(h, CELLH) for h in headers]]
    for r in rows:
        cells = []
        for i, c in enumerate(r):
            if statuscol is not None and i == statuscol:
                cells.append(status_cell(str(c)))
            else:
                cells.append(Paragraph(str(c), CELL))
        data.append(cells)
    t = Table(data, colWidths=widths, repeatRows=1)
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), NAVY),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#b8c4d9")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, LIGHT]),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 3), ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("LEFTPADDING", (0, 0), (-1, -1), 4), ("RIGHTPADDING", (0, 0), (-1, -1), 4),
    ]))
    story.append(t); sp(6)

def image(path, w, caption=None):
    if os.path.exists(path):
        try:
            img = Image(path); iw, ih = img.drawWidth, img.drawHeight
            img.drawWidth = w; img.drawHeight = ih * (w / iw)
            img.hAlign = "CENTER"; story.append(img)
            if caption: story.append(Paragraph(caption, CAP))
            sp(6)
        except Exception as e:
            story.append(Paragraph(f"[image {os.path.basename(path)} : {e}]", SMALL))

# ---------------- PAGE DE GARDE ----------------
story.append(Spacer(1, 3 * cm))
story.append(Paragraph("Déploiement et sécurisation d'une infrastructure virtuelle",
             ParagraphStyle("T", parent=ss["Title"], fontSize=22, textColor=NAVY, alignment=TA_CENTER, leading=28)))
sp(6)
story.append(Paragraph("Pare-feu pfSense · VLAN · Ubuntu durci · TrueNAS ZFS · Docker · Prométhée/Grafana · OpenVPN",
             ParagraphStyle("Sub", parent=ss["Title"], fontSize=12, textColor=BLUE, alignment=TA_CENTER, leading=16)))
sp(10)
story.append(HRFlowable(width="60%", color=BLUE, thickness=1.2))
sp(20)
story.append(Table([
    [Paragraph("<b>Projet</b>", BODY), Paragraph("Infrastructure virtuelle sécurisée (laboratoire)", BODY)],
    [Paragraph("<b>Hyperviseur</b>", BODY), Paragraph("VMware Workstation 17.5.2 sur Windows 11 Pro", BODY)],
    [Paragraph("<b>Date</b>", BODY), Paragraph("19 novembre 2026", BODY)],
    [Paragraph("<b>Membres de l'équipe</b>", BODY), Paragraph("&lt;Nom 1&gt; — &lt;rôle&gt;  ·  &lt;Nom 2&gt; — &lt;rôle&gt;  ·  &lt;Nom 3&gt; — &lt;rôle&gt;", BODY)],
    [Paragraph("<b>Encadrant</b>", BODY), Paragraph("&lt;Nom de l'enseignant&gt;", BODY)],
], colWidths=[4.5 * cm, 11 * cm], style=TableStyle([
    ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#b8c4d9")),
    ("BACKGROUND", (0, 0), (0, -1), LIGHT), ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ("TOPPADDING", (0, 0), (-1, -1), 6), ("BOTTOMPADDING", (0, 0), (-1, -1), 6)])))
sp(14)
story.append(Paragraph("Les champs entre chevrons &lt;…&gt; sont des espaces réservés à compléter.", SMALL))
story.append(PageBreak())

# ---------------- 1. INTRODUCTION ----------------
h1(1, "Introduction")
p("Ce rapport présente la conception, le déploiement, le durcissement et la validation d'une infrastructure "
  "informatique virtuelle simulant l'environnement d'une petite organisation. L'ensemble est construit sur un "
  "unique ordinateur portable à l'aide de VMware Workstation et de Docker, en réutilisant des images ISO "
  "existantes (Windows 7, Ubuntu, TrueNAS, pfSense). L'accent est mis sur la <b>sécurité</b> : segmentation "
  "réseau par VLAN, pare-feu à politique « refus par défaut », chiffrement, authentification par clé, "
  "supervision et accès distant par VPN. Toutes les mesures ont été <b>réellement mises en œuvre et testées</b> ; "
  "les résultats, y compris les échecs et les limites, sont rapportés sans fabrication.")

# ---------------- 2. OBJECTIFS ----------------
h1(2, "Objectifs du projet")
bullets([
    "Déployer un pare-feu central (pfSense) assurant routage inter-VLAN, NAT, DHCP, DNS et VPN.",
    "Segmenter le réseau en VLAN isolés (clients, serveurs, stockage, administration).",
    "Durcir un serveur Ubuntu (SSH par clé, UFW, auditd, fail2ban) hébergeant une application conteneurisée.",
    "Mettre en place un stockage TrueNAS (pool ZFS miroir, dataset chiffré, partage SMB, snapshots).",
    "Superviser l'infrastructure avec Prometheus et Grafana.",
    "Fournir un accès distant sécurisé par OpenVPN.",
    "Documenter un atelier pédagogique sur l'isolation des hyperviseurs et l'évasion de VM.",
    "Valider chaque élément par des tests reproductibles et consigner les preuves.",
])

# ---------------- 3. ENVIRONNEMENT ----------------
h1(3, "Environnement matériel et logiciel")
table(["Élément", "Valeur constatée"], [
    ["Processeur", "Intel Core i7-11800H — 8 cœurs / 16 threads"],
    ["Mémoire vive", "32 Go (déploiement échelonné des VM)"],
    ["Disque", "~100 Go libres ; disques virtuels fins (thin)"],
    ["Système hôte", "Microsoft Windows 11 Professionnel (build 26300)"],
    ["Hyperviseur", "VMware Workstation 17.5.2 build-23775571"],
    ["Conteneurs", "Docker Desktop 4.57 (validation) ; Docker Engine 29.2.1 sur Ubuntu (production)"],
    ["ISO réutilisées", "Windows 7 Pro x64 FR (MLF), Ubuntu 25.04, TrueNAS SCALE 25.10.7, pfSense CE 2.7.2"],
], [4.5 * cm, 11 * cm])
p("Les sommes de contrôle SHA-256 des ISO Ubuntu et TrueNAS ont été vérifiées conformes aux valeurs officielles. "
  "VBS/Hyper-V étant actif sur l'hôte, VMware s'exécute via la plateforme d'hyperviseur Windows.")

# ---------------- 4. ARCHITECTURE ----------------
h1(4, "Architecture réseau")
p("La segmentation est réalisée par des <b>segments L2 isolés</b> (LAN Segments VMware) pour les VLAN 10, 20 et 30, "
  "chacun relié à une interface dédiée de pfSense — équivalent fonctionnel d'un port d'accès par VLAN. VMware "
  "Workstation ne proposant pas de commutateur 802.1Q et le client Windows 7 ne sachant pas étiqueter les trames, "
  "cette approche garantit que <b>tout trafic inter-VLAN traverse le pare-feu</b>. Le réseau d'administration "
  "(VLAN 99) utilise un réseau hôte dédié (VMnet5).")
sp(4)
try:
    drawing = svg2rlg(os.path.join(DOC, "architecture", "diagramme_reseau.svg"))
    if drawing:
        scale = (15.5 * cm) / drawing.width
        drawing.width *= scale; drawing.height *= scale; drawing.scale(scale, scale)
        drawing.hAlign = "CENTER"; story.append(drawing)
        story.append(Paragraph("Figure 1 — Architecture réseau de l'infrastructure virtuelle", CAP))
        sp(6)
except Exception as e:
    story.append(Paragraph(f"[diagramme : {e}]", SMALL))
table(["VLAN", "Rôle", "Sous-réseau", "Passerelle (pfSense)"], [
    ["WAN", "Accès Internet (NAT VMware)", "192.168.101.0/24", "192.168.101.10 → .2"],
    ["10", "Clients Windows", "192.168.10.0/24", "192.168.10.1"],
    ["20", "Serveurs / applications", "192.168.20.0/24", "192.168.20.1"],
    ["30", "Stockage TrueNAS", "192.168.30.0/24", "192.168.30.1"],
    ["99", "Administration", "192.168.99.0/24", "192.168.99.1"],
    ["VPN", "Accès distant OpenVPN", "10.8.0.0/24", "10.8.0.1"],
], [1.6 * cm, 5.4 * cm, 4 * cm, 4.5 * cm])

# ---------------- 5. VMs ----------------
h1(5, "Infrastructure VMware")
table(["VM", "Rôle", "Ressources", "État"], [
    ["fw01-pfsense", "Pare-feu / routeur / VPN", "2 vCPU · 2 Go · 16 Go", "Opérationnel"],
    ["srv01-ubuntu", "Ubuntu 25.04 · Docker · supervision", "2 vCPU · 4 Go · 25 Go", "Opérationnel"],
    ["cli01-win7", "Client Windows 7 Pro RTM", "2 vCPU · 2 Go · 30 Go", "Opérationnel"],
    ["nas01-truenas", "TrueNAS SCALE 25.10.7", "2 vCPU · 8 Go · 20+10+10 Go", "Opérationnel"],
], [3.2 * cm, 6 * cm, 4 * cm, 2.3 * cm])
p("Chaque VM est durcie au niveau de l'hyperviseur (voir §14) : dossiers partagés, presse-papiers, glisser-déposer, "
  "USB et audio désactivés. Les quatre VM sont démarrées dans l'ordre de dépendance (pfSense d'abord) via le "
  "script <font face='Courier'>scripts/00_start_lab.ps1</font>.")
image(os.path.join(SHOT, "pfsense_console_interfaces.png"), 13 * cm,
      "Figure 2 — Console pfSense : les cinq interfaces aux adresses planifiées")

# ---------------- 6. WINDOWS 7 ----------------
h1(6, "Sécurisation de Windows 7")
p("Installation automatisée (autounattend.xml). Durcissement appliqué au premier démarrage via un service "
  "LocalSystem éphémère, injecté hors ligne (disque monté en lecture/écriture depuis un conteneur).")
table(["Mesure", "Résultat", "Statut"], [
    ["Installation non assistée", "Windows 7 Pro x64 — 6.1.7600 (RTM, sans SP1)", "PASS"],
    ["Pare-feu Windows (3 profils)", "Actif, entrant bloqué, journalisation", "PASS"],
    ["Audit des événements", "Toutes catégories succès+échec (4688, 5156…)", "PASS"],
    ["Politique de mots de passe", "12 car. min, verrouillage 5 essais / 15 min", "PASS"],
    ["Comptes locaux", "Invité désactivé, admin + utilisateur standard", "PASS"],
    ["windows_exporter v0.18.1", "Service RUNNING, métriques depuis srv01", "PASS"],
    ["Sysmon 15.22", "Échec (0xC0000139) — incompatible Win7 RTM", "FAIL"],
], [6.2 * cm, 7.3 * cm, 2 * cm], statuscol=2)
p("<b>Limites.</b> Windows 7 RTM (sans SP1) est hors support : Sysmon 15 ne démarre pas (aucune version antérieure "
  "de source officielle), et le client SMB ne négocie pas avec le serveur TrueNAS durci (voir §8). L'audit natif "
  "prend le relais de Sysmon. Windows 7 est maintenu isolé en VLAN 10, sans exposition entrante depuis Internet.")

# ---------------- 7. UBUNTU ----------------
h1(7, "Sécurisation d'Ubuntu")
p("Serveur Ubuntu 25.04 construit par debootstrap, démarré via systemd-boot, puis durci par script "
  "(<font face='Courier'>scripts/10_ubuntu_harden.sh</font>).")
table(["Mesure", "Résultat", "Statut"], [
    ["SSH par clé uniquement", "passwordauth=no, root interdit, AllowUsers sysadmin", "PASS"],
    ["Pare-feu UFW (refus entrant)", "22 depuis MGMT/VPN seulement", "PASS"],
    ["DOCKER-USER (ports Docker)", "Filtre les ports publiés qui contournent UFW", "PASS"],
    ["auditd", "12 règles ; événements identity/sshd/docker/root", "PASS"],
    ["fail2ban", "Jail sshd active", "PASS"],
    ["rsyslog", "Journaux dédiés sécurité et pare-feu", "PASS"],
    ["Moindre privilège", "root verrouillé ; sudo par clé", "PASS"],
], [6.2 * cm, 7.3 * cm, 2 * cm], statuscol=2)

# ---------------- 8. TRUENAS ----------------
h1(8, "TrueNAS — installation et stockage")
p("TrueNAS SCALE 25.10.7. Toute la configuration a été réalisée par l'<b>API middleware (midclt)</b> via SSH par "
  "clé. L'accès SSH a été activé hors ligne (le disque système, sauvegardé, a été monté temporairement sur srv01 "
  "qui dispose d'OpenZFS) : clé publique ajoutée, service SSH activé et tâche POSTINIT garantissant son démarrage.")
table(["Élément", "Résultat", "Statut"], [
    ["Pool ZFS miroir", "tank ONLINE, miroir sdb+sdc, sain", "PASS"],
    ["Dataset chiffré", "tank/share — AES-256-GCM, clé chargée", "PASS"],
    ["Partage SMB", "lab_share, service cifs RUNNING + au boot", "PASS"],
    ["Comptes & ACL", "smbuser1 + groupe smbshare, ACL NFSv4", "PASS"],
    ["Accès SMB (srv01, SMB3)", "liste, écriture, lecture", "PASS"],
    ["Snapshots", "tâche horaire (rétention 2 sem.) + baseline", "PASS"],
    ["Récupération par snapshot", "suppression SMB puis rollback : fichier restauré", "PASS"],
    ["Persistance après reboot", "SSH, déverrouillage auto, SMB : OK (~65 s)", "PASS"],
], [5.3 * cm, 8.2 * cm, 2 * cm], statuscol=2)
p("<b>Limite.</b> Un miroir ZFS <i>virtuel</i> protège de la perte logique mais pas d'une panne du disque physique "
  "unique du portable. Disques virtuels de test uniquement, aucune donnée personnelle.")

# ---------------- 9. DOCKER ----------------
h1(9, "Déploiement de l'application conteneurisée")
p("Choix d'architecture : <b>Docker Engine sur la VM Ubuntu (VLAN 20)</b>, derrière pfSense, afin que tout le "
  "trafic traverse le pare-feu (segmentation réelle). Docker Desktop n'a servi qu'à valider la pile avant "
  "déploiement. Application de démonstration « Lab Inventory » : Flask + PostgreSQL, via Docker Compose.")
table(["Test", "Résultat", "Statut"], [
    ["Santé applicative (/health)", "{\"db\":\"ok\",\"status\":\"ok\"} HTTP 200", "PASS"],
    ["Écriture / persistance des données", "données conservées après recréation", "PASS"],
    ["Redémarrage automatique (crash)", "restart policy, conteneur relancé", "PASS"],
    ["Base non exposée au réseau", "réseau interne, port 5432 injoignable", "PASS"],
    ["Durcissement conteneur", "non-root, rootfs read-only, cap_drop ALL", "PASS"],
    ["Secrets protégés", "répertoire 700, lecture refusée aux autres", "PASS"],
], [6.2 * cm, 7.3 * cm, 2 * cm], statuscol=2)

# ---------------- 10. SUPERVISION ----------------
h1(10, "Supervision — Prometheus et Grafana")
p("Pile de supervision (Docker Compose) sur srv01 : Prometheus, Grafana, node_exporter, blackbox_exporter et "
  "snmp_exporter. Prometheus n'est pas exposé (loopback) ; Grafana n'est accessible que depuis MGMT/VPN.")
table(["Test", "Résultat", "Statut"], [
    ["Cibles Prometheus", "12 cibles « up » (srv01, cli01, pfSense SNMP, app, sondes)", "PASS"],
    ["Métriques réelles", "CPU, RAM, disque, réseau, interfaces pfSense", "PASS"],
    ["Règles d'alerte", "TargetDown, ServiceProbeFailed, HighMemory, DiskAlmostFull", "PASS"],
    ["Grafana protégé", "accès anonyme refusé (401), source + tableau provisionnés", "PASS"],
    ["Prometheus non exposé", "9090 en loopback uniquement", "PASS"],
], [6.2 * cm, 7.3 * cm, 2 * cm], statuscol=2)
image(os.path.join(SHOT, "grafana_login.jpg"), 10 * cm,
      "Figure 3 — Grafana déployé et protégé par authentification (VLAN 20)")

# ---------------- 11. PFSENSE ----------------
h1(11, "Pare-feu pfSense")
p("pfSense assure le routage inter-VLAN, le NAT, le DHCP, le DNS (résolveur Unbound avec validation DNSSEC) et les "
  "politiques de filtrage. 96 règles chargées, avec blocage par défaut inter-VLAN et autorisations explicites.")
table(["Fonction", "Résultat", "Statut"], [
    ["Interfaces (5)", "WAN/VLAN10/20/30/99 aux adresses planifiées", "PASS"],
    ["NAT + Internet", "sortie Internet via WAN, 0 % de perte", "PASS"],
    ["DNS + DNSSEC", "résolution interne/externe ; domaine erroné → SERVFAIL", "PASS"],
    ["DHCP", "VLAN 10 et VLAN 30 (réservations)", "PASS"],
    ["SNMP", "exposé à Prometheus sur VLAN 20 uniquement", "PASS"],
    ["Pare-feu (refus par défaut)", "96 règles, inter-VLAN bloqué sauf autorisations", "PASS"],
], [5.6 * cm, 7.9 * cm, 2 * cm], statuscol=2)
p("<b>Correctifs de sécurité en cours de test.</b> Deux règles ICMP initialement trop larges (autorisation vers "
  "tout 192.168.0.0/16) ont été détectées puis restreintes à des alias précis (MONITORED_HOSTS, VPN_SERVERS), "
  "empêchant un hôte VLAN 20 ou un client VPN de joindre le réseau d'administration.")

# ---------------- 12. VLAN ----------------
h1(12, "Segmentation VLAN — tests")
p("Tests de connectivité autorisée/bloquée exécutés depuis les VM elles-mêmes (Windows 7 en VLAN 10, Ubuntu en "
  "VLAN 20) et depuis le VPN.")
table(["Flux testé", "Attendu", "Résultat", "Statut"], [
    ["VLAN10 → application srv01:8080", "autorisé", "OPEN", "PASS"],
    ["VLAN10 → Grafana / SSH / admin pfSense", "bloqué", "BLOCKED", "PASS"],
    ["VLAN10 → interface TrueNAS (443)", "bloqué", "BLOCKED", "PASS"],
    ["VLAN20 → cli01:9182 (supervision)", "autorisé", "OPEN", "PASS"],
    ["VLAN20 → MGMT / WAN / firewall", "bloqué", "BLOCKED", "PASS"],
    ["DNS interne/externe via pfSense", "résolu", "OK", "PASS"],
    ["Contournement DNS direct (1.1.1.1:53)", "bloqué", "BLOCKED", "PASS"],
], [6.7 * cm, 2.6 * cm, 2.4 * cm, 1.8 * cm], statuscol=3)

# ---------------- 13. OPENVPN ----------------
h1(13, "Configuration OpenVPN")
p("Serveur d'accès distant sur pfSense. Authentification par <b>certificat client X.509</b> (CA du lab) renforcée "
  "par <b>tls-crypt</b> : sans certificat ni clé, le serveur ne répond pas. Testé depuis un client OpenVPN "
  "entrant par le WAN, comme un utilisateur distant.")
table(["Test", "Résultat", "Statut"], [
    ["Établissement du tunnel", "TLS 1.3, données AES-256-GCM, IP 10.8.0.2", "PASS"],
    ["Routes poussées limitées", "VLAN 20 et VLAN 30 uniquement", "PASS"],
    ["VPN → application / Grafana", "autorisé", "PASS"],
    ["VPN → SMB TrueNAS (445)", "autorisé", "PASS"],
    ["VPN → MGMT / VLAN10 (client forçant les routes)", "bloqué", "PASS"],
    ["Règle ICMP VPN trop large", "détectée → restreinte à VPN_SERVERS", "FAIL→corrigé"],
], [6.6 * cm, 6.9 * cm, 2 * cm], statuscol=2)
p("<b>Rappel.</b> Le serveur peut être repassé en « certificat + identifiant/mot de passe » dans l'interface "
  "pfSense (mode « Remote Access SSL/TLS + User Auth ») ; l'utilisateur vpnuser1 existe déjà.")

# ---------------- 14. VM ESCAPE ----------------
h1(14, "Atelier VM-to-VM / évasion d'hyperviseur")
p("Un atelier pédagogique défensif et contrôlé (document <font face='Courier'>09_atelier_vm_escape.md</font>) "
  "distingue l'<i>évasion de VM</i> (exécution de code hors de la VM via une faille de l'hyperviseur ou d'un "
  "périphérique virtuel) du simple <i>trafic réseau</i> entre VM (contrôlé par pfSense). Il couvre la surface "
  "d'attaque (USB/EHCI, dossiers partagés HGFS, presse-papiers, VMware Tools, hôte non corrigé) avec CVE de "
  "référence, et les contre-mesures appliquées à chaque VM :")
bullets([
    "<font face='Courier'>isolation.tools.hgfs/copy/paste/dnd.disable = TRUE</font> (pas de partage, presse-papiers, glisser-déposer)",
    "<font face='Courier'>usb.present = FALSE</font>, <font face='Courier'>sound.present = FALSE</font> (surface de périphériques réduite)",
    "Segments L2 isolés, pare-feu « refus par défaut », mises à jour de l'hyperviseur.",
])
p("Aucune exploitation réelle n'est menée contre l'hôte ; les exercices utilisent des snapshots jetables.")

# ---------------- 15. SECURITY POLICIES ----------------
h1(15, "Politiques de sécurité")
bullets([
    "<b>Moindre privilège</b> : accès administratif restreint au VLAN 99 ; comptes dédiés ; root verrouillé.",
    "<b>Refus par défaut</b> : tout trafic inter-VLAN bloqué sauf autorisation explicite et justifiée.",
    "<b>Authentification forte</b> : SSH par clé (mot de passe désactivé), VPN par certificat + tls-crypt.",
    "<b>Chiffrement</b> : dataset TrueNAS AES-256-GCM ; tunnels TLS 1.3 / AES-256-GCM.",
    "<b>Journalisation & audit</b> : auditd, rsyslog, journaux pare-feu, audit Windows, SNMP supervisé.",
    "<b>Non-exposition</b> : services internes jamais publiés sur Internet ; bases et Prometheus en loopback.",
    "<b>Secrets</b> : mots de passe et clés générés aléatoirement, stockés hors du code (dossier secrets).",
])

# ---------------- 16. TESTS ----------------
h1(16, "Tests et résultats — synthèse")
p("Chaque test comporte objectif, procédure, résultat attendu, résultat réel et statut ; les preuves brutes sont "
  "dans <font face='Courier'>documentation/tests/</font>. Synthèse par domaine :")
table(["Domaine", "Tests", "PASS", "FAIL (traité)"], [
    ["pfSense (réseau, NAT, DNS, DHCP, VPN, SNMP)", "6", "6", "0"],
    ["Segmentation VLAN (VLAN10/20/VPN)", "≈24", "≈24", "2 règles corrigées"],
    ["Windows 7 (durcissement, exporter)", "10", "8", "2 (limites legacy)"],
    ["Ubuntu (SSH, UFW, auditd, fail2ban…)", "7", "7", "0"],
    ["Application Docker", "7", "7", "0"],
    ["Supervision Prometheus/Grafana", "6", "5", "1 corrigé"],
    ["TrueNAS (pool, chiffrement, SMB, snapshots)", "12", "12", "0"],
    ["OpenVPN", "9", "8", "1 corrigé"],
], [7 * cm, 2 * cm, 1.8 * cm, 3.7 * cm])
p("Les « FAIL corrigés » sont des défauts réels détectés par les tests (règles pare-feu trop larges, méthode de "
  "rechargement de Prometheus) puis corrigés et re-testés — ils illustrent la valeur de la démarche de test. Les "
  "« limites legacy » (Windows 7 RTM) ne sont pas corrigées par principe de sécurité (voir §17).")

# ---------------- 17. LIMITES ----------------
h1(17, "Limites de sécurité constatées")
bullets([
    "<b>Windows 7 RTM sans SP1</b> (hors support) : Sysmon 15 incompatible ; le client SMB ne négocie pas avec le "
    "serveur TrueNAS durci (SMB1 et NTLMv1 désactivés). Le pare-feu autorise bien VLAN10→445 (couche réseau "
    "validée), mais la session échoue côté client. Ne PAS affaiblir le serveur pour un client obsolète ; "
    "correctif : SP1 (KB976932) ou client SMB3.",
    "<b>Ubuntu 25.04 en fin de vie</b> : plus de correctifs ; dépôt pointé vers l'archive officielle.",
    "<b>Hyperviseur de type 2</b> : une compromission de l'hôte Windows 11 compromettrait toutes les VM.",
    "<b>Miroir ZFS virtuel</b> : pas de protection contre une panne du disque physique unique.",
    "<b>Certificats auto-signés</b> (pfSense, TrueNAS, Grafana) : à signer par la CA du lab pour les navigateurs.",
    "<b>VPN testé en local</b> via le NAT VMware ; un accès depuis Internet nécessiterait une redirection de port "
    "volontairement non configurée.",
    "<b>VMware Workstation 17.5.2</b> n'est pas la dernière 17.x : mise à jour recommandée.",
])

# ---------------- 18. CONCLUSION ----------------
h1(18, "Conclusion")
p("L'infrastructure virtuelle sécurisée a été construite, interconnectée, durcie et démontrée de bout en bout : "
  "un pare-feu pfSense segmente quatre VLAN avec une politique de refus par défaut, un serveur Ubuntu durci "
  "héberge une application conteneurisée et la supervision Prometheus/Grafana, un serveur TrueNAS fournit un "
  "stockage ZFS miroir chiffré avec partage SMB et snapshots, et un VPN OpenSSL/OpenVPN offre un accès distant "
  "fortement authentifié. La démarche de test a mis au jour des défauts réels — deux règles pare-feu trop "
  "permissives et une méthode de rechargement inadaptée — qui ont été corrigés et re-validés. Les limites "
  "(systèmes legacy hors support, hyperviseur de type 2, redondance virtuelle) sont documentées honnêtement. "
  "L'ensemble constitue un laboratoire fonctionnel, reproductible et pédagogique de sécurité des infrastructures.")

# ---------------- 19. ASSESSMENT ----------------
h1(19, "Tableau d'évaluation des exigences")
table(["Exigence du cahier des charges", "État", "Preuve"], [
    ["Client Windows 7", "Réalisé", "§6 · cli01_evidence"],
    ["Serveur Ubuntu durci", "Réalisé", "§7 · T_srv01"],
    ["Stockage TrueNAS (ZFS, SMB)", "Réalisé", "§8 · T_truenas"],
    ["Application conteneurisée Docker", "Réalisé", "§9 · T_docker"],
    ["Pare-feu pfSense", "Réalisé", "§11 · T_pfsense"],
    ["Supervision Prometheus/Grafana", "Réalisé", "§10 · T_monitoring"],
    ["Accès distant OpenVPN", "Réalisé", "§13 · T_openvpn"],
    ["Segmentation réseau VLAN", "Réalisé", "§12"],
    ["Sécurité interne et audit", "Réalisé", "§6, §7 · auditd/Sysmon*"],
    ["Atelier évasion VM-to-VM", "Réalisé", "§14 · 09_atelier"],
    ["Snapshots ZFS", "Réalisé", "§8 (N7/N8)"],
    ["Chiffrement du stockage", "Réalisé", "§8 (AES-256-GCM)"],
    ["Tests documentés avec preuves", "Réalisé", "§16 · documentation/tests"],
    ["Rapport final (ce document)", "Réalisé", "final_report.pdf"],
], [8.5 * cm, 2.6 * cm, 4.4 * cm])
story.append(Paragraph("* Sysmon non fonctionnel sur Windows 7 RTM (limite documentée, §17) ; l'audit natif assure la journalisation.", SMALL))

sp(10)
story.append(HRFlowable(width="100%", color=BLUE, thickness=0.8))
story.append(Paragraph("Rapport généré à partir des résultats réels du laboratoire — 19 novembre 2026. "
             "Les captures et journaux bruts sont dans documentation/ (architecture, screenshots, tests, configurations).", SMALL))


def footer(canvas, doc):
    canvas.saveState()
    canvas.setFont("Helvetica", 7.5); canvas.setFillColor(GREY)
    canvas.drawString(2 * cm, 1.1 * cm, "Déploiement et sécurisation d'une infrastructure virtuelle")
    canvas.drawRightString(A4[0] - 2 * cm, 1.1 * cm, "Page %d" % doc.page)
    canvas.setStrokeColor(colors.HexColor("#b8c4d9")); canvas.line(2 * cm, 1.4 * cm, A4[0] - 2 * cm, 1.4 * cm)
    canvas.restoreState()

doc = SimpleDocTemplate(OUT, pagesize=A4, leftMargin=2 * cm, rightMargin=2 * cm,
                        topMargin=1.8 * cm, bottomMargin=1.8 * cm,
                        title="Deploiement et securisation d'une infrastructure virtuelle",
                        author="Projet Cloud")
doc.build(story, onFirstPage=footer, onLaterPages=footer)
print("PDF written:", OUT, os.path.getsize(OUT), "bytes")
