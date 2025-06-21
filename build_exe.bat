@echo off
echo 开始打包语音录制与转写工具...
echo =======================================
echo.

CD /D "%~dp0"

echo 检查文件夹结构...
if not exist "models" (
    echo 警告: models文件夹不存在，将创建空models文件夹
    mkdir models
)

echo 开始使用PyInstaller打包...
.\.venv\Scripts\pyinstaller --clean voice_app.spec

echo.
if %ERRORLEVEL% NEQ 0 (
    echo 打包过程出错，错误代码: %ERRORLEVEL%
) else (
    echo 打包完成！
    echo 打包后的文件位于 dist\语音录制与转写工具 文件夹中
)
echo.
echo 你可以将以下内容复制到U盘或其他位置:
echo - dist\语音录制与转写工具 文件夹 (包含可执行文件和所有依赖)
echo - models 文件夹 (包含模型文件)
echo.
echo 如需添加新的模型，请将模型文件放入models文件夹中
echo.
pause
