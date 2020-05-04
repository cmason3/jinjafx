## Docker for JinjaFx Server

### Build Docker Image
```
docker image build -t jinjafx:latest https://raw.githubusercontent.com/cmason3/jinjafx/master/docker/Dockerfile
```

### Run Docker Container
```
docker container run -d --name jinjafx --restart unless-stopped -p 127.0.0.1:8080:8080 jinjafx:latest
```

### /etc/haproxy/haproxy.cfg

The preferred way to use JinjaFx Server is with HAProxy running in front of it. Please see https://ssl-config.mozilla.org/#server=haproxy for TLS termination options.

```
frontend fe_jinjafx
  bind *:80
  mode http
  default_backend be_jinjafx

backend be_jinjafx
  mode http
  server jinjafx 127.0.0.1:8080
```
