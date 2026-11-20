"""Generates first-boot configuration for the lab:
  - PKI (CA, OpenVPN server cert, VPN client cert) + tls-crypt key
  - pfSense config.xml  -> secrets/generated/pfsense/config.xml  (+ FAT16 ECL disk image)
  - Ubuntu autoinstall   -> ISO/seed/ubuntu-cidata/{user-data,meta-data}
  - Windows 7 unattend   -> ISO/seed/win7-unattend/autounattend.xml
  - OpenVPN client       -> secrets/generated/vpnuser1.ovpn
Secrets come from secrets/credentials.json and never get printed."""
import base64, json, os, secrets, struct, subprocess, textwrap
from pathlib import Path

ROOT = Path(r"C:\Users\azizb\Desktop\projet cloud")
GEN = ROOT / "secrets" / "generated"
PKI = GEN / "pki"
SEED = ROOT / "ISO" / "seed"
OPENSSL = r"C:\cygwin64\bin\openssl.exe"
for d in (GEN, PKI, GEN / "pfsense", SEED / "ubuntu-cidata", SEED / "win7-unattend"):
    d.mkdir(parents=True, exist_ok=True)

cred_file = ROOT / "secrets" / "credentials.json"
cred = json.loads(cred_file.read_text())
for k in ("vpnuser1", "snmp_community"):
    cred.setdefault(k, secrets.token_urlsafe(12).replace("-", "x").replace("_", "y"))
cred_file.write_text(json.dumps(cred, indent=2))
pubkey = Path(r"C:\Users\azizb\.ssh\projet_cloud_ed25519.pub").read_text().strip()


def wsl_hash(pw, method):
    code = f"import crypt,sys;print(crypt.crypt(sys.stdin.read(),crypt.mksalt(crypt.{method})))"
    out = subprocess.run(["wsl", "-d", "Ubuntu", "--", "python3", "-W", "ignore", "-c", code],
                         input=pw, capture_output=True, text=True, check=True).stdout.strip()
    return out


def bcrypt(pw):  # PHP password_verify() expects the $2y$ prefix (same algorithm as $2b$)
    return "$2y$" + wsl_hash(pw, "METHOD_BLOWFISH")[4:]


(PKI / "openssl.cnf").write_text("[req]\ndistinguished_name=dn\n[dn]\n")
OSSL_ENV = {**os.environ, "OPENSSL_CONF": str(PKI / "openssl.cnf").replace("\\", "/")}


def ossl(*args):
    r = subprocess.run([OPENSSL, *args], capture_output=True, text=True, env=OSSL_ENV)
    if r.returncode: raise RuntimeError(f"openssl {args[0]} failed: {r.stderr[-400:]}")


def p(name):
    return str(PKI / name).replace("\\", "/")


# ---------------------------------------------------------------- PKI
if not (PKI / "ca.crt").exists():
    ossl("ecparam", "-name", "prime256v1", "-genkey", "-noout", "-out", p("ca.key"))
    ossl("req", "-x509", "-new", "-key", p("ca.key"), "-sha256", "-days", "3650", "-subj", "/CN=LAB-ROOT-CA/O=Projet Cloud",
         "-addext", "basicConstraints=critical,CA:TRUE", "-addext", "keyUsage=critical,keyCertSign,cRLSign", "-out", p("ca.crt"))
    for name, cn, eku in (("server", "fw01.lab.local", "serverAuth"), ("vpnuser1", "vpnuser1", "clientAuth")):
        ossl("ecparam", "-name", "prime256v1", "-genkey", "-noout", "-out", p(f"{name}.key"))
        ossl("req", "-new", "-key", p(f"{name}.key"), "-subj", f"/CN={cn}/O=Projet Cloud", "-out", p(f"{name}.csr"))
        (PKI / f"{name}.ext").write_text(f"basicConstraints=CA:FALSE\nkeyUsage=critical,digitalSignature,keyAgreement\n"
                                          f"extendedKeyUsage={eku}\nsubjectAltName=DNS:{cn}\n")
        ossl("x509", "-req", "-in", p(f"{name}.csr"), "-CA", p("ca.crt"), "-CAkey", p("ca.key"), "-CAcreateserial",
             "-days", "825", "-sha256", "-extfile", p(f"{name}.ext"), "-out", p(f"{name}.crt"))
    # OpenVPN static key v1 (2048 bits) for tls-crypt
    hx = secrets.token_hex(256)
    (PKI / "tls-crypt.key").write_text("-----BEGIN OpenVPN Static key V1-----\n" +
                                       "\n".join(hx[i:i + 32] for i in range(0, len(hx), 32)) +
                                       "\n-----END OpenVPN Static key V1-----\n")
