@echo off
echo Installing required libraries if missing (pystray, Pillow, pynput)...
pip install pyinstaller pystray Pillow pynput

echo.
echo Building Jiggle with system tray support...
echo Note: This expects 'icon.ico' to exist in this folder.

REM --noconsole: Hides the black command window
REM --onefile: Bundles everything into a single .exe
REM --icon: Sets the file icon
REM --add-data: Adds the icon file inside the EXE
REM --collect-all: Explicitly collects hidden dependencies for pystray and its friends.

pyinstaller --noconsole --onefile --icon=icon.ico ^
--add-data "icon.ico;." ^
--collect-all "pystray" ^
--collect-all "Pillow" ^
--collect-all "pynput" ^
--name="Jiggle" jiggle_app.py

echo.
echo Build Complete!
echo You can find your new executable in the "dist" folder.
pause