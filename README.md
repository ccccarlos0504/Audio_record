# 语音录制与识别应用

这是一个基于PySide6的桌面应用程序，具有以下功能：

1. 麦克风录音功能，带有开始/停止控制
2. 实时音频波形显示
3. 将录音保存为MP3格式
4. 语音转文字功能

## 依赖项

- Python 3.6+
- PySide6
- PyAudio
- matplotlib
- pydub
- SpeechRecognition

## 使用方法

1. 安装依赖项：
```
pip install pyside6 pyaudio matplotlib pydub SpeechRecognition
```

2. 运行应用程序：
```
python main.py
```

3. 使用界面：
   - 点击"开始录制"按钮开始录音
   - 录音时可以看到实时波形显示
   - 再次点击按钮停止录音
   - 录音将自动转换为MP3格式并保存
   - 录音内容将转换为文字并显示在文本框中

## 注意事项

- 语音识别需要连接到互联网（使用Google语音识别API）
- 首次录音可能需要允许应用访问麦克风权限
