import pandas
import matplotlib
import numpy
import bs4
import psycopg
import RPi.GPIO
import gpiozero
import PIL
import docker
import schedule
import seaborn
import selenium
import sqlalchemy
import requests
import cv2
import fastapi
import uvicorn
import prometheus_client
import psutil

from gpiozero import CPUTemperature
cpu = CPUTemperature()
print(f"CPU Temperature: {cpu.temperature}")

print(f"psycopg version: {psycopg.__version__}")

from RPi import GPIO
print(f"GPIO version: {GPIO.VERSION}")
print(f"Loaded from: {GPIO.__file__}")
print("All imports OK")