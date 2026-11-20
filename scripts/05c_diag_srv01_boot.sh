#!/bin/bash
# Read-only diagnosis of srv01 EFI boot chain
set -u
command -v qemu-nbd >/dev/null || { apt-get update -q >/dev/null && apt-get install -y -q qemu-utils binutils >/dev/null; }
qemu-nbd -r -c /dev/nbd0 -f vmdk /vm/srv01-ubuntu-disk0.vmdk; sleep 2; blockdev --rereadpt /dev/nbd0; sleep 1
MM=$(cat /sys/block/nbd0/dev); MAJ=${MM%%:*}; MIN=${MM##*:}
for n in 1 2; do [ -b /dev/nbd0p$n ] || mknod /dev/nbd0p$n b $MAJ $((MIN + n)); done
mkdir -p /e /r; mount -o ro /dev/nbd0p1 /e; mount -o ro,noload /dev/nbd0p2 /r
echo "--- ESP"; find /e -type f -exec ls -la {} \;
echo "--- prefixes embedded in EFI binaries"; for f in /e/EFI/BOOT/grubx64.efi /e/EFI/BOOT/BOOTX64.EFI; do echo "$f:"; strings -n 6 $f | grep -E "^/EFI/|prefix|\.disk/info" | head -5; done
echo "--- /boot"; ls -la /r/boot /r/boot/grub | head -30
echo "--- grub.cfg menuentry"; grep -m3 -E "menuentry|linux\s" /r/boot/grub/grub.cfg
echo "--- ext4 features"; dumpe2fs -h /dev/nbd0p2 2>/dev/null | grep -i features
echo "--- dpkg grub"; chroot /r dpkg -l | grep -E "grub|shim" | awk '{print $2,$3}'
umount /e /r; qemu-nbd -d /dev/nbd0
