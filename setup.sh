#!/bin/bash

mkdir -p databases
mkdir -p logs

# start the mongo servers
docker run --rm --name mongodb -p 27017:27017 --network mongo-net -v $(pwd)/databases:/data/db -d mongo
docker run --rm --name mongo-express -p 8081:8081 --network mongo-net -e ME_CONFIG_MONGODB_URL="mongodb://mongodb:27017" -d mongo-express

# start the redis server as daemon
# (even if you execute this script multiple times, only one server will run)
sudo redis-server /opt/local/etc/redis.conf --daemonize yes