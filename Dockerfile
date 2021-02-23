FROM python:3.8.5-alpine

COPY requirements.txt .

RUN pip install -U -r requirements.txt