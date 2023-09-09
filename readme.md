# Project: HomeTemp
The original idea of this project was to automate the periodically measured temperature and humidity values in my apartment. 
This idea is still growing prosperously.

## Current Features
- Connection to postgres db
- CRUD operations for tables and columns
- Create data visualizations using seaborn and matplot
- Ability to send emails with text and attached pdf file
- Recover sensor data from log file and save to database 


While `humidity.py` is the entrypoint to start periodical data collection and distribution, `crunch_numbers.ipynb` is a playground for everything.

## Start Instructions
The following sections provide information and tips for starting the related services and dependencies.

### Start pigpio Deamon
For retrieving the temperatue values, we (indirectly) use `gpiozero` to communicate with GPIO pins (e.g., on the raspberry pi).
This packages displays warnings when its used for the first time after start. To decrease the warning messages, we can start the deamon with:
`sudo pigpiod` 
However, this does not remove all warning messages, it just decreases their amount and in terms of accuricy or reliability of data retrieval, 
we didn't observ any issues. 

### Start Docker Container
```
docker run --name postgres-container -e POSTGRES_PASSWORD=<ENTER PASSWORD HERE> -d -p 5432:5432 postgres:latest
```
after a restart,  use `docker ps -a` to get the container ID and then `docker start <containerID>` to start the old database
