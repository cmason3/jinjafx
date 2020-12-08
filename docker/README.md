## Docker for JinjaFx Server

### Docker Hub

JinjaFx Server will always be available in Docker Hub at [https://hub.docker.com/repository/docker/cmason3/jinjafx](https://hub.docker.com/repository/docker/cmason3/jinjafx) - if you use this image then the build step below can be skipped. The tag `latest` will always refer to the latest released version of JinajaFx.

### Build Docker Image

There are two Dockerfiles - `Dockerfile.Release` and `Dockerfile.Master`. The first (and recommended) will build the Docker container from the latest release and the second (for testing) will build the Docker container by performing a clone of the `master` branch.

```
docker build --no-cache -t jinjafx:latest https://raw.githubusercontent.com/cmason3/jinjafx/master/docker/Dockerfile.Release
```

### Run Docker Container
```
docker run -d --name jinjafx --restart unless-stopped -e TZ=<TIMEZONE> -p 127.0.0.1:8080:8080 jinjafx:latest
```

By default it won't enable a repository directory so 'Get Link' won't work - it will return 503 Service Unavailable. To enable this functionality you need to specify `-r` with a directory (or `-s3` if using AWS S3) - the following example will demonstrate how you can use "/var/lib/jinjafx" on the local filesystem (exposed inside the container as "/var/lib/jinjafx"), which will persist if the container is reloaded:

```
sudo mkdir /var/lib/jinjafx
sudo chmod a+rwx /var/lib/jinjafx

docker run -d --name jinjafx --restart unless-stopped -e TZ=<TIMEZONE> -p 127.0.0.1:8080:8080 -v /var/lib/jinjafx:/var/lib/jinjafx jinjafx:latest -r /var/lib/jinjafx
```

### Podman Equivalent using Systemd with AWS S3

```
sudo podman build --no-cache -t jinjafx:latest https://raw.githubusercontent.com/cmason3/jinjafx/master/docker/Dockerfile.Release

sudo podman create --name jinjafx -e TZ=<TIMEZONE> -e AWS_ACCESS_KEY=<KEY> -e AWS_SECRET_KEY=<KEY> -p 127.0.0.1:8080:8080 jinjafx:latest -s3 <bucket>.s3.<region>.amazonaws.com
sudo podman generate systemd -n --restart-policy=always jinjafx | sudo tee /etc/systemd/system/jinjafx.service

sudo systemctl enable jinjafx
sudo systemctl start jinjafx
```

#### To Upgrade Container
```
sudo podman build ...

sudo systemctl stop jinjafx
sudo podman rm jinjafx

sudo podman create ...
sudo podman generate systemd ...

sudo systemctl daemon-reload
sudo systemctl start jinjafx
```

### /etc/haproxy/haproxy.cfg

The preferred way to use JinjaFx Server is with HAProxy running in front of it. Please see https://ssl-config.mozilla.org/#server=haproxy for TLS termination options, but the following will forward port 80 requests to JinjaFx running in Docker or Podman that has been exposed on 127.0.0.1:8080.

```
frontend fe_jinjafx
  bind *:80
  mode http
  default_backend be_jinjafx

backend be_jinjafx
  mode http
  server jinjafx 127.0.0.1:8080
```
