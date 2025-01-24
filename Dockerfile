FROM python:3.9-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 5000

ENV FLASK_APP=app.py
ENV FLASK_ENV=production

CMD ["sh", "-c", "flask fetch-gpu-data & gunicorn --bind 0.0.0.0:5000 app:create_app"]