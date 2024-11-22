# Episodes
Self-hosted TV show Episode tracker built using django and bootstrap5.<br/>
Episodes allows you to keep track of your favourite tv shows either continuing or ending.

Using http://thetvdb.com/ for metadata.

Forked from https://github.com/guptachetan1997/Episodes

Inspired from https://github.com/jamienicol/episodes

## Install using Docker Compose

1. Download the docker-compose.yml file to your computer
2. Edit the docker-compose.yml file to change the SECRET_KEY and CSRF_TRUSTED_ORIGINS variables, and change the port if you want to.
    * SECRET_KEY - this can be generated with python like this:
      ```python
      python3 -c 'import secrets; print(secrets.token_hex(100))'
      ```
    * CSRF_TRUSTED_ORIGINS - this needs to be where you will access the server from, multiple origins can be separated by a space like this:    
      ```
      "http://localhost https://example.com"
      ```
    * Change the port on the left side only unless you know what you are doing. If you want to access from port 8080, change to `"8080:3000"`
3. Run: `docker compose pull`
4. Run: `docker compose up -d`
5. Access your server from http://localhost:3000

## Install Manually

To use clone the production branch, install requirements, run the following terminal commands:

### open to the directory you want to install Episodes (change /opt to wherever you want)  

> cd /opt

### clone this Episodes repo

> git clone https://github.com/bryangerlach/Episodes.git

### open the Episodes directory

> cd Episodes

### setup a python virtual environment called episodes (or whatever name you want)

> python -m venv episodes

### activate the python virtual environment on linux

> source episodes/bin/activate

 or on windows

> ./episodes/Scripts/activate

### install the python dependencies

> pip install -r requirements.txt

### setup the database

> python manage.py migrate

### run the server, change 8000 with whatever you want

> python manage.py runserver 0.0.0.0:8000

### you can now access the webpage from http://localhost:8000, you can use nginx, caddy, or other reverse proxy for better access

## You will also want to set up a cron job to update the database with thetvdb api data
### The following command will add a cron job to update all continuing shows for new data at 3am and 3pm everyday (this only works on linux):

> python manage.py crontab add

to show cron jobs created by this server

> python manage.py crontab show

to delete cron jobs created by this server

> python manage.py crontab remove

### You can also manually update the database in the app by pressing the update button, or from commandline by running:

> python manage.py update_db
    
![alt tag](https://raw.githubusercontent.com/bryangerlach/Episodes/master/1.png)
![alt tag](https://raw.githubusercontent.com/bryangerlach/Episodes/master/2.png)
![alt tag](https://raw.githubusercontent.com/bryangerlach/Episodes/master/3.png)
![alt tag](https://raw.githubusercontent.com/bryangerlach/Episodes/master/4.png)
