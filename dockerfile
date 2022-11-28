# syntax=docker/dockerfile:1

FROM python:3.10.6

WORKDIR /proxy

COPY requirements.txt requirements.txt
RUN pip3 install -r requirements.txt

COPY . /proxy

EXPOSE 7000
