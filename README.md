
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
