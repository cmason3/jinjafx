## Docker for JinjaFx Server

### Docker Hub

JinjaFx Server will always be available in Docker Hub at [https://hub.docker.com/repository/docker/cmason3/jinjafx](https://hub.docker.com/repository/docker/cmason3/jinjafx) - the `latest` tag will always refer to the latest released version of JinajaFx.

### Dockerfiles

There are two Dockerfiles - `Dockerfile.Release` and `Dockerfile.Master`. The first (and recommended) will build the Docker container from the latest release and the second (for testing) will build the Docker container by performing a clone of the `master` branch.

### /etc/haproxy/haproxy.cfg

The preferred way to use JinjaFx Server is with HAProxy running in front of it. Please see https://ssl-config.mozilla.org/#server=haproxy for TLS termination options, but the following will forward port 80 requests to the JinjaFx Server running in a container that has been exposed on 127.0.0.1:8080.

```
frontend fe_jinjafx
  bind *:80
  mode http
  default_backend be_jinjafx

backend be_jinjafx
  mode http
  server jinjafx 127.0.0.1:8080
```
