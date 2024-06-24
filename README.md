
install redis (depending on your system):
```bash
sudo port install redis
```
install the python dependencies:
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r Requirements.txt
```


start redis server on localhost:
```bash
sudo redis-server /opt/local/etc/redis.conf
```

launch the dramatiq workers:
```bash
#python -m dramatiq scanner
python -m dramatiq scanner --watch .
```

launch the scan in a separate terminal window:
```bash
sudo python scanner.py -p 80
```

launch a mongodb and mongo-express docker containers:
```bash
docker network create mongo-net
docker run --rm --name mongodb -p 27017:27017 --network mongo-net -v $(pwd)/databases:/data/db -d mongo
docker run -it --rm --name mongo-express -p 8081:8081 --network mongo-net -e ME_CONFIG_MONGODB_URL="mongodb://mongodb:27017" mongo-express
```

go to [mongo-express](http://127.0.0.1:8081) and log in with `admin` and `pass`.