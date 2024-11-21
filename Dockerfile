FROM docker.io/rasa/rasa:3.6.20-full

USER root
COPY requirements.txt  /app/requirements.txt
RUN pip install -r /app/requirements.txt
COPY . /app
RUN chown -R rasa /app

USER rasa
RUN cd /app && rasa train
