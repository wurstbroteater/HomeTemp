# Project: HomeTemp v0.4-DEV

The original idea of this project was to automate the periodically measured temperature and humidity values in my
apartment. The room temperature and humidity is caputred by an AM2302 sensor, connected to a Raspberry Pi 4 Model B.
This idea is still growing prosperously and currently provides the following features:

## Requirements

- Everyhing in `requirements.txt` for pip
- Docker
- pigpiod

## Current Features

- Initializing docker container for postgres database or reuse existing
- Connecting to postgres database
- CRUD operations for tables and columns
- Creating data visualizations using seaborn and matplot
- Sending emails containing statistic data as text and visualizations as pdf
- Recovering sensor data from log file
- Data fetching from various API endpoints/websites (currently: Deutsche Wetterdienst (DWD) and Google Weather, Ulm.de and Wetter.com)
- Commanding via email

While `hometemp.py` is the entrypoint to start periodical data collection and distribution, `crunch_numbers.ipynb` is a
playground for everything.

## Installation Instructions

The following steps needs to be performed once to assure correct driver setup.

### Configure Hometemp.ini

At first, rename `default_hometemp.ini` to `hometemp.ini` and assign values to all variables.

### Install Chromedriver

Selenium is used to fetch data from endpoints which rely on Javascript.
On a raspberry pi, install chromium driver with the following command and set permissions:

```
sudo apt-get install chromium-chromedriver
sudo chmod -R 755 /usr/lib/chromium-browser 
```

## Start Instructions

The following sections provide information and tips for starting the related services and dependencies.

### Start pigpio Deamon

For retrieving the temperatue values, we (indirectly) use `gpiozero` to communicate with GPIO pins (e.g., on the
raspberry pi).
This packages displays warnings when its used for the first time after start. To decrease the warning messages, we can
start the deamon with:
`sudo pigpiod`
However, this does not remove all warning messages, it just decreases their amount and in terms of accuricy or
reliability of data retrieval,
we didn't observ any issues.

### Start Docker Container

Images and containers should be pulled or created/reused automatically. However, for this to work, the user needs to be
added to the docker group:

```
sudo usermod -aG docker $USER
```

Afterwards, a reboot is required otherwise the following error will occur:

```
docker.errors.DockerException: Error while fetching server API version: ('Connection aborted.', PermissionError(13, 'Permission denied'))
```

This step should be obsolete because the HomeTemp automatically does this. However, it is left for documentation.

```
docker run --name postgres-db -e POSTGRES_PASSWORD=<ENTER PASSWORD HERE> -d -p 5432:5432 postgres:latest
```

after a restart, use `docker ps -a` to get the container ID and then `docker start <containerID>` to start the old
database.
