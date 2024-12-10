#!/bin/sh
sed -e "s|\${MONGODB_PORT}|${MONGODB_PORT}|g" /etc/mongod.template.conf > /etc/mongod.conf
exec mongod --config /etc/mongod.conf