rd = lambda n: (PKI / n).read_text()
b64 = lambda s: base64.b64encode(s.encode()).decode()

# ---------------------------------------------------------------- pfSense config.xml
def rule(iface, descr, typ="pass", proto=None, src=None, dst=None, dport=None, log=False, tracker=[1700000000]):
    tracker[0] += 1
    def ep(e):
        if e is None: return "<any></any>"
        if e.startswith("net:"): return f"<network>{e[4:]}</network>"
        return f"<address>{e}</address>"
    x = f"<rule><tracker>{tracker[0]}</tracker><type>{typ}</type><interface>{iface}</interface><ipprotocol>inet</ipprotocol>"
    if proto: x += f"<protocol>{proto}</protocol>"
    x += f"<source>{ep(src)}</source><destination>{ep(dst)}{f'<port>{dport}</port>' if dport else ''}</destination>"
    if log: x += "<log></log>"
    return x + f"<descr><![CDATA[{descr}]]></descr></rule>"

R = []
R.append(rule("wan", "OpenVPN remote access", proto="udp", dst="net:wanip", dport="1194"))
for ifc in ("lan", "opt1", "opt2"):
    R.append(rule(ifc, "DNS to gateway", proto="tcp/udp", src=f"net:{ifc}", dst=f"net:{ifc}ip", dport="53"))
    R.append(rule(ifc, "NTP to gateway", proto="udp", src=f"net:{ifc}", dst=f"net:{ifc}ip", dport="123"))
# VLAN10 clients
R += [rule("lan", "Clients -> App srv01:8080", proto="tcp", src="net:lan", dst="192.168.20.10", dport="8080"),
      rule("lan", "Clients -> NAS SMB", proto="tcp", src="net:lan", dst="192.168.30.10", dport="445"),
      rule("lan", "Allow scrape replies / ping gw", proto="icmp", src="net:lan", dst="net:lanip")]
# VLAN20 servers
R += [rule("opt1", "Prometheus -> windows_exporter", proto="tcp", src="192.168.20.10", dst="net:lan", dport="9182"),
      rule("opt1", "Prometheus -> pfSense SNMP", proto="udp", src="192.168.20.10", dst="net:opt1ip", dport="161"),
      rule("opt1", "Blackbox -> NAS https/smb", proto="tcp", src="192.168.20.10", dst="192.168.30.10", dport="443"),
      rule("opt1", "Blackbox -> NAS smb", proto="tcp", src="192.168.20.10", dst="192.168.30.10", dport="445"),
      rule("opt1", "Blackbox ICMP to monitored hosts", proto="icmp", src="192.168.20.10", dst="MONITORED_HOSTS")]
# block access to firewall + other internal nets, then Internet web only
for ifc in ("lan", "opt1", "opt2"):
    R.append(rule(ifc, "Block access to firewall", typ="block", src=f"net:{ifc}", dst="(self)", log=True))
    R.append(rule(ifc, "Block other internal networks", typ="block", src=f"net:{ifc}", dst="RFC1918", log=True))
    R.append(rule(ifc, "Internet HTTP/HTTPS", proto="tcp", src=f"net:{ifc}", dport="WEB_PORTS"))
    R.append(rule(ifc, "Internet ICMP", proto="icmp", src=f"net:{ifc}"))
