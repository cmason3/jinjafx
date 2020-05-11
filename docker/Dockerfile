FROM python:3.8-slim-buster
MAINTAINER Chris Mason <chris@jinjafx.org>

ARG VERSION="1.0.5"

RUN apt-get update; apt-get install -y curl; apt-get clean
RUN pip3 --no-cache-dir install ansible netaddr
RUN curl -Ls https://github.com/cmason3/jinjafx/archive/v${VERSION}.tar.gz | tar -zx -C /opt --transform="s/jinjafx-[0-9\.]*/jinjafx/"

RUN useradd -m jinjafx
USER jinjafx

EXPOSE 8080

WORKDIR /opt/jinjafx

CMD [ "/usr/local/bin/python3", "-u", "jinjafx_server.py", "-s", "-l", "0.0.0.0", "-p", "8080" ]
