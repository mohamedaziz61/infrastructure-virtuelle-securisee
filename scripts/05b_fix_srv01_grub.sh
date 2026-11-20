#!/bin/bash
# srv01 booted to "grub>": shim's signed grubx64.efi looks for \EFI\ubuntu\grub.cfg, but grub-install
# --removable only populated \EFI\BOOT. Add the stub config (same as Ubuntu's installer writes).
set -euxo pipefail
command -v qemu-nbd >/dev/null || { apt-get update -q >/dev/null && apt-get install -y -q qemu-utils >/dev/null; }
DEV=/dev/nbd0
qemu-nbd --disconnect $DEV || true
qemu-nbd --connect=$DEV --format=vmdk /vm/srv01-ubuntu-disk0.vmdk; sleep 2
blockdev --rereadpt $DEV || true; sleep 1
MM=$(cat /sys/block/nbd0/dev); MAJ=${MM%%:*}; MIN=${MM##*:}
for n in 1 2; do [ -b ${DEV}p$n ] || mknod ${DEV}p$n b $MAJ $((MIN + n)); done
ROOTUUID=$(blkid -s UUID -o value ${DEV}p2)
mkdir -p /efi; mount ${DEV}p1 /efi
mkdir -p /efi/EFI/ubuntu
cat > /efi/EFI/ubuntu/grub.cfg <<EOF
search.fs_uuid $ROOTUUID root
set prefix=(\$root)'/boot/grub'
configfile \$prefix/grub.cfg
EOF
cp /efi/EFI/ubuntu/grub.cfg /efi/EFI/BOOT/grub.cfg
find /efi -type f | sort
cat /efi/EFI/ubuntu/grub.cfg
umount /efi; sync; qemu-nbd --disconnect $DEV
echo GRUBFIX_OK
