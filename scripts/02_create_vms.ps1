# Creates the 4 project VMs (thin-provisioned disks) in "projet cloud\VMs". Never overwrites an existing VM.
$ErrorActionPreference = 'Stop'
$root  = "C:\Users\azizb\Desktop\projet cloud"
$vmdir = "$root\VMs"
$vdm   = "C:\Program Files (x86)\VMware\VMware Workstation\vmware-vdiskmanager.exe"
$seed  = "$root\ISO\seed"
# LAN segment IDs (VLAN 10/20/30). Same ID in every VMX = same isolated L2 segment.
$PVN = @{
  VLAN10 = "52 70 6a 63 6c 69 00 10-ce 01 aa 10 00 00 00 10"
  VLAN20 = "52 70 6a 63 73 72 00 20-ce 01 aa 20 00 00 00 20"
  VLAN30 = "52 70 6a 63 73 74 00 30-ce 01 aa 30 00 00 00 30"
}
$slots = 33,160,192,224,256

function New-Nic($i, $net, $mac, $dev) {
  $l = @("ethernet$i.present = `"TRUE`"", "ethernet$i.virtualDev = `"$dev`"", "ethernet$i.addressType = `"static`"",
         "ethernet$i.address = `"$mac`"", "ethernet$i.pciSlotNumber = `"$($slots[$i])`"")
  switch -regex ($net) {
    '^nat$'    { $l += "ethernet$i.connectionType = `"nat`"" }
    '^vmnet\d+'{ $l += "ethernet$i.connectionType = `"custom`"", "ethernet$i.vnet = `"$($net.ToUpper() -replace 'VMNET','VMnet')`"" }
    '^VLAN'    { $l += "ethernet$i.connectionType = `"pvn`"", "ethernet$i.pvnID = `"$($PVN[$net])`"" }
  }
  $l
}

function New-VM($name, $guest, $mem, $cpu, $fw, $disks, $nics, $cds, [string[]]$extra) {
  $d = "$vmdir\$name"
  if (Test-Path "$d\$name.vmx") { Write-Host "SKIP $name (exists)"; return }
  New-Item -ItemType Directory -Force $d | Out-Null
  $v = @('.encoding = "UTF-8"','config.version = "8"','virtualHW.version = "21"',
    "displayName = `"$name`"","guestOS = `"$guest`"","memsize = `"$mem`"","numvcpus = `"$cpu`"","cpuid.coresPerSocket = `"$cpu`"",
    "firmware = `"$fw`"",'pciBridge0.present = "TRUE"','pciBridge4.present = "TRUE"','pciBridge4.virtualDev = "pcieRootPort"','pciBridge4.functions = "8"',
    'pciBridge5.present = "TRUE"','pciBridge5.virtualDev = "pcieRootPort"','pciBridge5.functions = "8"',
    'pciBridge6.present = "TRUE"','pciBridge6.virtualDev = "pcieRootPort"','pciBridge6.functions = "8"',
    'pciBridge7.present = "TRUE"','pciBridge7.virtualDev = "pcieRootPort"','pciBridge7.functions = "8"',
    'vmci0.present = "TRUE"','hpet0.present = "TRUE"','usb.present = "FALSE"','sound.present = "FALSE"','floppy0.present = "FALSE"',
    # Hardening for the VM-escape workshop: no shared folders / clipboard / drag-and-drop
    'isolation.tools.hgfs.disable = "TRUE"','isolation.tools.copy.disable = "TRUE"','isolation.tools.paste.disable = "TRUE"',
    'isolation.tools.dnd.disable = "TRUE"','sharedFolder.maxNum = "0"','isolation.tools.setGUIOptions.enable = "FALSE"',
    'tools.syncTime = "TRUE"','sata0.present = "TRUE"')
  $i = 0
  foreach ($dk in $disks) {
    $f = "$name-disk$i.vmdk"
    & $vdm -c -s "$($dk)GB" -a lsilogic -t 0 "$d\$f" | Out-Null   # -t 0 = growable single file (thin)
    $v += "sata0:$i.present = `"TRUE`"", "sata0:$i.fileName = `"$f`""
    $i++
  }
  $c = 0
  foreach ($cd in $cds) {
    $u = $c + 4   # CD-ROMs on sata0:4+
    $v += "sata0:$u.present = `"TRUE`"", "sata0:$u.deviceType = `"cdrom-image`"", "sata0:$u.fileName = `"$cd`"", "sata0:$u.startConnected = `"TRUE`""
    $c++
  }
  $n = 0; foreach ($nic in $nics) { $v += New-Nic $n $nic[0] $nic[1] $nic[2]; $n++ }
  if ($extra) { $v += $extra }
  Set-Content -Path "$d\$name.vmx" -Value $v -Encoding ASCII
  Write-Host "CREATED $name"
}

$iso = $root
New-VM "fw01-pfsense" "freebsd14-64" 2048 2 "bios" @(16) `
  @(@("nat","00:50:56:2A:01:00","e1000"),@("VLAN10","00:50:56:2A:01:10","e1000"),@("VLAN20","00:50:56:2A:01:20","e1000"),
    @("VLAN30","00:50:56:2A:01:30","e1000"),@("vmnet5","00:50:56:2A:01:99","e1000")) `
  @("$iso\pfSense-CE-2.7.2-RELEASE-amd64.iso")

New-VM "srv01-ubuntu" "ubuntu-64" 4096 2 "efi" @(25) `
  @(,@("VLAN20","00:50:56:2A:20:10","vmxnet3")) `
  @("$iso\ubuntu-25.04-desktop-amd64.iso","$seed\ubuntu-cidata.iso")

New-VM "cli01-win7" "windows7-64" 2048 2 "bios" @(30) `
  @(,@("VLAN10","00:50:56:2A:10:50","e1000")) `
  @("$iso\SW_DVD5_Win_Pro_7_64BIT_French_Full_MLF_X15-71101.ISO","$seed\win7-unattend.iso")

New-VM "nas01-truenas" "debian12-64" 8192 2 "efi" @(20,10,10) `
  @(,@("VLAN30","00:50:56:2A:30:10","vmxnet3")) `
  @("$iso\TrueNAS-SCALE-25.10.7.iso") @('disk.EnableUUID = "TRUE"')
