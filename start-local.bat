@echo off
echo Pokrecem lokalni server...
echo.
echo Otvori u browseru: http://localhost:8000
echo Za zaustavljanje pritisni Ctrl+C
echo.
python -m http.server 8000
pause