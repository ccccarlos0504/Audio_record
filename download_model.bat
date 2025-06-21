@echo off
echo 欢迎使用Whisper模型下载工具
echo =========================
echo.

CD /D "%~dp0"
@REM 使用虚拟环境中的Python解释器
.\.venv\Scripts\python.exe download_model.py

echo.
if %ERRORLEVEL% NEQ 0 (
  echo 程序执行失败，错误代码: %ERRORLEVEL%
  pause
) else (
  echo 操作完成，请关闭此窗口或按任意键继续...
  pause
)
