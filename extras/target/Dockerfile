FROM alpine:3.19
RUN apk add --no-cache rsync tini

COPY rsyncd.conf /etc/isopod-target/rsyncd.conf
COPY entrypoint.sh /usr/local/bin/entrypoint.sh

VOLUME /mnt/isopod-target
ENTRYPOINT ["tini", "--", "/usr/local/bin/entrypoint.sh"]
