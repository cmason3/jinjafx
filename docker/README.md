## Docker for JinjaFx Server

Work in progress - not finished yet

### Build Docker Image
```
docker image build --no-cache -t jinjafx:latest https://raw.githubusercontent.com/cmason3/jinjafx/master/docker/Dockerfile
```

### Run Docker Container
```
docker container run -d --name jinjafx --restart unless-stopped -p 0.0.0.0:8080:8080 jinjafx:latest
```
