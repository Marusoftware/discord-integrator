#!/bin/sh
set -e

chown -R nonroot ./

exec /usr/local/bin/pysu nonroot "$@"