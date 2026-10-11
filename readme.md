# Project: HomeTemp v0.7-Dev

The original idea of `HomeTemp` was to automatically measure the temperature and humidity of a room and create plots
visualizing the data. Currently supported temperature and humidity sensors are `AM2302`, `DHT11` and `DHT22`,
connected to a Raspberry Pi 4 Model B or Raspberry Pi 5.
The fork `BaseTemp` was created to periodically measure and save the temperature and humidity of my basement. It also
takes pictures using a `5MP Raspberry Pi camera module` with an OV5647 sensor and is able to take and send a live
picture via commanding.

## Requirements

- screen
- Docker
- libpq-dev
- xvfb
- Python >= 3.9
- Everything in `requirements.txt` for pip

## Current Features

- Initializing Docker container for Postgres database or reuse existing
- Connecting to postgres database
- CRUD operations for tables and columns
- Creating data visualizations using seaborn and matplot
- Sending emails containing statistic data as text and visualizations as pdf
- Data fetching from various API endpoints/websites
- Commanding via email
- Taking pictures (timed or commanded) via camera module (only tested on **Raspberry Pi 4 Model B**)
- Create timelapse video of a set of pictures
- Grafana Web Frontend
- MotionEye Live Camera Frontend
- Ecowitt integration

## Default Ports
The following list shows the which instance uses which ports as default:

- HomeTemp/BaseTemp: 3000 Grafana Web Frontend
- FetchTemp: 8001 Prometheus
- HomeTemp: 8002 Prometheus
- BaseTemp: 8003 Prometheus
- MotionEye: 8765 Web Frontend
- Postgres: 5432
- Loki: 3100
- Alloy: 32000

## Installation Instructions

The following steps needs to be performed once to assure correct driver setup.

### Install Dependencies

First install teh system dependencies, then create the virtual environment for python.

#### Install System Dependencies

Install **docker**, e.g., as described [here for raspberry-pi](https://docs.docker.com/engine/install/raspberry-pi-os/).

```sh
sudo apt update
sudo apt install screen libpq-dev xvfb
```

In case data fetching from endpoints is a desired feature, chromedriver has to be installed as well (see below).

#### Virtual Environment

For venv setup, use `--system-site-package` parameter. The following snippets creates the environment in the folder
`.venv`. The `start.sh` expects the folder name to be `.venv`.

```shell
python -m venv --system-site-packages .venv
```

After the venv is activated, e.g. by `source .venv/bin/activate`, install the dependencies via `requirements.txt`.

```sh
pip install -r requirements.txt
# or
.venv/bin/pip install -r requirements.txt
```

### Create config.ini

At first, rename `default_config.ini` to `config.ini` and assign values to all variables. The field `instance` defines
to start `HomeTemp` (hometemp) or `BaseTemp` (basetemp).

### Optional Features

Some features are supported to be disabled or not started at all. This can be configured via the `config.ini`.
Currently this holds for the following features:

- **distribution** if no distribution is wanted then remove the entire section
- **database** if no database is wanted then remove the entire section or set enabled to false
- **visualization*** is disabled when the database is disabled
- **heat warnings** (only in [basetemp], optional) get e-mail when the temperature is below min_heat or above max_heat

### Install Chromedriver

Selenium is used to fetch data from endpoints which rely on Javascript.
On a raspberry pi, install chromium driver with the following command and set permissions:

```sh
sudo apt-get install chromium-chromedriver
sudo chmod -R 755 /usr/lib/chromium-browser
# or if not existing
sudo chmod -R 755 /usr/bin/chromedriver

```

### Firewall Configuration

Configure the firewall to allow frontend access.

```sh
sudo ufw allow 3000/tcp comment "Grafana Frontend"
sudo ufw reload
```

## Start Instructions

When everything is set up as intended, it should be enough to run `./start.sh [basetemp|hometemp]`. Once started, the frontend
should be accessible via `http://<pi-ip>:3000/`. In case it didn't work, the following sections provide information and tips 
for starting the related services and dependencies.

## Update/Restore Instructions

Use the following commands to import and export database. In this snippet, the database container name is `postgres-db`:

```sh
# Just open pqsql console (leave \q)
docker exec -it postgres-db bash -c "PGPASSWORD='<DB_PASSWORD>' psql -U <DB_USER> -d <DB_NAME>"
# Export
docker exec -t postgres-db sh -c 'PGPASSWORD=<DB_PASSWORD> pg_dump -U <DB_USER> <DB_NAME>' > backup.sql

# Import
# start container
docker cp backup.sql postgres-db:/backup.sql
docker exec -i postgres-db sh -c 'PGPASSWORD=<DB_PASSWORD> psql -U <DB_USER> -d <DB_NAME>' < backup.sql
```

