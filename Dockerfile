FROM python:3.11

WORKDIR /app

COPY . .
RUN apt-get update
RUN apt-get install -y cron
RUN pip install --no-cache-dir -r requirements.txt

EXPOSE 3000

RUN chmod +x /app/docker-entrypoint.sh
ENTRYPOINT [ "/app/docker-entrypoint.sh" ]

CMD ["gunicorn", "-c", "gunicorn.conf.py", "Episodes.wsgi:application"]