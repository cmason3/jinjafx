## Docker for JinjaFx Server

### Build Docker Image

There are two Dockerfiles - `Dockerfile.Release` will build the Docker containter from the latest release and `Dockerfile.Master` will build the Docker container by performing a clone of the `master` branch. It is recommended that `Dockerfile.Release` is used as it is more likely to be stable.

```
docker image build -t jinjafx:latest https://raw.githubusercontent.com/cmason3/jinjafx/master/docker/Dockerfile.Release
```

### Run Docker Container
```
docker container run -d --name jinjafx --restart unless-stopped -e TZ=Europe/London -p 127.0.0.1:8080:8080 jinjafx:latest
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