R.append(rule("opt3", "Management: full admin access", src="net:opt3"))
R += [rule("openvpn", "VPN -> App + Grafana", proto="tcp", src="10.8.0.0/24", dst="192.168.20.10", dport="VPN_APP_PORTS"),
      rule("openvpn", "VPN -> NAS SMB", proto="tcp", src="10.8.0.0/24", dst="192.168.30.10", dport="445"),
      rule("openvpn", "VPN ICMP to VPN servers only", proto="icmp", src="10.8.0.0/24", dst="VPN_SERVERS")]
# '(self)' is written as a special address in pfSense XML
rules_xml = "\n".join(R).replace("<address>(self)</address>", "<network>(self)</network>")

def iface(name, ifn, ip, descr, extra=""):
    return (f"<{name}><enable></enable><if>{ifn}</if><descr><![CDATA[{descr}]]></descr>"
            f"<ipaddr>{ip}</ipaddr><subnet>24</subnet>{extra}</{name}>")

admin_hash = bcrypt(cred["pfsense_admin"])
vpn_hash = bcrypt(cred["vpnuser1"])
config = f"""<?xml version="1.0"?>
<pfsense>
<version>23.3</version>
<lastchange></lastchange>
<system>
  <optimization>normal</optimization><hostname>fw01</hostname><domain>lab.local</domain>
  <dnsserver>9.9.9.9</dnsserver><dnsserver>1.1.1.1</dnsserver><dnsallowoverride></dnsallowoverride>
  <group><name>all</name><description><![CDATA[All Users]]></description><scope>system</scope><gid>1998</gid><member>0</member><member>2000</member></group>
  <group><name>admins</name><description><![CDATA[System Administrators]]></description><scope>system</scope><gid>1999</gid><member>0</member><priv>page-all</priv></group>
  <user><name>admin</name><descr><![CDATA[System Administrator]]></descr><scope>system</scope><groupname>admins</groupname>
    <bcrypt-hash>{admin_hash}</bcrypt-hash><uid>0</uid><priv>user-shell-access</priv><authorizedkeys>{b64(pubkey)}</authorizedkeys></user>
  <user><name>vpnuser1</name><descr><![CDATA[VPN remote user]]></descr><scope>user</scope>
    <bcrypt-hash>{vpn_hash}</bcrypt-hash><uid>2000</uid><cert>vpnuser1cert</cert></user>
  <nextuid>2001</nextuid><nextgid>2000</nextgid>
  <timeservers>pool.ntp.org</timeservers><timezone>Africa/Tunis</timezone>
  <webgui><protocol>https</protocol><loginautocomplete></loginautocomplete><port>443</port><max_procs>2</max_procs>
    <noantilockout></noantilockout><ssl-certref>webguicert</ssl-certref></webgui>
  <disablesegmentationoffloading></disablesegmentationoffloading><disablelargereceiveoffloading></disablelargereceiveoffloading>
  <ssh><enable>enabled</enable><sshdkeyonly>enabled</sshdkeyonly><port>22</port></ssh>
  <already_run_config_upgrade></already_run_config_upgrade>
  <hn_altq_enable></hn_altq_enable><powerd_ac_mode>hadp</powerd_ac_mode>
  <bogons><interval>monthly</interval></bogons>
</system>
<interfaces>
  {iface("wan","em0","192.168.101.10","WAN","<gateway>WANGW</gateway><blockbogons></blockbogons>")}
  {iface("lan","em1","192.168.10.1","VLAN10_CLIENTS")}
  {iface("opt1","em2","192.168.20.1","VLAN20_SERVERS")}
  {iface("opt2","em3","192.168.30.1","VLAN30_STORAGE")}
  {iface("opt3","em4","192.168.99.1","VLAN99_MGMT")}
</interfaces>
<gateways><gateway_item><interface>wan</interface><gateway>192.168.101.2</gateway><name>WANGW</name><weight>1</weight>
  <ipprotocol>inet</ipprotocol><descr><![CDATA[VMware NAT gateway]]></descr></gateway_item><defaultgw4>WANGW</defaultgw4></gateways>
<staticroutes></staticroutes>
<dhcpd>
  <lan><enable></enable><range><from>192.168.10.100</from><to>192.168.10.199</to></range>
    <dnsserver>192.168.10.1</dnsserver><gateway>192.168.10.1</gateway><domain>lab.local</domain><ntpserver>192.168.10.1</ntpserver>
    <staticmap><mac>00:50:56:2a:10:50</mac><ipaddr>192.168.10.50</ipaddr><hostname>cli01</hostname><descr><![CDATA[Windows 7 client]]></descr></staticmap>
  </lan>
</dhcpd>
<unbound><enable></enable><dnssec></dnssec><active_interface>lan,opt1,opt2,opt3,openvpn,lo0</active_interface>
  <outgoing_interface>wan</outgoing_interface><system_domain_local_zone_type>transparent</system_domain_local_zone_type>
  <hosts><host>srv01</host><domain>lab.local</domain><ip>192.168.20.10</ip><descr><![CDATA[Ubuntu server]]></descr><aliases></aliases></hosts>
  <hosts><host>nas01</host><domain>lab.local</domain><ip>192.168.30.10</ip><descr><![CDATA[TrueNAS]]></descr><aliases></aliases></hosts>
  <hosts><host>fw01</host><domain>lab.local</domain><ip>192.168.99.1</ip><descr><![CDATA[pfSense mgmt]]></descr><aliases></aliases></hosts>
</unbound>
<snmpd><syslocation>Lab projet cloud</syslocation><syscontact>admin</syscontact><rocommunity>{cred['snmp_community']}</rocommunity>
  <pollport>161</pollport><enable></enable><bindip>opt1</bindip><modules><mibii></mibii><netgraph></netgraph><pf></pf><hostres></hostres><ucd></ucd><regex></regex></modules></snmpd>
<nat><outbound><mode>automatic</mode></outbound></nat>
<aliases>
  <alias><name>RFC1918</name><type>network</type><address>10.0.0.0/8 172.16.0.0/12 192.168.0.0/16</address><descr><![CDATA[Private networks]]></descr><detail><![CDATA[||]]></detail></alias>
  <alias><name>WEB_PORTS</name><type>port</type><address>80 443</address><descr><![CDATA[HTTP/HTTPS]]></descr><detail><![CDATA[|]]></detail></alias>
  <alias><name>VPN_APP_PORTS</name><type>port</type><address>8080 3000</address><descr><![CDATA[App + Grafana]]></descr><detail><![CDATA[|]]></detail></alias>
</aliases>
<filter>
{rules_xml}
</filter>
<syslog><filterdescriptions>1</filterdescriptions><nentries>500</nentries><logall></logall></syslog>
<ca><refid>labca</refid><descr><![CDATA[LAB-ROOT-CA]]></descr><trust>disabled</trust><randomserial>enabled</randomserial>
  <crt>{b64(rd('ca.crt'))}</crt><prv>{b64(rd('ca.key'))}</prv><serial>10</serial></ca>
<cert><refid>ovpnservercert</refid><descr><![CDATA[OpenVPN server fw01]]></descr><type>server</type><caref>labca</caref>
  <crt>{b64(rd('server.crt'))}</crt><prv>{b64(rd('server.key'))}</prv></cert>
<cert><refid>webguicert</refid><descr><![CDATA[webConfigurator fw01]]></descr><type>server</type><caref>labca</caref>
  <crt>{b64(rd('server.crt'))}</crt><prv>{b64(rd('server.key'))}</prv></cert>
<cert><refid>vpnuser1cert</refid><descr><![CDATA[vpnuser1]]></descr><type>user</type><caref>labca</caref>
  <crt>{b64(rd('vpnuser1.crt'))}</crt></cert>
<openvpn><openvpn-server>
  <vpnid>1</vpnid><mode>server_tls</mode><protocol>UDP4</protocol><dev_mode>tun</dev_mode>
  <interface>wan</interface><ipaddr></ipaddr><local_port>1194</local_port><description><![CDATA[Remote access VPN]]></description>
  <custom_options></custom_options><tls>{b64(rd('tls-crypt.key'))}</tls><tls_type>crypt</tls_type>
  <caref>labca</caref><crlref></crlref><certref>ovpnservercert</certref><dh_length>none</dh_length><ecdh_curve>prime256v1</ecdh_curve>
  <cert_depth>1</cert_depth><strictusercn>yes</strictusercn><remote_cert_tls>yes</remote_cert_tls>
  <data_ciphers>AES-256-GCM,AES-128-GCM,CHACHA20-POLY1305</data_ciphers><data_ciphers_fallback>AES-256-GCM</data_ciphers_fallback>
  <digest>SHA256</digest><engine>none</engine><tunnel_network>10.8.0.0/24</tunnel_network><tunnel_networkv6></tunnel_networkv6>
  <remote_network></remote_network><local_network>192.168.20.0/24,192.168.30.0/24</local_network><maxclients>5</maxclients>
  <allow_compression>no</allow_compression><compression></compression><dynamic_ip>yes</dynamic_ip><topology>subnet</topology>
  <serverbridge_dhcp></serverbridge_dhcp><dns_domain>lab.local</dns_domain><dns_server1>192.168.20.1</dns_server1>
  <inactive_seconds>300</inactive_seconds><keepalive_interval>10</keepalive_interval><keepalive_timeout>60</keepalive_timeout>
  <verbosity_level>3</verbosity_level><create_gw>v4only</create_gw><ping_method>keepalive</ping_method>
</openvpn-server></openvpn>
<widgets><sequence>system_information:col1:show,interfaces:col2:show,gateways:col2:show,openvpn:col2:show</sequence></widgets>
</pfsense>
"""
(GEN / "pfsense" / "config.xml").write_text(config, encoding="utf-8", newline="\n")


