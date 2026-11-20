# Admin workstation (host, 192.168.99.10) -> internal VLANs through pfSense MGMT (192.168.99.1).
# Non-persistent routes (removed at reboot). Run elevated. Remove: route delete 192.168.10.0 (etc.)
foreach ($n in "192.168.10.0","192.168.20.0","192.168.30.0") {
  route delete $n 2>$null | Out-Null
  route add $n mask 255.255.255.0 192.168.99.1 metric 5
}
route print -4 | Select-String "192.168.(10|20|30).0" | Out-File "C:\Users\azizb\Desktop\projet cloud\logs\host_routes.log"
