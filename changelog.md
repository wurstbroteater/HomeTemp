# Project: HomeTemp

## 0.3

- Refactored code to modules `api`, `persist` and `visualize`
- Updated `recover_from_logs.py`, `crunch_numbers.ipynb` and `humidity.py` to use new modules
- Added data fetcher and database handler for **Deutsche Wetterdienst (DWD)** and **Google Weather**
- Added `fetch_forecasts.py` for pulling data from various endpoints
- Added `default_hometemp.ini` for better overview of used local variables
- Decreased the time delay in "every 10 minutes" jobs by using the method `run_threaded`
- Added "tests" but only for toying around or minial usage examples
- renamed `humidity.py` to `hometemp.py`
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

initial idea