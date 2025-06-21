# 语音录制与转写工具

一款简单易用的桌面应用程序，用于录制音频并实时转写为文字。基于PySide6和Whisper语音识别技术构建。

## 功能特性

- 📝 录制麦克风声音并保存为MP3格式
- 📊 实时显示录音波形图
- 🔊 将录音自动转写为文字
- 🌐 支持离线使用，无需互联网连接
- 📚 支持多种Whisper模型，适应不同场景需求
- 🔄 支持自定义模型，用户可自行添加新模型

## 安装与使用

### 方法一：直接使用可执行文件（推荐）

1. 下载最新的发行版本
2. 解压缩文件夹
3. 运行`语音录制与转写工具.exe`

首次运行时，如果没有检测到模型文件，程序会提示您下载最小的模型文件(tiny)。

### 方法二：从源代码运行

1. 克隆项目仓库
   ```bash
   git clone https://github.com/您的用户名/项目名称.git
   cd 项目名称
   ```

2. 安装依赖
   ```bash
   pip install -r requirements.txt
   ```

3. 下载Whisper模型（至少一个）
   ```bash
   python download_model.py
   ```

4. 运行程序
   ```bash
   python main.py
   ```

## 使用说明

1. 点击"开始录制"按钮开始录音
2. 录音过程中可观察实时波形图
3. 再次点击按钮停止录音
4. 程序会自动保存录音为MP3文件并转写为文字
5. 转写结果会显示在界面下方的文本框中

## 模型说明

程序使用Whisper.cpp作为语音识别引擎，支持以下模型：

| 模型名称 | 文件大小 | 内存需求 | 速度 | 准确度 |
|---------|---------|--------|------|-------|
| tiny    | ~75MB   | 低     | 最快  | 一般   |
| base    | ~142MB  | 中低   | 快    | 较好   |
| small   | ~465MB  | 中     | 中    | 好     |
| medium  | ~1.5GB  | 高     | 慢    | 很好   |
| large   | ~3GB    | 很高   | 很慢  | 最好   |

程序支持量化模型(如`ggml-small-q8_0.bin`)，这些模型体积更小、速度更快，同时保持不错的准确率。

### 添加自定义模型

1. 将下载的模型文件(*.bin)放入程序目录下的models文件夹中
2. 在程序中点击"刷新"按钮
3. 在下拉菜单中选择新添加的模型

## 技术细节

- 使用PySide6构建图形用户界面
- 使用PyAudio录制音频流
- 使用pywhispercpp调用Whisper.cpp进行语音识别
- 使用Matplotlib绘制实时音频波形

## 系统要求

- Windows 10/11 64位
- 至少4GB RAM (使用large模型时建议8GB以上)
- 100MB可用磁盘空间 (不含模型文件)

## 常见问题

**Q: 程序无法启动？**  
A: 请确保您的系统满足最低配置要求，并且已安装必要的Visual C++ Redistributable运行库。

**Q: 语音识别准确率不高？**  
A: 尝试使用更大的模型(如small或medium)，并确保录音环境尽量安静。

**Q: 程序运行很慢？**  
A: 尝试使用更小或量化的模型(如tiny或small-q8_0)。

**Q: 如何获取更多模型？**  
A: 您可以从[Hugging Face](https://huggingface.co/ggerganov/whisper.cpp)下载更多预训练模型。

## 许可证

本项目基于MIT许可证开源。

## 致谢

- [OpenAI Whisper](https://github.com/openai/whisper) - 原始语音识别模型
- [Whisper.cpp](https://github.com/ggerganov/whisper.cpp) - Whisper的C++实现
- [pywhispercpp](https://github.com/abdeladim-s/pywhispercpp) - Whisper.cpp的Python绑定
- [PySide6](https://wiki.qt.io/Qt_for_Python) - Python的Qt绑定