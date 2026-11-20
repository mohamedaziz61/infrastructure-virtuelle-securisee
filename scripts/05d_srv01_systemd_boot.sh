#!/bin/bash
# srv01 still stopped at "grub>" (shim + signed GRUB on a debootstrapped system, error not visible).
# Switch to systemd-boot: firmware -> \EFI\BOOT\BOOTX64.EFI (systemd-boot) -> kernel+initrd on the ESP.
# Also points APT to mirrors.edge.kernel.org (official Ubuntu mirror) because Canonical's servers time out
# from this network. Run in labtools:1 privileged container, /vm = VMs/srv01-ubuntu.
set -euxo pipefail
DEV=/dev/nbd0
qemu-nbd --disconnect $DEV || true
qemu-nbd --connect=$DEV --format=vmdk /vm/srv01-ubuntu-disk0.vmdk; sleep 2
blockdev --rereadpt $DEV || true; sleep 1
MM=$(cat /sys/block/nbd0/dev); MAJ=${MM%%:*}; MIN=${MM##*:}
for n in 1 2; do [ -b ${DEV}p$n ] || mknod ${DEV}p$n b $MAJ $((MIN + n)); done
T=/target; mkdir -p $T; mount ${DEV}p2 $T; mount ${DEV}p1 $T/boot/efi
for d in dev dev/pts proc sys; do mount --bind /$d $T/$d; done
cp /etc/resolv.conf $T/etc/resolv.conf.lab; mv $T/etc/resolv.conf $T/etc/resolv.conf.orig || true; cp /etc/resolv.conf $T/etc/resolv.conf
MIR=http://mirrors.edge.kernel.org/ubuntu
sed -i "s#http://archive.ubuntu.com/ubuntu#$MIR#; s#http://security.ubuntu.com/ubuntu#$MIR#" $T/etc/apt/sources.list.d/ubuntu.sources
printf 'Acquire::Retries "6";\nAcquire::http::Timeout "20";\nAcquire::ForceIPv4 "true";\n' > $T/etc/apt/apt.conf.d/80lab
ROOTUUID=$(blkid -s UUID -o value ${DEV}p2)
chroot $T /bin/bash -euxc "
  apt-get update -q
  DEBIAN_FRONTEND=noninteractive apt-get install -y -q --no-install-recommends systemd-boot-efi
  ls /usr/lib/systemd/boot/efi/
"
E=$T/boot/efi
mkdir -p /backup_esp && cp -a $E/EFI /backup_esp/ 2>/dev/null || true
install -D -m 0644 $T/usr/lib/systemd/boot/efi/systemd-bootx64.efi $E/EFI/BOOT/BOOTX64.EFI
install -D -m 0644 $T/usr/lib/systemd/boot/efi/systemd-bootx64.efi $E/EFI/systemd/systemd-bootx64.efi
KVER=$(ls $T/boot | sed -n 's/^vmlinuz-//p' | sort -V | tail -1)
mkdir -p $E/ubuntu $E/loader/entries
cp $T/boot/vmlinuz-$KVER $E/ubuntu/vmlinuz
cp $T/boot/initrd.img-$KVER $E/ubuntu/initrd.img
cat > $E/loader/loader.conf <<EOF
default ubuntu.conf
timeout 2
editor no
EOF
cat > $E/loader/entries/ubuntu.conf <<EOF
title   Ubuntu 25.04 srv01 ($KVER)
linux   /ubuntu/vmlinuz
initrd  /ubuntu/initrd.img
options root=UUID=$ROOTUUID ro console=tty0
EOF
# keep the ESP copy in sync on future kernel updates
cat > $T/etc/kernel/postinst.d/zz-lab-esp-sync <<'EOF'
#!/bin/sh
K=$(ls /boot | sed -n 's/^vmlinuz-//p' | sort -V | tail -1)
cp /boot/vmlinuz-$K /boot/efi/ubuntu/vmlinuz && cp /boot/initrd.img-$K /boot/efi/ubuntu/initrd.img
EOF
chmod 755 $T/etc/kernel/postinst.d/zz-lab-esp-sync
mkdir -p $T/etc/initramfs/post-update.d && cp $T/etc/kernel/postinst.d/zz-lab-esp-sync $T/etc/initramfs/post-update.d/
mv $T/etc/resolv.conf.orig $T/etc/resolv.conf 2>/dev/null || ln -sf /run/systemd/resolve/stub-resolv.conf $T/etc/resolv.conf
rm -f $T/etc/resolv.conf.lab
find $E -type f | sort; cat $E/loader/entries/ubuntu.conf
for d in sys proc dev/pts dev; do umount $T/$d; done
umount $T/boot/efi; umount $T; sync; qemu-nbd --disconnect $DEV
echo SDBOOT_OK
