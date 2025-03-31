FROM python:3.9-alpine

WORKDIR /app

COPY app/requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY app/ .

ENV FLASK_ENV=development
ENV FLASK_DEBUG=1

EXPOSE 5002

CMD ["python", "simple_server.py"]
