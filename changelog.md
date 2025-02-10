# Project: HomeTemp

## 0.5

This release overhauls the start process by introducing `start.sh` and renaming the config file to `config.ini`. Files,
e.g., plots and pictures are stored like previously but the root folder is defined in `data_path` (config.ini), now. The
reworked plotting module is now **\~90\%** faster and supports merged and distinct visualizations.

- Added `./start.sh [hometemp|basetemp]` to start all components for an instance.
- Moved log file creation to `start.sh`.
- **BREAKING CHANGE**: Removed `basetemp.py` and `hometemp.py`:
    - Now, the instance to run depends on parameter `core.instance` in configuration file.
    - Added module `core.instance` which includes class `HomeTemp` and `BaseTemp`.
    - Now, just use `python start.py`!
- **BREAKING CHANGE**: Removed `fetch_forecasts.py`:
    - Moved its core functionality to `endpoint.usage_util`.
    - Added module `endpoint.instance` which includes class `FetchTemp`.
    - Now, just use `python start.py --instance FetchTemp`!
- Optimized `RpiCamController._rotate_image` to update an image only if the rotation parameter is not zero.
- Added timelapse video creation of a set of pictures with the name format '%Y-%m-%d-%H:%M:%S'.
- Updated `requirements.txt` to only contain top level dependencies.
- Updated `GoogleFetcher` to new javascript-enabled browser fetcher (uses Selenium now).
- **BREAKING CHANGE**: Removed `draw_plots` from plotting and replaced it with `draw_complete_summary`.
- Refactored `core.plotting` to be more flexible and extendable:
    - Added `SupportedDataFrames` for defining how to enrich known dataframes with plotting information.
    - Added `PlotData` to combine dataframe with `SupportedDataFrames`.
    - Added `PlotDataSelector` to specify which data has to be selected from a `PlotData` instances.
    - Added `DefaultPlotCategory.DISTINCT` for multi-lineplots. Use with an `PlotDataSelector.*ALL`.
    - Added `DefaultPlotCategory.DISTINCT24` for 24h-multi-lineplots. Use with an `PlotDataSelector.*24`.
    - Added `DefaultPlotCategory.MERGED` for lineplots with merged subplots. Currently, only supports temperature!
    - Added `DefaultPlotCategory.MERGED24` for 24h-lineplots with merged subplots. Currently, only supports temperature!
    - Added `DefaultPlotCategory` for combining `DefaultPlotCategory` with the main plot parameter configuration.
- Added new functionality to `core.database.PostgresHandler`:
    - Added `close()` to close the current database connection. If the handler instance is reused, the
      `init_db_connection` has to be called before doing something with the instance!
    - Added `is_db_ready()` which returns true if the database is currently ready to accept transactions else false. By
      default, it initializes the database before checking for ready.
- Added `core.usage_util` providing utilities for several core functionalities.
- **BREAKING CHANGE**: Removed `core.sensors.util` and moved method to `core.usage_util.get_cput_temperature()`.
- **BREAKING CHANGE**: Refactored and renamed `default_hometemp.ini` to `default_configuration.ini`.
- Added decorator `require_web_access` for checking if internet connection is available or skips the annotated method.
- Added `FileManager` to handle file reading/writing and file path management.
    - Added `data_path` in `config.ini` which defaults to `./data`.
- BaseTemp: Added `phase` command to switch between scheduler plans. Currently supported: `common`, `phase1`, `phase2`.
- Improved command handling in `core.command`.
- Fixed incorrect temperature for DHT 11 when below zero.
- Improved timestamp handling across modules. Now, all data stored in database uses `core.database.TIME_FORMAT`.

## 0.4

This version adds the ability to create, receive and execute commands from external, introduces new instance `BaseTemp`
and refactors the current module structure. Therefore, this release contains **BREAKING CHANGES**!

- Refactored old modules `distribute`, `persist`, `util` and `visualize` into `core` modules
- Moved `get_sensor_data`, `init_postgres_container` and `get_cpu_temperature` into related core modules
- Renamed module `api` to `endpoint`
- Added `BaseTemp`
- Divided `crunch_numbers.ipynb` into one for HomeTemp and one for BaseTemp
- Added wrapper `RpiCamController` for `rpicam-apps` command to be able to take pictures with raspberry pi camera module
- Added `camera_test.py` for testing `RpiCamController`
- Updated `EmailDistributor` to support CRUD for emails
- Added `Command`, `CommandRequest`, `CommandParser` and `CommandService` to enable commanding
- Added `command_test.py` as (test) demo for commanding
- Restructured and added new fields in `default_hometemp.ini`
- Restructured and updated dependencies
- Replaced deprecated dependency `Adafruit-DHT` with new module `core.sensors.dht`
- Updated logging and introduced new module `core.core_log`
- Introduced new module `core.core_configuration` for handling config file parsing and publishing
- Updated readme.md

## 0.3.3

- Added URI-save whitespace in `GoogleFetcher`
- Updated `readme.md`

## 0.3.2

- Replaced throwing exceptions in `get_sensor_data` and use logging instead
- Fixed incorrect error printing in base fetcher
- Increased error robustness of `api` module

## 0.3.1

- Added data fetcher, database handler and visualization for **Ulm.de**
- Fixed deadlocks causing whole Pi to be unresponsive (database recovery mode was triggered by to many pending
  connections)

## 0.3

- Refactored code to modules `api`, `distribute`, `persist` and `visualize`
- Updated `recover_from_logs.py`, `crunch_numbers.ipynb` and `humidity.py` to use new modules
- Added data fetcher and database handler for **wetter.com**, **Deutsche Wetterdienst (DWD)** and **Google Weather**
- Added `fetch_forecasts.py` for pulling data from various endpoints
- Added `default_hometemp.ini` for better overview of used local variables
- Decreased the time delay in "every 10 minutes" jobs by using the method `run_threaded`
- Added "tests" but only for toying around or minial usage examples
- Introduced module `util` and added `DockerManager` and `PostgresDockerManager`
- Renamed `humidity.py` to `hometemp.py`
- Introduced version number
- Updated `hometemp.ini`

## 0.2.1

- Fixed: Errors not logged to file
- Introduced configuration profile file hometemp.ini
- Switched from psycopg2 to SQLAlchemy for better pandas support
- Renamed `fixed.py` to `recover_from_logs.py`
- Minor adjustments to `recover_from_logs.py`
- Added .gitignore
- Added readme.md
- Uploaded to GitHub

## 0.2

- Fixed error due to incorrect timestamp format. Changed from d-m-Y H:M:S to Y-m-d H:M:S because postgres expects format
  in ISO 8601. <br />
  Therefore **BREAKING CHANGE IN LOG FILE!!**<br />
  Created 'fixed.py' which recovers from log file, **clears and saves to db**
- Increased accuracy of data in log
- Added new plots to email
- Minor refactorings to draw_plots and email error handling
- Added more statistics to email body

## 0.1

Initial idea: Write script for periodically collecting room temperature and humidity and visualize the data.
In the end, this data should be retrievable from everywhere (not just in local network), i.e. in an app or website.
