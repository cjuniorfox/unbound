# Unbound DNS Server with Podman and Kubernetes

This repository contains the necessary files to build and run an Unbound DNS server using Podman or Kubernetes. The setup includes a Dockerfile for building the Unbound container and a `pod.yaml` file for deploying the container as a pod.

## Table of Contents

- [Overview](#overview)
- [Dockerfile](#dockerfile)
- [Podman Setup](#podman-setup)
- [Kubernetes Setup](#kubernetes-setup)
- [Volumes](#volumes)
- [Healthcheck](#healthcheck)
- [Changelog](#changelog)

## Overview

This project sets up an Unbound DNS server using a containerized environment. The container is built using Alpine Linux and includes Unbound, OpenSSL, Python3, and other necessary tools. The pod configuration is designed to run on both Podman and Kubernetes.

## Dockerfile

The `Dockerfile` is used to build the Unbound DNS server container. It installs the necessary dependencies, sets up configuration files, and defines health checks.

### Key Features

- **Base Image**: Alpine Linux 3.18
- **Installed Packages**: Unbound, OpenSSL, Python3, Bind-tools, Supervisor
- **Volumes**:
  - `/unbound-conf`: Custom Unbound configuration files
  - `/etc/unbound/unbound.conf.d/`: Additional Unbound configuration
  - `/dhcp.leases`: DHCP leases file
  - `/etc/certificates`: TLS certificates files for TLS enable DNS server
- **Healthcheck**: Ensures that Unbound is running correctly by querying `google.com`.

### Build the Docker Image

To build the Docker image, run the following command:

```sh
docker build -t unbound-dns . 
```

## Podman Setup

You can use Podman to run the Unbound DNS server as a pod. The `pod.yaml` file defines the pod and container configuration.

### Steps to Run with Podman

#### 1. **Create the Pod and Network**

```sh
podman network create unbound-net \
  --driver bridge \
  --gateway 10.89.10.97 \
  --subnet 10.89.10.96/28 \
  --ip-range 10.89.10.98/28 
  
podman pod create \
    -p <IP_LAN>:53:53/udp \
    -p <IP_GUEST>:53:53/udp \
    -p 853:853/tcp \
    --network unbound-net \
    --ip 10.89.10.100 unbound-pod 
```

#### 2. **Run the Container**

```sh
podman run -d \
    --pod unbound-pod \
    --name unbound-server \
    --restart always \
    --env DOMAIN=juniorfox.net \
    --env DHCPSERVER=dhcpd \
    --volume /var/lib/dhcp/dhcpd.leases:/dhcp.leases \
    --volume $(pwd)/unbound-conf:/unbound-conf \
    --volume certificates:/etc/certificates/ \
    --volume unbound-conf:/etc/unbound/unbound.conf.d/ \
    cjuniorfox/unbound:1.20.0 
```

- **DOMAIN** is the domain defined as the `search domains`.
- **DHCPSERVER** is the name of the DHCP server. It is used to retrieve DHCP leases. Can be 
  - `dhcpd`
  - `kea`
  - `dnsmasq`.

#### 3. **Firewall Configuration** (Optional)

If you want to forward DNS requests to the pod, you can configure firewall:

```sh
firewall-cmd --add-forward-port=port=53:proto=udp:toport=53:toaddr=10.89.10.100 --zone=internal 
firewall-cmd --runtime-to-permanent 
```

## Kubernetes Setup

The `pod.yaml` file can also be used to deploy the Unbound DNS server in a Kubernetes environment.

### Steps to Deploy with Kubernetes

#### 1. **Apply the Pod and Network Configuration**

```sh
kubectl apply -f pod.yaml 
```

#### 2. **Verify the Pod**

Check the status of the pod to ensure it is running:

```sh
kubectl get pods 
```

#### 3. **Access the DNS Server**

The DNS server will be accessible on the specified host IPs and ports defined in the `pod.yaml` file.

## Volumes

The following volumes are used in the container:

- **`/unbound-conf`**: Custom Unbound configuration files.
- **`/etc/unbound/unbound.conf.d/`**: Additional Unbound configuration files.
- **`/dhcp.leases`**: DHCP Leases file.
- **Persistent Volume Claims (PVC)**:
  - `certificates-pvc`: Mounted at `/etc/certificates/`.
  - `unbound-conf-pvc`: Mounted at `/etc/unbound/unbound.conf.d/`.

Ensure that the paths for the volumes are correctly set up in your environment.

## Healthcheck

The container includes a health check to ensure that the Unbound server is up and running.

## Changelog

### 2023-10-15

- Added **DNSMasq** Watcher
- Renamed volume **/dhcpd** to **/dhcpd.leases** to reflect the leasesfile instead of directory containing the leases file.
