FROM python:3.13-slim

WORKDIR /app

COPY requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY configuration.py main.py models.py decorators.py migrate.py seed.py seed.sql start.sh ./
COPY migrations ./migrations

RUN chmod +x ./start.sh

ENTRYPOINT ["./start.sh"]