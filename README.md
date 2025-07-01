# Unbound DNS Server with Podman and Kubernetes

This repository contains the necessary files to build and run an Unbound DNS server using Podman or Kubernetes. The setup includes a Dockerfile for building the Unbound container and a `pod.yaml` file for deploying the container as a pod.

## Table of Contents

- [Overview](#overview)
- [Dockerfile](#dockerfile)
- [Podman Setup](#podman-setup)
  - [Steps to Run with Podman](#steps-to-run-with-podman)
    - [Create the Pod and Network](#1-create-the-pod-and-network)
    - [Run the Container](#2-run-the-container)
    - [Notes about DHCPSERVER](#notes-about-dhcpserver)
    - [IPv6 Name Resolution](#ipv6-name-resolution)
    - [Firewall Configuration (Optional)](#3-firewall-configuration-optional)
- [Kubernetes Setup](#kubernetes-setup)
  - [Steps to Deploy with Kubernetes](#steps-to-deploy-with-kubernetes)
    - [Apply the Pod and Network Configuration](#1-apply-the-pod-and-network-configuration)
    - [Verify the Pod](#2-verify-the-pod)
    - [Access the DNS Server](#3-access-the-dns-server)
- [Using the Docker Images](#using-the-docker-images)
  - [Note about the image](#note-about-the-image)
  - [Pulling from GHCR](#pulling-from-ghcr)
  - [Authentication for GHCR](#authentication-for-ghcr)
  - [Pulling the Images](#pulling-the-images)
  - [Running the Images](#running-the-images)
  - [Notes](#notes)
- [Volumes](#volumes)
- [Healthcheck](#healthcheck)
- [Troubleshooting](#troubleshooting)
  - [Docker Daemon Not Running](#docker-daemon-not-running)
- [Testing](#testing)
  - [Running the Tests](#running-the-tests)
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
  - `/dhcp.leases`: DHCP leases file or directory
  - `/etc/certificates`: TLS certificates files for TLS-enabled DNS server
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
    --env SLAAC_RESOLVER=slaac-resolver \
    --volume /var/lib/dhcp/dhcpd.leases:/dhcp.leases \
    --volume $(pwd)/unbound-conf:/unbound-conf \
    --volume /run/slaac-resolver:/slaac-resolver
    --volume certificates:/etc/certificates/ \
    cjuniorfox/unbound:1.20.0 
```

- **DOMAIN** is the domain defined as the `search domains`.
- **DHCPSERVER** is the name of the DHCP server. It is used to retrieve DHCP leases. Can be:

  - `dhcpd`
  - `kea`
  - `dnsmasq`
  - `systemd-networkd`

### Notes about DHCPSERVER

- If the `DHCPSERVER` variable is not set, the container will print the following message and remain idle:

  ```txt
  No DHCP server defined. Keeping the process running but doing nothing...
  ```

- Ensure that the `/dhcp.leases` file or directory is correctly mounted and accessible by the container.

### IPv6 Name Resolution

IPv6 name resolution can be achieved using a **SLAAC watcher**.

- **SLAAC_RESOLVER** refers to the IPv6 SLAAC watcher used for name resolution. Currently, the only supported option is [slaac-resolver](https://github.com/cjuniorfox/slaac-resolver).

---

#### 3. **Firewall Configuration** (Optional)

If you want to forward DNS requests to the pod, you can configure the firewall:

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

## Using the Docker Images

The Docker images for this project are published to Docker Hub. You can pull and run the images for both the `main` and `develop` branches.

### Note about the image

All references point to the Docker image, but you can also pull it from GitHub Container Registry (GHCR) using the image `ghcr.io/cjuniorfox/unbound:<version>`, where `<version>` can be:

- `developer`
- `latest`
- A specific version number (e.g., `1.20.0`)

#### Pulling from GHCR

To pull an image from GitHub Container Registry:

```sh
docker pull ghcr.io/cjuniorfox/unbound:latest
```

#### Authentication for GHCR

If you encounter permission issues when pulling from GHCR, ensure you are logged in:

```sh
echo $GITHUB_TOKEN | docker login ghcr.io -u <username> --password-stdin
```

### Pulling the Images

1. **Stable Release (Main Branch)**:
   - The `main` branch publishes the `latest` tag and versioned tags (e.g., `1.20.0`).
   - To pull the stable release:

     ```sh
     docker pull docker.io/cjuniorfox/unbound:latest
     ```

   - To pull a specific version:

     ```sh
     docker pull docker.io/cjuniorfox/unbound:1.20.0
     ```

2. **Development Version (Develop Branch)**:
   - The `develop` branch publishes the `developer` tag and versioned `-develop` tags (e.g., `1.20.0-develop`).
   - To pull the development version:

     ```sh
     docker pull docker.io/cjuniorfox/unbound:developer
     ```

   - To pull a specific development version:

     ```sh
     docker pull docker.io/cjuniorfox/unbound:1.20.0-develop
     ```

### Running the Images

1. **Run the Stable Release**:

   ```sh
   docker run -d \
       --name unbound-server \
       --restart always \
       --env DOMAIN=juniorfox.net \
       --env DHCPSERVER=dhcpd \
       --env SLAAC_RESOLVER=slaac-resolver \
       --volume /run/slaac-resolver:/slaac-resolver \
       --volume /var/lib/dhcp/dhcpd.leases:/dhcp.leases \
       --volume $(pwd)/unbound-conf:/unbound-conf \
       --volume certificates:/etc/certificates/ \
       docker.io/cjuniorfox/unbound:latest
   ```

2. **Run the Development Version**:

   ```sh
   docker run -d \
       --name unbound-server-dev \
       --restart always \
       --env DOMAIN=juniorfox.net \
       --env DHCPSERVER=dhcpd \
       --volume /var/lib/dhcp/dhcpd.leases:/dhcp.leases \
       --env SLAAC_RESOLVER=slaac-resolver \
       --volume /run/slaac-resolver:/slaac-resolver
       --volume $(pwd)/unbound-conf:/unbound-conf \
       --volume certificates:/etc/certificates/ \
       docker.io/cjuniorfox/unbound:developer
   ```

### Notes

- Ensure the required volumes and environment variables are correctly set up.

## Volumes

The following volumes are used in the container:

- **`/unbound-conf`**: Custom Unbound configuration files.
- **`/etc/unbound/unbound.conf.d/`**: Additional Unbound configuration files.
- **`/dhcp.leases`**: DHCP leases file or directory.
- **`/slaac-resolver`**: The directory containing the SLAAC name resolution files.
- **Persistent Volume Claims (PVC)**:
  - `certificates-pvc`: Mounted at `/etc/certificates/`.
  - `unbound-conf-pvc`: Mounted at `/etc/unbound/unbound.conf.d/`.

Ensure that the paths for the volumes are correctly set up in your environment.

## Healthcheck

The container includes a health check to ensure that the Unbound server is up and running. You can verify the health status using the following command:

```sh
docker inspect --format='{{json .State.Health}}' unbound-server
```

## Troubleshooting

### Docker Daemon Not Running

If you encounter an error like `Cannot connect to the Docker daemon`, ensure that the Docker service is running:

```sh
sudo systemctl start docker
```

## Testing

Unit tests are included to validate the functionality of the Unbound watcher scripts. The tests cover the following scenarios:

- Parsing leases from a file or directory.
- Identifying new or updated leases.
- Detecting expired leases.
- Detecting leases that no longer exist.
- Updating Unbound records correctly.

### Running the Tests

1. **Install Dependencies**:
   Ensure you have Python 3 and `unittest` installed.

2. **Set the `PYTHONPATH`**:
   Add the `unbound` directory to the `PYTHONPATH` environment variable:

   ```sh
   export PYTHONPATH=/path/of/the/project/app/dhcp_watcher:$PYTHONPATH
   ```

3. **Run the Tests**:
   Use the following command to run all tests:

   ```sh
   python3 -m unittest discover -s /path/of/the/project/tests
   ```

4. **Expected Output**:
   If all tests pass, you should see output similar to:

   ```sh
   ....
   ----------------------------------------------------------------------
   Ran 4 tests in 0.004s

   OK
   ```

## Changelog

### 2025-07-01

- Added support for **SLAAC Name resolution** Watcher.

### 2025-03-30

- Added **System-Networkd DHCP Server** Watcher.
- Added the option of not having any DHCP Server Watcher at all.
- Added unit tests for parsing leases, detecting changes, and updating Unbound.

### 2024-11-01

- Added **Kea DHCP Server** Watcher.

### 2023-10-15

- Added **DNSMasq** Watcher.
- Renamed volume **/dhcpd** to **/dhcpd.leases** to reflect the leases file instead of a directory containing the leases file.
