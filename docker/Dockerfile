FROM python:3.8-slim-buster
MAINTAINER Chris Mason <chris@jinjafx.org>

ARG VERSION="1.0.2"

RUN apt-get update; apt-get install -y curl; apt-get clean
RUN pip3 --no-cache-dir install jinja2 pyyaml
RUN curl -Ls https://github.com/cmason3/jinjafx/archive/v${VERSION}.tar.gz | tar -zx -C /opt --transform="s/jinjafx-[0-9\.]*/jinjafx/"

USER nobody

EXPOSE 8080

WORKDIR /opt/jinjafx

CMD [ "/usr/bin/python3", "jinjafx_server.py", "-s" ]
