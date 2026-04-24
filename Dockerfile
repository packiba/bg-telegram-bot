FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN mkdir -p data

CMD gunicorn wsgi:application --bind 0.0.0.0:${PORT:-5000} --worker-class aiohttp.GunicornWebWorker --workers 1 --timeout 120
