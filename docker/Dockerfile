FROM python:3
MAINTAINER Chris Mason <chris@jinjafx.org>

ARG VERSION="1.0.2"

RUN pip3 install jinja2
RUN curl -Ls https://github.com/cmason3/jinjafx/archive/v${VERSION}.tar.gz | tar -zx -C /opt --transform="s/jinjafx-${VERSION}/jinjafx/"

USER nobody

EXPOSE 8080

CMD [ "/usr/bin/python3", "/opt/jinjafx/jinjafx_server.py", "-s" ]
