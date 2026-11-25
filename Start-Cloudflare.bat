@echo off
cd /d "%~dp0"
echo Start AMBU first using Start-AMBU.bat.
echo Keep this window open while sharing the public link.
cloudflared.exe tunnel --url http://127.0.0.1:8877 --no-autoupdate
pause
