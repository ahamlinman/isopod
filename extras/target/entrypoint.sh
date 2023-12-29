#!/bin/sh

if [ "$(id -u)" -eq 0 ] || [ "$(id -g)" -eq 0 ]; then
	echo "isopod-target: refusing to run as root" 1>&2
	exit 120
fi

if tmpfile="$(mktemp -qp /)" && [ "$tmpfile" ]; then
	rm -f "$tmpfile"
	echo "isopod-target: refusing to run on read-write root filesystem" 1>&2
	exit 120
fi

echo "isopod-target: starting daemon for UNENCRYPTED rsync transfers" 1>&2
set -x
exec rsync --daemon --no-detach --config=/etc/isopod-target/rsyncd.conf "$@"
