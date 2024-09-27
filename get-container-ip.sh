sudo podman inspect unbound-server --format '{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}'