# ---------------------------------------------------------------- FAT16 disk (pfSense External Config Loader)
def fat16_image(path, files_in_config_dir, size_mb=16):
    SS, total = 512, size_mb * 2048
    p_start = 2048; p_size = total - p_start
    spc, rsv, nfats, root_ents = 2, 1, 2, 512
    root_secs = root_ents * 32 // SS
    fatsz = 1
    while True:
        clusters = (p_size - rsv - nfats * fatsz - root_secs) // spc
        need = ((clusters + 2) * 2 + SS - 1) // SS
        if need <= fatsz: break
        fatsz = need
    img = bytearray(total * SS)
    # MBR
    def chs(_): return b"\xfe\xff\xff"
    entry = b"\x00" + chs(0) + b"\x06" + chs(0) + struct.pack("<II", p_start, p_size)
    img[446:462] = entry; img[510:512] = b"\x55\xaa"
    base = p_start * SS
    bs = bytearray(SS)
    bs[0:3] = b"\xeb\x3c\x90"; bs[3:11] = b"MSWIN4.1"
    struct.pack_into("<HBHBHHBHHHII", bs, 11, SS, spc, rsv, nfats, root_ents, 0, 0xF8, fatsz, 63, 255, p_start, p_size)
    struct.pack_into("<BBBI11s8s", bs, 36, 0x80, 0, 0x29, 0x20261119, b"PFSENSECFG ", b"FAT16   ")
    bs[510:512] = b"\x55\xaa"
    img[base:base + SS] = bs
    fat = bytearray(fatsz * SS); struct.pack_into("<HH", fat, 0, 0xFFF8, 0xFFFF)
    data0 = base + (rsv + nfats * fatsz + root_secs) * SS
    csize = spc * SS
    nxt = [2]
    def alloc(data):
        n = max(1, (len(data) + csize - 1) // csize); first = nxt[0]
        for i in range(n):
            c = first + i
            struct.pack_into("<H", fat, c * 2, 0xFFFF if i == n - 1 else c + 1)
            off = data0 + (c - 2) * csize
            chunk = data[i * csize:(i + 1) * csize]
            img[off:off + len(chunk)] = chunk
        nxt[0] += n
        return first
    def dent(name83, attr, clus, size, nt=0):
        e = bytearray(32); e[0:11] = name83; e[11] = attr; e[12] = nt
        # fields: crt time10ms/time/date, acc date, hi clus, wrt time, wrt date, lo clus, size
        e[13] = 0; struct.pack_into("<H", e, 14, 0); struct.pack_into("<H", e, 16, 0x5B73)
        struct.pack_into("<H", e, 18, 0x5B73); struct.pack_into("<H", e, 20, 0)
        struct.pack_into("<H", e, 22, 0); struct.pack_into("<H", e, 24, 0x5B73)
        struct.pack_into("<H", e, 26, clus); struct.pack_into("<I", e, 28, size)
        return bytes(e)
    dir_clus = nxt[0]; nxt[0] += 1
    struct.pack_into("<H", fat, dir_clus * 2, 0xFFFF)
    entries = dent(b".          ", 0x10, dir_clus, 0) + dent(b"..         ", 0x10, 0, 0)
    for n83, data in files_in_config_dir:
        c = alloc(data); entries += dent(n83, 0x20, c, len(data), nt=0x18)
    off = data0 + (dir_clus - 2) * csize; img[off:off + len(entries)] = entries
    root_off = base + (rsv + nfats * fatsz) * SS
    vol = bytearray(32); vol[0:11] = b"PFSENSECFG "; vol[11] = 0x08
    img[root_off:root_off + 32] = vol
    img[root_off + 32:root_off + 64] = dent(b"CONFIG     ", 0x10, dir_clus, 0, nt=0x08)
    for i in range(nfats):
        o = base + (rsv + i * fatsz) * SS; img[o:o + len(fat)] = fat
    Path(path).write_bytes(img)
    return total

ecl_dir = ROOT / "VMs" / "fw01-pfsense"
flat = ecl_dir / "ecl-config-flat.vmdk"
sectors = fat16_image(flat, [(b"CONFIG  XML", config.encode())])
(ecl_dir / "ecl-config.vmdk").write_text(textwrap.dedent(f"""\
    # Disk DescriptorFile
    version=1
    CID=fffffffe
    parentCID=ffffffff
    createType="monolithicFlat"
    RW {sectors} FLAT "ecl-config-flat.vmdk" 0
    ddb.adapterType = "lsilogic"
    ddb.geometry.cylinders = "{sectors // (255 * 63) or 1}"
    ddb.geometry.heads = "255"
    ddb.geometry.sectors = "63"
    ddb.virtualHWVersion = "21"
    """))

# ---------------------------------------------------------------- OpenVPN client profile
ovpn = f"""client
dev tun
proto udp4
remote 192.168.101.10 1194
resolv-retry infinite
nobind
persist-key
persist-tun
remote-cert-tls server
verify-x509-name fw01.lab.local name
data-ciphers AES-256-GCM:AES-128-GCM:CHACHA20-POLY1305
auth SHA256
verb 3
<ca>
{rd('ca.crt').strip()}
</ca>
<cert>
{rd('vpnuser1.crt').strip()}
</cert>
<key>
{rd('vpnuser1.key').strip()}
</key>
<tls-crypt>
{rd('tls-crypt.key').strip()}
</tls-crypt>
"""
(GEN / "vpnuser1.ovpn").write_text(ovpn)

# ---------------------------------------------------------------- Ubuntu autoinstall (NoCloud CIDATA)
ub_hash = wsl_hash(cred["ubuntu_sysadmin"], "METHOD_SHA512")
user_data = f"""#cloud-config
autoinstall:
  version: 1
  interactive-sections: []
  locale: fr_FR.UTF-8
  keyboard: {{layout: fr}}
  timezone: Africa/Tunis
  identity:
    hostname: srv01
    realname: Sysadmin
    username: sysadmin
    password: '{ub_hash}'
  ssh:
    install-server: true
    allow-pw: true
    authorized-keys: ['{pubkey}']
  network:
    version: 2
    ethernets:
      lan0:
        match: {{macaddress: '00:50:56:2a:20:10'}}
        set-name: lan0
        addresses: [192.168.20.10/24]
        routes: [{{to: default, via: 192.168.20.1}}]
        nameservers: {{addresses: [192.168.20.1], search: [lab.local]}}
  apt:
    geoip: false
    preserve_sources_list: false
    primary:
      - arches: [default]
        uri: http://old-releases.ubuntu.com/ubuntu
    security:
      - arches: [default]
        uri: http://old-releases.ubuntu.com/ubuntu
    fallback: offline-install
  storage:
    layout: {{name: lvm}}
  packages: [openssh-server, curl, ca-certificates]
  late-commands:
    - curtin in-target -- systemctl enable ssh
    - curtin in-target -- systemctl set-default multi-user.target
"""
(SEED / "ubuntu-cidata" / "user-data").write_text(user_data, newline="\n")
(SEED / "ubuntu-cidata" / "meta-data").write_text("instance-id: srv01\nlocal-hostname: srv01\n", newline="\n")
# subiquity also accepts autoinstall.yaml (with top-level 'autoinstall:' key) at the root of an attached volume
(SEED / "ubuntu-cidata" / "autoinstall.yaml").write_text(user_data.replace("#cloud-config\n", ""), newline="\n")

# ---------------------------------------------------------------- Windows 7 autounattend.xml
W = 'xmlns:wcm="http://schemas.microsoft.com/WMIConfig/2002/State" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"'
A = 'processorArchitecture="amd64" publicKeyToken="31bf3856ad364e35" language="neutral" versionScope="nonSxS"'
first_logon = [
    'auditpol /set /category:* /success:enable /failure:enable',
    'netsh advfirewall set allprofiles state on',
    'netsh advfirewall set allprofiles firewallpolicy blockinbound,allowoutbound',
    'netsh advfirewall set allprofiles logging droppedconnections enable',
    'netsh advfirewall firewall add rule name="ICMP from gateway" dir=in action=allow protocol=icmpv4 remoteip=192.168.10.1',
    'net accounts /minpwlen:12 /maxpwage:90 /lockoutthreshold:5 /lockoutduration:15 /lockoutwindow:15',
    'net user Guest /active:no',
    'wevtutil sl Security /ms:209715200',
    'reg add "HKLM\\SYSTEM\\CurrentControlSet\\Control\\Lsa" /v LmCompatibilityLevel /t REG_DWORD /d 5 /f',
    'reg add "HKLM\\SYSTEM\\CurrentControlSet\\Services\\LanmanServer\\Parameters" /v SMB1 /t REG_DWORD /d 0 /f',
    'reg add "HKLM\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Policies\\Explorer" /v NoDriveTypeAutoRun /t REG_DWORD /d 255 /f',
]
fl = "\n".join(f'<SynchronousCommand wcm:action="add"><Order>{i+1}</Order><CommandLine>cmd /c {c.replace("&","&amp;").replace(chr(34),"&quot;")}</CommandLine></SynchronousCommand>'
               for i, c in enumerate(first_logon))
unattend = f"""<?xml version="1.0" encoding="utf-8"?>
<unattend xmlns="urn:schemas-microsoft-com:unattend">
 <settings pass="windowsPE">
  <component name="Microsoft-Windows-International-Core-WinPE" {A} {W}>
   <SetupUILanguage><UILanguage>fr-FR</UILanguage></SetupUILanguage>
   <InputLocale>040c:0000040c</InputLocale><SystemLocale>fr-FR</SystemLocale><UILanguage>fr-FR</UILanguage><UserLocale>fr-FR</UserLocale>
  </component>
  <component name="Microsoft-Windows-Setup" {A} {W}>
   <DiskConfiguration><WillShowUI>OnError</WillShowUI><Disk wcm:action="add"><DiskID>0</DiskID><WillWipeDisk>true</WillWipeDisk>
    <CreatePartitions><CreatePartition wcm:action="add"><Order>1</Order><Type>Primary</Type><Extend>true</Extend></CreatePartition></CreatePartitions>
    <ModifyPartitions><ModifyPartition wcm:action="add"><Order>1</Order><PartitionID>1</PartitionID><Active>true</Active><Format>NTFS</Format><Label>System</Label><Letter>C</Letter></ModifyPartition></ModifyPartitions>
   </Disk></DiskConfiguration>
   <ImageInstall><OSImage><InstallTo><DiskID>0</DiskID><PartitionID>1</PartitionID></InstallTo><WillShowUI>OnError</WillShowUI></OSImage></ImageInstall>
   <UserData><AcceptEula>true</AcceptEula><FullName>Lab</FullName><Organization>Projet Cloud</Organization></UserData>
  </component>
 </settings>
 <settings pass="specialize">
  <component name="Microsoft-Windows-Shell-Setup" {A} {W}>
   <ComputerName>CLI01</ComputerName><TimeZone>W. Central Africa Standard Time</TimeZone>
  </component>
  <component name="Microsoft-Windows-TerminalServices-LocalSessionManager" {A} {W}><fDenyTSConnections>true</fDenyTSConnections></component>
 </settings>
 <settings pass="oobeSystem">
  <component name="Microsoft-Windows-International-Core" {A} {W}>
   <InputLocale>040c:0000040c</InputLocale><SystemLocale>fr-FR</SystemLocale><UILanguage>fr-FR</UILanguage><UserLocale>fr-FR</UserLocale>
  </component>
  <component name="Microsoft-Windows-Shell-Setup" {A} {W}>
   <OOBE><HideEULAPage>true</HideEULAPage><NetworkLocation>Work</NetworkLocation><ProtectYourPC>1</ProtectYourPC><SkipMachineOOBE>true</SkipMachineOOBE><SkipUserOOBE>true</SkipUserOOBE></OOBE>
   <UserAccounts>
    <AdministratorPassword><Value>{cred['win7_labadmin']}</Value><PlainText>true</PlainText></AdministratorPassword>
    <LocalAccounts>
     <LocalAccount wcm:action="add"><Name>labadmin</Name><Group>Administrators</Group><Password><Value>{cred['win7_labadmin']}</Value><PlainText>true</PlainText></Password></LocalAccount>
     <LocalAccount wcm:action="add"><Name>user1</Name><Group>Users</Group><Password><Value>{cred['win7_user1']}</Value><PlainText>true</PlainText></Password></LocalAccount>
    </LocalAccounts>
   </UserAccounts>
   <AutoLogon><Enabled>true</Enabled><LogonCount>1</LogonCount><Username>labadmin</Username><Password><Value>{cred['win7_labadmin']}</Value><PlainText>true</PlainText></Password></AutoLogon>
   <FirstLogonCommands>
{fl}
   </FirstLogonCommands>
  </component>
 </settings>
</unattend>
"""
(SEED / "win7-unattend" / "autounattend.xml").write_text(unattend, encoding="utf-8")
print("OK: config.xml, ECL disk, vpnuser1.ovpn, ubuntu cidata, win7 autounattend generated")
