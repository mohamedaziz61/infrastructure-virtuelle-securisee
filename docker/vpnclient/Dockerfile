# OpenVPN test client (official Ubuntu openvpn package) used to validate remote access from the WAN side.
FROM ubuntu:24.04
RUN sed -i "s#http://archive.ubuntu.com/ubuntu#http://mirrors.edge.kernel.org/ubuntu#; s#http://security.ubuntu.com/ubuntu#http://mirrors.edge.kernel.org/ubuntu#" /etc/apt/sources.list.d/ubuntu.sources \
 && printf 'Acquire::Retries "6";\nAcquire::http::Timeout "20";\nAcquire::ForceIPv4 "true";\n' > /etc/apt/apt.conf.d/80lab \
 && apt-get update && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends openvpn iproute2 iputils-ping curl netcat-openbsd ca-certificates \
 && rm -rf /var/lib/apt/lists/*
