## Docker for JinjaFx Server

### Build Docker Image

There are two Dockerfiles - `Dockerfile.Release` and `Dockerfile.Master`. The first (and recommended) will build the Docker container from the latest release and the second (for testing) will build the Docker container by performing a clone of the `master` branch.

```
docker image build --no-cache -t jinjafx:latest https://raw.githubusercontent.com/cmason3/jinjafx/master/docker/Dockerfile.Release
```

### Run Docker Container
```
docker run -d --name jinjafx --restart unless-stopped -e TZ=Europe/London -p 127.0.0.1:8080:8080 jinjafx:latest
```

By default it won't enable a repository directory so 'Get Link' won't work - it will return 503 Service Unavailable. To enable this functionaility you need to specify `-r` with a directory - the following example will demonstarte how you can use "/tmp" on the local filesystem, which is outside the Docker container and will persist if the container is reloaded:

```
docker run -d --name jinjafx --restart unless-stopped -e TZ=Europe/London -p 127.0.0.1:8080:8080 jinjafx:latest
```

### /etc/haproxy/haproxy.cfg

The preferred way to use JinjaFx Server is with HAProxy running in front of it. Please see https://ssl-config.mozilla.org/#server=haproxy for TLS termination options, but the following will forward port 80 requests to JinjaFx running in Docker that has been exposed on 127.0.0.1:8080.

```
frontend fe_jinjafx
  bind *:80
  mode http
  default_backend be_jinjafx

backend be_jinjafx
  mode http
  server jinjafx 127.0.0.1:8080
```
