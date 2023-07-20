# MyHelpline

MyHelpline is a communication framework for support call centers.

## Requirements

 * Python 3.6 +
 * [Django](http://djangoproject.com/) 2.2.1+
 * [Asterisk](http://www.asterisk.org) 1.4+ and enabled manager
 * Redis >= 2.6.0
 * RabbitMQ
 * Nginx
 * PostgreSQL

## Technology Platform
 * Nginx
 * Python
 * Linux (Ubuntu)
 * PostgreSQL
 * Asterisk with AMI enabled.
 * RapidPRO

## Installation

Install package dependencies in Ubuntu

```
    sudo apt install -y python3-dev
    sudo apt install -y nodejs-dev node-gyp libssl1.0-dev
    sudo apt install -y nodejs
    sudo apt install -y npm
    sudo apt install -y virtualenv
    sudo npm install -g bower
    sudo apt install -y gettext
    sudo apt install -y postgresql postgresql-contrib
    sudo apt install -y libmemcached-dev
    sudo apt install -y gdal-bin
    sudo apt install -y libz-dev
    sudo apt install -y postgis
    sudo apt install -y unixodbc
    sudo apt install -y libmaxminddb0 libmaxminddb-dev mmdb-bin
    sudo apt-get install -y libmemcached-dev
    sudo apt-get install -y zlib1g-dev
    sudo apt install -y memcached


```

Install package dependencies in RHEL

```
sudo yum install -y python-devel.x86_64
sudo yum install -y python-devel
sudo yum install -y libpq5.x86_64
sudo yum install -y libpq5
sudo yum install -y libpq5.x86_64
sudo yum install -y libpq5
sudo yum install -y libpq5-devel.x86_64
sudo yum install -y python3-devel.x86_64
sudo yum install -y gcc
sudo yum install -y gdal-libs.x86_64 gdal-devel.x86_64
```


To bulk install the requirements in Ubuntu run:

    sudo ./script/install/ubuntu



After you install nodejs you might want to run the following command:
Not required in Ubuntu 18.04 +

```
    ln -s /usr/bin/nodejs /usr/bin/node
```

```
    $ sudo npm install -g bower
```


## Database setup

### In the base OS

Replace username and db name accordingly.

.. code-block:: sh

    sudo su postgres -c "psql -c \"CREATE USER helplineuser WITH PASSWORD 'helplinepasswd';\""
    sudo su postgres -c "psql -c \"CREATE DATABASE helpline OWNER helplineuser;\""
    sudo su postgres -c "psql -d helpline -c \"CREATE EXTENSION IF NOT EXISTS postgis;\""
    sudo su postgres -c "psql -d helpline -c \"CREATE EXTENSION IF NOT EXISTS postgis_topology;\""

## Asterisk setup

### In the PBX Server


On /etc/odbc.ini add the following connection properties.

```
[helplineconn]
Driver      = PostgreSQL Unicode
Description = PostgreSQL Connection to Asterisk database
Database    = helpline
; This should match your helpline application database
Servername  = 127.0.0.1
; OR IP of your database server
User        = helplineuser
Password    = helplinepasswd
Port        = 5432
```

On /etc/asterisk/res_odbc.conf make sure to add the following.
The config above lets Asterisk know which database to use, in this case it will use the one above.
If you have a different username and password or database, you can specifiy it here.


[helpline]
enabled => yes
dsn => helplineconn
username => helplineuser
password => helplinepasswd
pre-connect => yes;

On /etc/asterisk/manager.conf set command permission for read and write, example:

```
    [helpline]
    secret = my_super_secret_password
    read = command
    write = command,originate,call,agent
```

#### AMI Options
    * _originate_ for spy, whisper and barge.
    * _call_ for hanging up calls.
    * _agent_ remove and add agents to and from the queues.

##  Prepare environment

 go to project directory
 ```
  git clone https://github.com/childhelpline/myhelpline.git
  cd myhelpline
  cp helpline/config.ini-dist helpline/config.ini
  cp myhelpline/localsettings.py-sample myhelpline/localsettings.py
 ```
  Edit config.ini file with Manager Asterisk parameters

Create a virtual environment for the application.

```
    virtualenv ~/.env/
```

Activate virtual environment:

```
    source ~/.env/bin/activate
```

Install requirements:

```
    pip install -r requirements.txt
```

## Translations
 ```
  python manage.py compilemessages
 ```

## Migrations 
Make sure PostgreSQl is running and the cridentials for the  database are available in your "myhelpline/localsettings.py" 
```
python manage.py makemigrations
python manage.py migrate
   ```
## Install components using bower
 ```
 python manage.py bower install
 ```
 ## Create User
 Run the following command and follow the prompt
  ```
  python manage.py createsuperuser
  ```
 
## Run webserver
 ```
    python manage.py runserver 0.0.0.0:8000
 ```

Go to url of the machine http://IP:8000


## How to contribute

 * Fork the project
 * Create a feature branch (git checkout -b my-feature)
 * Add your files changed (git add file_change1 file_change2, etc..)
 * Commit your changes (git commit -m "add my feature")
 * Push to the branch (git push origin my-feature)
 * Create a pull request

