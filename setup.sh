#!/bin/bash
# (even if you execute this script multiple times, only one server will run)

mkdir -p databases
mkdir -p logs
mkdir -p redis

docker network create masscan-net

# start the mongo servers
docker run --rm --name mongodb -p 27017:27017 --network masscan-net -v $(pwd)/databases:/data/db -d mongo
docker run --rm --name mongo-express -p 8081:8081 --network masscan-net -e ME_CONFIG_MONGODB_URL="mongodb://mongodb:27017" -d mongo-express

# start the redis-server
#sudo redis-server /opt/local/etc/redis.conf --daemonize yes
docker run --rm --name redis -p 6379:6379 --network masscan-net -v $(pwd)/redis:/data -d redis redis-server --save 60 1 --loglevel warning

# interact with redis:
# docker run -it --network masscan-net --rm redis redis-cli -h redis
