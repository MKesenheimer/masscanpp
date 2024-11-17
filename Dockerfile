FROM ubuntu:20.04
ENV DEBIAN_FRONTEND="noninteractive" 

RUN apt-get update &&  apt-get install -y git 
RUN apt autoclean && apt autoremove
RUN rm -rf /var/lib/apt/lists/*
RUN git clone https://github.com/RedSiege/EyeWitness.git 

WORKDIR /EyeWitness/Python/setup
RUN ./setup.sh

RUN mkdir /tmp/EyeWitness
WORKDIR /tmp/EyeWitness/
ENTRYPOINT ["python3", "/EyeWitness/Python/EyeWitness.py", "--no-prompt"]
