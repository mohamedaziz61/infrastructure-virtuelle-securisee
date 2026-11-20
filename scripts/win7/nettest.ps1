# VLAN10 segmentation tests run ON cli01 (PowerShell 2.0 compatible). Output: C:\lab\evidence\segmentation_vlan10.txt
$out = "C:\lab\evidence\segmentation_vlan10.txt"
function T($h, $p, $what, $exp) {
  $c = New-Object System.Net.Sockets.TcpClient
  $ar = $c.BeginConnect($h, $p, $null, $null)
  $ok = $ar.AsyncWaitHandle.WaitOne(3000, $false) -and $c.Connected
  $c.Close()
  $r = if ($ok) { "OPEN" } else { "BLOCKED" }
  $s = if ($r -eq $exp) { "PASS" } else { "FAIL" }
  "{0,-22} {1,-38} {2,-8} expected {3,-8} {4}" -f "${h}:$p", $what, $r, $exp, $s
}
$lines = @()
$lines += "=== Segmentation tests from cli01 (VLAN10) $(Get-Date -Format s)"
$lines += (ipconfig | Select-String "IPv4|Passerelle|Gateway" | ForEach-Object { $_.Line.Trim() })
$lines += T "192.168.20.10" 8080 "Client -> application (allowed)" "OPEN"
$lines += T "192.168.20.10" 3000 "Client -> Grafana (MGMT/VPN only)" "BLOCKED"
$lines += T "192.168.20.10" 22   "Client -> srv01 SSH" "BLOCKED"
$lines += T "192.168.20.10" 9100 "Client -> node_exporter" "BLOCKED"
$lines += T "192.168.10.1"  443  "Client -> pfSense webGUI (own gw)" "BLOCKED"
$lines += T "192.168.10.1"  22   "Client -> pfSense SSH" "BLOCKED"
$lines += T "192.168.99.1"  443  "Client -> MGMT network" "BLOCKED"
$lines += T "192.168.30.10" 443  "Client -> TrueNAS webUI" "BLOCKED"
$lines += T "1.1.1.1"       443  "Internet HTTPS" "OPEN"
$lines += T "1.1.1.1"       53   "Direct external DNS (bypass)" "BLOCKED"
$lines += T "192.168.101.2" 80   "WAN-side network" "BLOCKED"
try { $h = (New-Object Net.WebClient).DownloadString("http://192.168.20.10:8080/health"); $lines += "HTTP GET app /health: $h  PASS" } catch { $lines += "HTTP GET app /health: FAIL $($_.Exception.Message)" }
try { $a = [Net.Dns]::GetHostAddresses("srv01.lab.local") | Select-Object -First 1; $lines += "DNS srv01.lab.local -> $a (pfSense resolver)  $(if ("$a" -eq '192.168.20.10') {'PASS'} else {'FAIL'})" } catch { $lines += "DNS srv01.lab.local FAIL" }
try { $e = [Net.Dns]::GetHostAddresses("www.debian.org") | Select-Object -First 1; $lines += "DNS www.debian.org -> $e  PASS" } catch { $lines += "DNS www.debian.org FAIL" }
$lines += "NOTE: 192.168.30.10:445 (SMB, allowed by pfSense) is tested after TrueNAS installation."
$lines | Out-File -FilePath $out -Encoding ASCII
