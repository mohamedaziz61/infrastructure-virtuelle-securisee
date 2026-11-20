#!/bin/bash
# Read-only copy of C:\lab\evidence from cli01 (VM powered off). labtools:1 container, /vm = VMs/cli01-win7,
# /out = documentation/tests/cli01_evidence
set -euxo pipefail
DEV=/dev/nbd1
qemu-nbd --disconnect $DEV || true
qemu-nbd -r --connect=$DEV --format=vmdk /vm/cli01-win7-disk0.vmdk; sleep 2
blockdev --rereadpt $DEV || true; sleep 1
MM=$(cat /sys/block/nbd1/dev); MAJ=${MM%%:*}; MIN=${MM##*:}
[ -b ${DEV}p1 ] || mknod ${DEV}p1 b $MAJ $((MIN + 1))
mkdir -p /w; ntfs-3g -o ro ${DEV}p1 /w
ls -la /w/lab/evidence
cp -r /w/lab/evidence/. /out/
# Sysmon service/driver presence and LabBootstrap removal
hivexget /w/Windows/System32/config/SYSTEM '\ControlSet001\Services\Sysmon64' ImagePath > /out/reg_sysmon64.txt 2>&1 || echo "Sysmon64 service key absent" > /out/reg_sysmon64.txt
hivexget /w/Windows/System32/config/SYSTEM '\ControlSet001\Services\LabBootstrap' ImagePath > /out/reg_labbootstrap.txt 2>&1 || echo "LabBootstrap removed" > /out/reg_labbootstrap.txt
umount /w; qemu-nbd --disconnect $DEV
# cmd.exe redirections are OEM code page (CP850 on fr-FR); msiexec logs are UTF-16LE with BOM
for f in /out/*.txt /out/*.log; do
  [ -s "$f" ] || continue
  case "$(head -c2 "$f" | od -An -tx1 | tr -d ' ')" in
    fffe) iconv -f UTF-16 -t UTF-8 "$f" > "$f.u8" ;;
    *)    iconv -f CP850 -t UTF-8 "$f" > "$f.u8" ;;
  esac && mv "$f.u8" "$f"
done
echo COLLECT_OK
