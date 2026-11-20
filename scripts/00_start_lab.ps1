# Starts the lab in dependency order. Run from a normal PowerShell; it asks UAC once for the host routes.
#   1. pfSense (gateway of every VLAN)  2. host routes via MGMT  3. srv01  4. cli01  5. (optional) nas01
# Usage:  powershell -ExecutionPolicy Bypass -File "scripts\00_start_lab.ps1" [-WithNas]
param([switch]$WithNas)
$vr   = "C:\Program Files (x86)\VMware\VMware Workstation\vmrun.exe"
$root = "C:\Users\azizb\Desktop\projet cloud"
$vm   = "$root\VMs"
$log  = "$root\logs\operations.log"
function Log($m) { "$(Get-Date -Format s) [START] $m" | Tee-Object -FilePath $log -Append }

if ((Get-NetAdapter -Name ProTUN -ErrorAction SilentlyContinue).Status -eq 'Up') {
  Log "WARNING: Proton VPN is connected - its kill switch blocks the lab networks. Disconnect it."
}
$free = [math]::Round((Get-CimInstance Win32_OperatingSystem).FreePhysicalMemory/1MB,1)
Log "Free RAM: $free GB"

& $vr -T ws start "$vm\fw01-pfsense\fw01-pfsense.vmx" gui
for ($i=0; $i -lt 45; $i++) { Start-Sleep 4; if (Test-Connection 192.168.99.1 -Count 1 -Quiet) { break } }
if (Test-Connection 192.168.99.1 -Count 1 -Quiet) { Log "pfSense up (~$($i*4)s)" } else { Log "ERROR: pfSense not reachable on 192.168.99.1"; exit 1 }

$have = route print -4 | Select-String "192.168.20.0\s+255.255.255.0\s+192.168.99.1"
if (-not $have) {
  $p = Start-Process powershell -Verb RunAs -Wait -PassThru -WindowStyle Hidden `
       -ArgumentList '-NoProfile','-ExecutionPolicy','Bypass','-File',"`"$root\scripts\04_host_routes_mgmt.ps1`""
  Log "host routes script exit=$($p.ExitCode)"
}
route print -4 | Select-String "192.168.(10|20|30).0" | ForEach-Object { Log $_.Line.Trim() }

& $vr -T ws start "$vm\srv01-ubuntu\srv01-ubuntu.vmx" gui; Log "srv01 started"
& $vr -T ws start "$vm\cli01-win7\cli01-win7.vmx" gui;   Log "cli01 started"
if ($WithNas) {
  if ($free -lt 10) { Log "WARNING: <10 GB free RAM; stop Docker Desktop before TrueNAS (8 GB)" }
  & $vr -T ws start "$vm\nas01-truenas\nas01-truenas.vmx" gui; Log "nas01 started"
}
& $vr list
