#!/bin/bash
# Offline injection of the cli01 (Windows 7) security tooling. VM must be powered off.
# Copies scripts/win7 + downloads/win7-tools to C:\lab and registers a one-shot LocalSystem service
# "LabBootstrap" that runs C:\lab\install.cmd at next boot (the script deletes the service itself).
# Runs in a privileged container:  /vm = VMs/cli01-win7, /p = project root (ro)
set -euxo pipefail
export DEBIAN_FRONTEND=noninteractive
command -v qemu-nbd >/dev/null || { apt-get update -q && apt-get install -y -q qemu-utils ntfs-3g libhivex-bin libwin-hivex-perl dos2unix >/dev/null; }
DEV=/dev/nbd1
qemu-nbd --disconnect $DEV || true
qemu-nbd --connect=$DEV --format=vmdk /vm/cli01-win7-disk0.vmdk
sleep 2; blockdev --rereadpt $DEV || true; sleep 1
MM=$(cat /sys/block/nbd1/dev); MAJ=${MM%%:*}; MIN=${MM##*:}
[ -b ${DEV}p1 ] || mknod ${DEV}p1 b $MAJ $((MIN + 1))
ntfsfix -d ${DEV}p1            # clear the dirty flag left by the hard power-off
mkdir -p /w; ntfs-3g ${DEV}p1 /w
ls /w/Windows/System32/config/SYSTEM
mkdir -p /w/lab/sysmon
cp /p/downloads/win7-tools/sysmon/Sysmon64.exe /p/downloads/win7-tools/sysmon/Eula.txt /w/lab/sysmon/
cp /p/downloads/win7-tools/windows_exporter-0.18.1-amd64.msi /w/lab/
cp /p/scripts/win7/sysmon-lab.xml /w/lab/
cp /p/scripts/win7/install.cmd /w/lab/install.cmd && unix2dos /w/lab/install.cmd
# --- registry: one-shot service in the active ControlSet
cp /w/Windows/System32/config/SYSTEM /backup/cli01_SYSTEM_hive_before_inject.bak
CUR=$(hivexget /w/Windows/System32/config/SYSTEM '\Select' Current)
CS=$(printf 'ControlSet%03d' "$CUR")
cat > /tmp/svc.reg <<EOF
Windows Registry Editor Version 5.00

[\\$CS\\Services\\LabBootstrap]
"Type"=dword:00000010
"Start"=dword:00000002
"ErrorControl"=dword:00000000
"ImagePath"="cmd.exe /c start \\"LabBootstrap\\" /b C:\\\\lab\\\\install.cmd"
"DisplayName"="Lab one-shot bootstrap (projet cloud)"
"ObjectName"="LocalSystem"
EOF
cat /tmp/svc.reg
hivexregedit --merge /w/Windows/System32/config/SYSTEM /tmp/svc.reg
hivexget /w/Windows/System32/config/SYSTEM "\\$CS\\Services\\LabBootstrap" ImagePath
ls -la /w/lab
sync; umount /w; qemu-nbd --disconnect $DEV
echo "INJECT_OK ($CS)"
