# Creates VMnet5 (host-only, VLAN 99 Management 192.168.99.0/24) WITHOUT VMware DHCP/NAT.
# Host adapter gets 192.168.99.10 (pfSense owns .1). Must run elevated. Idempotent.
$ErrorActionPreference = 'Continue'
$log = "C:\Users\azizb\Desktop\projet cloud\logs\vmnet5_setup.log"
Start-Transcript -Path $log -Append | Out-Null
$vnet = "C:\Program Files (x86)\VMware\VMware Workstation\vnetlib64.exe"
& $vnet -- add adapter vmnet5
& $vnet -- set vnet vmnet5 addr 192.168.99.0
& $vnet -- set vnet vmnet5 mask 255.255.255.0
& $vnet -- update adapter vmnet5
& $vnet -- remove dhcp vmnet5 2>$null
& $vnet -- remove nat vmnet5 2>$null
Start-Sleep 5
$name = "VMware Network Adapter VMnet5"
netsh interface ipv4 set address name="$name" static 192.168.99.10 255.255.255.0
Get-NetIPAddress -InterfaceAlias $name -AddressFamily IPv4 | Format-Table InterfaceAlias,IPAddress,PrefixLength
Stop-Transcript | Out-Null
