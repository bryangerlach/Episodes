# Episodes
Self-hosted TV show Episode tracker built using django and bootstrap5.<br/>
Episodes allows you to keep track of your favourite tv shows either continuing or ending.

Using http://thetvdb.com/ for metadata.

Forked from https://github.com/guptachetan1997/Episodes

Inspired from https://github.com/jamienicol/episodes


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
    
![alt tag](https://raw.githubusercontent.com/bryangerlach/Episodes/master/1.jpeg)
![alt tag](https://raw.githubusercontent.com/bryangerlach/Episodes/master/2.jpeg)
![alt tag](https://raw.githubusercontent.com/bryangerlach/Episodes/master/3.jpeg)
