# Project: HomeTemp v0.3-DEV

The original idea of this project was to automate the periodically measured temperature and humidity values in my
apartment.
This idea is still growing prosperously.

## Current Features

- Connection to postgres db
- Initialize docker container for postgres db or reuse existing
- CRUD operations for tables and columns
- Create data visualizations using seaborn and matplot
- Ability to send emails with text and attached pdf file
- Recover sensor data from log file and save to database
- Ability to fetch data from API endpoints (currently: Deutsche Wetterdiens and Google Weather)

While `hometemp.py` is the entrypoint to start periodical data collection and distribution, `crunch_numbers.ipynb` is a
playground for everything.

## Installation Instructions
The following steps needs to be performed once to assure correct driver setup.

### Install Chromedriver
Selenium is used to fetch data from endpoints which rely on javascript.
On a raspberry pi, installl chromium driver with the following command and set permissions:

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
