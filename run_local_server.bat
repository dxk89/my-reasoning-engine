@echo off
echo =======================================================
echo  STARTING THE AI JOURNALIST SERVER (Version 1.4)
echo =======================================================
echo.
echo  This will start the main server.
echo  Once it says 'Application startup complete', open your
echo  web browser and go to: http://127.0.0.1:8000
echo.
echo  Press CTRL+C in this window to stop the server.
echo.
echo =======================================================
echo.
:: This command starts the FastAPI server from within the 'my_framework' directory
cd my_framework
uvicorn app.server:app --reload

echo.
echo Server stopped.
echo.
pause