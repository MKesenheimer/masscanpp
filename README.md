install the python dependencies:
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r Requirements.txt
```


start redis and mongo servers on localhost:
```bash
./setup.sh
```

launch the dramatiq workers:
```bash
python -m dramatiq scanner
#python -m dramatiq scanner --watch .
```

launch the scan in a separate terminal window:
```bash
sudo python scanner.py -p 80
```

go to [mongo-express](http://127.0.0.1:8081) and log in with `admin` and `pass`.

query the number of jobs in queue:
```bash
redis-cli
> LLEN dramatiq:default
```

clear all keys from redis:
```bash
redis-cli
> flushall
```
