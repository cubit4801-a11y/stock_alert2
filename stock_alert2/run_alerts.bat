cd C:\Users\PC\Desktop\stock_alert2
C:\Users\PC\AppData\Local\Programs\Python\Python314\python.exe manage.py check_alerts
@echo off
echo Starting NEPSE Alert Checker...
:loop
cd /d C:\Users\PC\Desktop\stock_alert2
C:\Users\PC\AppData\Local\Programs\Python\Python314\python.exe manage.py check_alerts
echo Waiting 5 minutes...
timeout /t 300 /nobreak
goto loop