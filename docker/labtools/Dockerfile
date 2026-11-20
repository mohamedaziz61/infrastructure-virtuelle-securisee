# Offline disk-maintenance toolbox for the lab VMs (nbd, NTFS, registry hives, ext4, EFI)
FROM ubuntu:24.04
RUN printf 'Acquire::Retries "6";\nAcquire::http::Timeout "20";\nAcquire::ForceIPv4 "true";\n' > /etc/apt/apt.conf.d/80lab \
 && apt-get update \
 && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
    qemu-utils ntfs-3g libhivex-bin libwin-hivex-perl dos2unix fdisk gdisk dosfstools e2fsprogs binutils util-linux debootstrap ca-certificates \
 && rm -rf /var/lib/apt/lists/*
