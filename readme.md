# Project: HomeTemp v0.4

The original idea of `HomeTemp` was to automatically measure the temperature and humidity of a room and create plots
visualizing the data. Currently supported temperature and humidity sensors are `AM2302`. `DHT11` and `DHT22` sensor,
connected to a Raspberry Pi 4 Model B or Raspberry Pi 5.
The fork `BaseTemp` was created to periodically measure and save the temperature and humidity of my basement. It also
takes pictures using a `5MP Raspberry Pi camera module` with an OV5647 sensor and is able to take and send a live
picture via commanding.

## Requirements

- Docker
- libpq-dev
- xvfb
- Everything in `requirements.txt` for pip

## Current Features

- Initializing Docker container for Postgres database or reuse existing
- Connecting to postgres database
- CRUD operations for tables and columns
- Creating data visualizations using seaborn and matplot
- Sending emails containing statistic data as text and visualizations as pdf
- Recovering sensor data from log file
- Data fetching from various API endpoints/websites
- Commanding via email
- Taking pictures via camera module (only tested on **Raspberry Pi 4 Model B**)

## Installation Instructions

The following steps needs to be performed once to assure correct driver setup.
For venv use,

```shell
python -m venv --system-site-packages <PATH_TO_VENV>
```

### Install Dependencies

Use this code snippet to install the required dependencies. Either use pip install with module name or use the
requirements file.

```sh
sudo apt-get install libpq-dev xvfb
## Module names
pip install pillow rpi-lgpio RPI.GPIO lgpio psycopg2 gpiozero docker seaborn SQLAlchemy requests selenium schedule pyvirtualdisplay bs4 jupyter_client jupyter_core
# or
#pip install -r requirements.txt
```

### Configure Hometemp.ini

At first, rename `default_hometemp.ini` to `hometemp.ini` and assign values to all variables.

### Install Chromedriver

Selenium is used to fetch data from endpoints which rely on Javascript.
On a raspberry pi, install chromium driver with the following command and set permissions:

```sh
sudo apt-get install chromium-chromedriver
sudo chmod -R 755 /usr/lib/chromium-browser 
```

## Start Instructions

The following sections provide information and tips for starting the related services and dependencies.

### Start Docker Container

Images and containers should be pulled or created/reused automatically. However, for this to work, the user needs to be
added to the docker group:

```sh
sudo usermod -aG docker $USER
```

Afterward, a reboot is required otherwise the following error will occur:

```
docker.errors.DockerException: Error while fetching server API version: ('Connection aborted.', PermissionError(13, 'Permission denied'))
```

It is also possible to start the container via the following command. HomeTemp will use this container if the name of
the container
matches the name specified in `hometemp.ini`.

```sh
docker run --name postgres-db -e POSTGRES_PASSWORD=<ENTER PASSWORD HERE> -d -p 5432:5432 postgres:latest
```

after a restart, use `docker ps -a` to get the container ID and then `docker start <containerID>` to start the old
database.

## Update/Restore Instructions

Use the following commands to import and export database:

```sh
# Export
docker exec -t postgres-db sh -c 'PGPASSWORD=<DB_PASSWORD> pg_dump -U <DB_USER> <DB_NAME>' > backup.sql

# Import
# start container
docker cp backup.sql postgres-db:/backup.sql
docker exec -i postgres-db sh -c 'PGPASSWORD=<DB_PASSWORD> psql -U <DB_USER> -d <DB_NAME>' < backup.sql
```

