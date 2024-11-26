#!/bin/bash

echo "Migrate the Database at startup of project"

# Wait for few minutes and run db migraiton
while ! python manage.py migrate  2>&1; do
    echo "Migration is in progress status"
    sleep 3
done

service cron restart

python manage.py crontab add

exec "$@"