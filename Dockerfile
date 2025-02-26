FROM python:3.9-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 5000

ENV FLASK_APP=app.py
ENV FLASK_ENV=production

CMD ["sh", "-c", "flask fetch-gpu-data & python3 scripts/sync_firebase_users.py & gunicorn --bind 0.0.0.0:5000 app:create_app"]