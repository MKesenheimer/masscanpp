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

other examples:
```bash
sudo python scanner.py -p 22 --protocol ssh
sudo python scanner.py -p 80 --protocol http
sudo python scanner.py -p 8080 --protocol http
sudo python scanner.py -p 2111 --protocol colaA
sudo python scanner.py -p 2112 --protocol colaB
```

go to [mongo-express](http://127.0.0.1:8081) and log in with `admin` and `pass`.

filtering for results on mongo-express (advanced search):

- port 80: `{port: 8080}`
- login in HTTP response: `{response: /login/i}`
- port 8080 and 200 Status code: `{port: 8080, response: /HTTP\/1.1 200/i}`
- port 22 and SSH response: `{port: 22, response: /SSH-/i}`
- specific SSH version: `{port: 22, response: /SSH-2.0-OpenSSH_9.2p1/i}`
- more options: `{response: {$regex: 'Ubuntu', $options: "$i"}}`


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
