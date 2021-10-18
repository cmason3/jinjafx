## Docker/Podman for JinjaFx Server

JinjaFx Server will always be available in Docker Hub at [https://hub.docker.com/repository/docker/cmason3/jinjafx_server](https://hub.docker.com/repository/docker/cmason3/jinjafx_server) - the `latest` tag will always refer to the latest released version.

Using HAProxy in front of JinjaFx Server is the preferred way with HAProxy dealing with TLS termination. The following commands (using sudo) will launch two containers - one for HAProxy which listens on port 80 (redirects to 443) and 443 (requires host networking) and one for JinjaFx Server which listens on localhost on port 8080.

The first step is to create a local user which maps to the UID/GID of the non-root user inside the container - as the certificate for HAProxy sits outside the container we need to give the local user read access to it.

```
groupadd -g 99 -r jinjafx
useradd -u 99 -g 99 -r jinjafx

chown root:jinjafx <certificate.pem>
chmod 640 <certificate.pem>
```

### HAProxy

```
podman build --no-cache --pull -t jinjafx_haproxy:latest https://raw.githubusercontent.com/cmason3/jinjafx/main/jinjafx_server/docker/Dockerfile.HAProxy

podman create --name jinjafx_haproxy --tz=local --cap-add net_bind_service --network host -v <certificate.pem>:/usr/local/etc/haproxy/fullchain.pem jinjafx_haproxy:latest

podman generate systemd -n --restart-policy=always jinjafx_haproxy | tee /etc/systemd/system/jinjafx_haproxy.service 1>/dev/null

systemctl daemon-reload
systemctl enable --now jinjafx_haproxy
```

The above commands will pass through the combined TLS certificate (private key and full certificate chain) to HAProxy - you will need to replace `<certificate.pem>` with the location of your certicate (this is presented inside the container as `/usr/local/etc/haproxy/fullchain.pem`) and you will HUP the container using `podman kill -s HUP jinjafx_haproxy` after you renew the certificate. The Dockerfile will download the [haproxy.cfg](https://raw.githubusercontent.com/cmason3/jinjafx/main/jinjafx_server/docker/haproxy.cfg) file from this repository.

### JinjaFx Server

```
podman create --name jinjafx_server --tz=local -p 127.0.0.1:8080:8080 docker.io/cmason3/jinjafx_server:latest

podman generate systemd -n --restart-policy=always jinjafx_server | tee /etc/systemd/system/jinjafx_server.service 1>/dev/null

systemctl daemon-reload
systemctl enable --now jinjafx_server
```

Once the two containers are running you should be able to point your browser at port 443 and it will be passed through to JinjaFx Server.
