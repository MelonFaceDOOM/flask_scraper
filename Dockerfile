FROM python:3.6-alpine

#create login with no password
RUN adduser -D fs

WORKDIR /home/flask_scraper

COPY requirements.txt requirements.txt

# for pyscopg2 (for postgresql)
# RUN apk update && apk add postgresql-dev gcc python3-dev musl-dev

# for pyzmqt
#RUN apk add build-base libzmq python3 zeromq-dev

# for lxml
RUN apk add g++ libxslt-dev
# RUN apk add libxml2-dev libxslt1-dev

RUN python -m venv venv
RUN venv/bin/pip install --upgrade pip
RUN venv/bin/pip install -r requirements.txt
RUN venv/bin/pip install gunicorn pymysql

COPY app app
COPY migrations migrations
COPY fs.py extensions.py config.py boot.sh ./
RUN chmod +x boot.sh

ENV FLASK_APP fs.py

RUN chown -R fs:fs ./
USER fs

EXPOSE 5000
ENTRYPOINT ["./boot.sh"]
