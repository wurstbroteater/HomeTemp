# Project: HomeTemp

## 0.2.1
- Fixed: Errors not logged to file
- Introduced configuration profile file hometemp.ini 
- Switched from psycopg2 to SQLAlchemy for better pandas support
- Renamed `fixed.py` to `recover_from_logs.py`
- Minor adjustments to `recover_from_logs.py`
- added .gitignore
- added readme.md
- uploaded to github

## 0.2
- Fixed error due to incorrect timestamp format. Changed from d-m-Y H:M:S to Y-m-d H:M:S because postgres expects fromat in ISO 8601. <br />
Therefore **BREAKING CHANGE IN LOG FILE!!**<br />
Created 'fixed.py' which recovers from log file, **clears and saves to db**
- Increased accuracy of data in log
- Added new plots to email
- Minor refactorings to draw_plots and email error handling
- Added more statistics to email body

## 0.1
initial idea