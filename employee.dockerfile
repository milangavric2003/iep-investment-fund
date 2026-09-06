FROM python:3.13-slim

WORKDIR /app

COPY requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY decorators.py fund_configuration.py fund_helpers.py employee.py mongo_seed.py fund_start.sh ./

RUN chmod +x ./fund_start.sh

ENV SERVICE_MODULE=employee.py

ENTRYPOINT ["./fund_start.sh"]