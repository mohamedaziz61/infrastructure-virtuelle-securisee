#!/bin/bash
# Generic offline one-shot task for cli01: copy files to C:\lab and register a LocalSystem service that runs once.
# env: SVC (service name), CMD (path in C:\lab), FILES (space-separated paths under /p). VM must be off.
set -euxo pipefail
DEV=/dev/nbd1
qemu-nbd --disconnect $DEV || true
qemu-nbd --connect=$DEV --format=vmdk /vm/cli01-win7-disk0.vmdk; sleep 2
blockdev --rereadpt $DEV || true; sleep 1
MM=$(cat /sys/block/nbd1/dev); MAJ=${MM%%:*}; MIN=${MM##*:}
[ -b ${DEV}p1 ] || mknod ${DEV}p1 b $MAJ $((MIN + 1))
ntfsfix -d ${DEV}p1
mkdir -p /w; ntfs-3g ${DEV}p1 /w
for f in $FILES; do cp "/p/$f" /w/lab/; done
H=/w/Windows/System32/config/SYSTEM
CS=$(printf 'ControlSet%03d' "$(hivexget $H '\Select' Current)")
# unquoted heredoc: "\\\\" -> "\\" in the .reg file (= one backslash for hivexregedit), same as script 06
cat > /tmp/svc.reg <<EOF
Windows Registry Editor Version 5.00

[\\$CS\\Services\\$SVC]
"Type"=dword:00000010
"Start"=dword:00000002
"ErrorControl"=dword:00000000
"ImagePath"="cmd.exe /c start \\"$SVC\\" /b C:\\\\lab\\\\$CMD"
"ObjectName"="LocalSystem"
EOF
cat /tmp/svc.reg; hivexregedit --merge $H /tmp/svc.reg
hivexget $H "\\${CS}\\Services\\${SVC}" ImagePath || true
ls -la /w/lab; sync; umount /w; qemu-nbd --disconnect $DEV; echo ONESHOT_OK
