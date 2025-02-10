FROM python:3.11

WORKDIR /app

COPY . .
RUN apt-get update
RUN apt-get install -y cron
RUN pip install --no-cache-dir -r requirements.txt

ENV PYTHONUNBUFFERED=1

EXPOSE 3000

RUN chmod +x /app/docker-entrypoint.sh
ENTRYPOINT [ "/app/docker-entrypoint.sh" ]

HEALTHCHECK --interval=30s --timeout=5s --retries=3 CMD wget --spider 0.0.0.0:3000

CMD ["gunicorn", "-c", "gunicorn.conf.py", "Episodes.wsgi:application"]