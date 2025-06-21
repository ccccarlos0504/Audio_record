@echo off
echo 启动语音录制与转写应用...
CD /D "%~dp0"
@REM 使用虚拟环境中的Python解释器
.\.venv\Scripts\python.exe main.py
if %ERRORLEVEL% NEQ 0 (
  echo 程序执行失败，错误代码: %ERRORLEVEL%
  pause
)
