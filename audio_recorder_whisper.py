#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
语音录制与转写应用 - 使用pywhispercpp进行语音转文字
支持录制麦克风声音、显示波形、保存为MP3和语音转文字功能
"""

import os
import wave
import pyaudio
import threading
import numpy as np
import matplotlib
matplotlib.use('QtAgg')
from matplotlib.figure import Figure
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from pydub import AudioSegment
from PySide6.QtCore import Qt, QTimer, Signal, Slot
from PySide6.QtWidgets import (
    QMainWindow, QPushButton, QVBoxLayout, QHBoxLayout, 
    QWidget, QTextEdit, QLabel, QMessageBox, QComboBox
)
from PySide6.QtGui import QFont
import logging
import traceback
import tempfile
from whisper_manager import (
    transcribe_audio_with_whisper, download_whisper_model, 
    get_available_models
)

# 配置日志
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    filename='voice_app.log',
    filemode='w',
    encoding='utf-8'
)
console = logging.StreamHandler()
console.setLevel(logging.INFO)
formatter = logging.Formatter('%(levelname)s: %(message)s')
console.setFormatter(formatter)
logging.getLogger('').addHandler(console)
logger = logging.getLogger('voice_app')

class WaveformCanvas(FigureCanvas):
    """音频波形显示画布，使用matplotlib"""
    def __init__(self, parent=None, width=5, height=4, dpi=100):
        self.fig = Figure(figsize=(width, height), dpi=dpi)
        self.axes = self.fig.add_subplot(111)
        self.axes.set_ylim(-32768, 32768)  # 16-bit audio range
        self.axes.set_xlim(0, 100)
        self.axes.set_yticks([])
        self.axes.set_xticks([])
        self.axes.set_title('音频波形', fontproperties='SimHei')
        
        # 初始化一个空波形
        self.xdata = np.arange(100)
        self.ydata = np.zeros(100)
        self.line, = self.axes.plot(self.xdata, self.ydata, 'r-')
        
        FigureCanvas.__init__(self, self.fig)
        self.setParent(parent)

    def update_waveform(self, data):
        """更新波形显示"""
        if len(data) != len(self.ydata):
            self.ydata = data
            self.xdata = np.arange(len(data))
            self.axes.set_xlim(0, len(data))
            self.line.set_data(self.xdata, self.ydata)
        else:
            self.ydata = data
            self.line.set_ydata(data)
        
        self.draw()


class AudioRecorderApp(QMainWindow):
    """主应用窗口类"""
    transcription_ready = Signal(str)
    
    def __init__(self):
        super().__init__()
        
        # 录音参数
        self.is_recording = False
        self.audio_frames = []
        self.sample_rate = 44100
        self.chunk_size = 1024
        self.channels = 1
        self.format = pyaudio.paInt16
        
        try:
            self.p = pyaudio.PyAudio()
            self.check_audio_devices()  # 检查音频设备
        except Exception as e:
            logger.error(f"PyAudio初始化错误: {str(e)}")
            traceback.print_exc()
            
        self.stream = None
        self.recording_thread = None
        self.temp_wav_file = "temp_recording.wav"
        self.output_mp3_file = "recording.mp3"
        
        # Whisper模型参数
        self.whisper_model_size = "tiny"  # 默认使用tiny模型
        self.whisper_language = "zh"       # 默认使用中文
          # 初始化并加载模型列表
        try:
            # 刷新模型列表（将在init_ui中调用）
            logger.info("初始化模型列表")
        except Exception as e:
            logger.error(f"模型列表初始化错误: {str(e)}")
        
        # 设置UI
        self.init_ui()
        
        # 实时更新定时器
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.update_waveform)
        self.update_interval = 100  # 毫秒
          # 连接信号
        self.transcription_ready.connect(self.update_transcription)
    
    def preload_whisper_model(self):
        """预加载Whisper模型"""
        try:
            logger.info(f"预加载Whisper模型: {self.whisper_model_size}")
            
            # 更新可用模型列表
            self.available_models = get_available_models()
            
            # 如果模型已经存在，直接加载
            if self.whisper_model_size in self.available_models:
                logger.info(f"模型已存在，直接加载: {self.whisper_model_size}")
                download_whisper_model(self.whisper_model_size, force_download=False)
                logger.info("Whisper模型加载完成")
                self.status_label.setText(f"{self.whisper_model_size} 模型就绪")
            else:
                logger.warning(f"模型不存在，请先下载: {self.whisper_model_size}")
                self.status_label.setText(f"模型 {self.whisper_model_size} 未找到，请下载后使用")
        except Exception as e:
            logger.error(f"Whisper模型加载失败: {str(e)}")
            self.status_label.setText(f"语音识别模型加载失败: {str(e)}")
    
    def check_audio_devices(self):
        """检查并记录可用的音频设备"""
        logger.info("正在检查音频设备...")
        info = self.p.get_host_api_info_by_index(0)
        num_devices = info.get('deviceCount')
        input_device_found = False
        
        with open('audio_devices.log', 'w', encoding='utf-8') as f:
            f.write("可用音频设备列表:\n")
        
        for i in range(num_devices):
            device_info = self.p.get_device_info_by_host_api_device_index(0, i)
            device_name = device_info.get('name')
            input_channels = device_info.get('maxInputChannels')
            
            logger.info(f"设备 {i}: {device_name}")
            
            with open('audio_devices.log', 'a', encoding='utf-8') as f:
                f.write(f"设备 {i}: {device_name}\n")
                f.write(f"  输入通道: {input_channels}\n")
                f.write(f"  输出通道: {device_info.get('maxOutputChannels')}\n")
                f.write(f"  默认采样率: {device_info.get('defaultSampleRate')}\n")
                f.write(f"  是否默认输入: {device_info.get('isDefaultInput')}\n\n")
            
            if input_channels > 0:
                input_device_found = True
        
        if not input_device_found:
            logger.warning("没有找到可用的音频输入设备!")
    
    def init_ui(self):
        """初始化用户界面"""
        self.setWindowTitle("语音录制与识别 - pywhispercpp")
        self.setMinimumSize(600, 500)
        
        # 主布局
        main_layout = QVBoxLayout()
        
        # 标题标签
        title_label = QLabel("语音录制与转写工具")
        title_label.setFont(QFont("SimHei", 16, QFont.Bold))
        title_label.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(title_label)        # 波形显示
        self.waveform_canvas = WaveformCanvas(self, width=5, height=2)
        main_layout.addWidget(self.waveform_canvas)
        
        # 设置区域（横向布局）
        settings_layout = QHBoxLayout()        # Whisper模型选择
        model_label = QLabel("模型:")
        model_label.setFont(QFont("SimHei", 10))
        self.model_combo = QComboBox()
        
        # 刷新并加载可用模型列表
        self.refresh_model_list()
        
        # 添加刷新按钮
        self.refresh_button = QPushButton("刷新")
        self.refresh_button.setMaximumWidth(60)
        self.refresh_button.clicked.connect(self.on_refresh_models)
        
        self.model_combo.currentIndexChanged.connect(self.change_whisper_model)
        
        settings_layout.addWidget(model_label)
        settings_layout.addWidget(self.model_combo)
        settings_layout.addWidget(self.refresh_button)
        settings_layout.addStretch()
        
        main_layout.addLayout(settings_layout)

        # 录制按钮
        self.record_button = QPushButton("开始录制")
        self.record_button.setFont(QFont("SimHei", 12))
        self.record_button.setMinimumHeight(50)
        self.record_button.setFixedWidth(150)
        # 设置按钮样式：正常、悬停、按下状态
        self.record_button.setStyleSheet("""
            QPushButton {
            background-color: #e74c3c;
            color: white;
            border-radius: 8px;
            border: none;
            }
            QPushButton:hover {
            background-color: #c0392b;
            }
            QPushButton:pressed {
            background-color: #922b21;
            }
        """)
        self.record_button.clicked.connect(self.toggle_recording)
        # 录制按钮水平居中
        record_layout = QHBoxLayout()
        record_layout.addStretch()
        record_layout.addWidget(self.record_button)
        record_layout.addStretch()
        main_layout.addLayout(record_layout)
        
        # main_layout.addWidget(self.record_button)
        
        # 状态标签
        self.status_label = QLabel("就绪")
        self.status_label.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(self.status_label)
        
        # 转写结果文本框
        self.transcription_text = QTextEdit()
        self.transcription_text.setFont(QFont("SimHei", 11))
        self.transcription_text.setPlaceholderText("录音转写内容将显示在这里...")
        self.transcription_text.setMinimumHeight(150)
        main_layout.addWidget(self.transcription_text)        # 设置中心部件
        central_widget = QWidget()
        central_widget.setLayout(main_layout)
        self.setCentralWidget(central_widget)
        
    def change_whisper_model(self, index):
        """更改Whisper模型"""
        # 获取选定的模型数据
        model_size = self.model_combo.itemData(index)
        display_name = self.model_combo.itemText(index)
        
        # 检查是否有效模型被选择
        if not model_size:
            logger.warning("选择了无效的模型")
            self.status_label.setText("请下载模型后再试")
            return
        
        self.whisper_model_size = model_size
        logger.info(f"切换模型: {model_size} ({display_name})")
        self.status_label.setText(f"切换到{model_size}模型...")
        
        # 在后台线程中加载模型
        threading.Thread(target=self.preload_whisper_model).start()
    
    def refresh_model_list(self):
        """刷新模型列表，检测新添加的模型文件"""
        logger.info("刷新模型列表")
        
        # 保存当前选择的模型
        current_model = self.whisper_model_size
        
        # 获取更新后的可用模型
        self.available_models = get_available_models()
        logger.info(f"刷新后发现的模型: {list(self.available_models.keys())}")
        
        # 清空现有选项
        self.model_combo.clear()
        
        # 如果有可用模型，重新填充选项
        if self.available_models:
            # 模型描述映射表
            model_descriptions = {
                "tiny": "最小模型，推荐入门",
                "base": "基础模型",
                "small": "小型模型，平衡",
                "medium": "中型模型，较精确",
                "large": "大型模型，最精确",
                "small-q8_0": "小型量化模型，推荐",
                "small-q5_0": "小型高压缩模型",
                "small-q4_0": "小型极压缩模型",
                "medium-q8_0": "中型量化模型",
                "medium-q5_0": "中型高压缩模型"
            }
            
            # 按模型大小排序模型ID
            size_order = {"tiny": 1, "base": 2, "small": 3, "medium": 4, "large": 5}
            
            # 对模型进行排序
            def sort_key(model_id):
                # 处理不同格式的模型ID
                if model_id.startswith("tiny"):
                    base_size = "tiny"
                elif model_id.startswith("base"):
                    base_size = "base"
                elif model_id.startswith("small"):
                    base_size = "small"
                elif model_id.startswith("medium"):
                    base_size = "medium"
                elif model_id.startswith("large"):
                    base_size = "large"
                else:
                    base_size = "unknown"
                
                # 获取模型大小的顺序值
                size_value = size_order.get(base_size, 99)
                
                # 量化模型在后面
                is_quantized = "-q" in model_id
                
                return (size_value, is_quantized, model_id)
            
            sorted_models = sorted(self.available_models.keys(), key=sort_key)
            
            # 添加排序后的模型到下拉框
            for model_id in sorted_models:
                # 获取模型描述，如果没有预定义描述则使用默认描述
                description = model_descriptions.get(model_id, "")
                if description:
                    display_name = f"{model_id} ({description})"
                else:
                    # 对未知模型生成描述
                    if ".en" in model_id:
                        display_name = f"{model_id} (仅英文)"
                    elif "-q" in model_id:
                        display_name = f"{model_id} (量化模型)"
                    else:
                        display_name = model_id
                
                self.model_combo.addItem(display_name, model_id)
            
            # 尝试恢复之前选择的模型
            found = False
            if current_model in self.available_models:
                for i in range(self.model_combo.count()):
                    if self.model_combo.itemData(i) == current_model:
                        self.model_combo.setCurrentIndex(i)
                        found = True
                        break
            
            # 如果之前的模型不在列表中，选择第一个可用的模型
            if not found and self.model_combo.count() > 0:
                self.whisper_model_size = self.model_combo.itemData(0)
                self.model_combo.setCurrentIndex(0)
                logger.info(f"切换到可用的模型: {self.whisper_model_size}")
        else:
            # 如果没有模型，添加提示
            self.model_combo.addItem("未找到模型，请下载", "")
            logger.warning("未找到任何模型！")
        
        return self.available_models

    def toggle_recording(self):
        """开始或停止录音"""
        try:
            if self.is_recording:
                logger.info("停止录音...")
                self.stop_recording()
            else:
                logger.info("开始录音...")
                self.start_recording()
        except Exception as e:
            logger.error(f"录音操作错误: {str(e)}")
            logger.error(traceback.format_exc())
            self.status_label.setText(f"录音错误: {str(e)}")
    
    def start_recording(self):
        """开始录音"""
        self.record_button.setText("停止录制")
        self.status_label.setText("正在录制...")
        self.is_recording = True
        self.audio_frames = []
        
        # 启动录音线程
        self.recording_thread = threading.Thread(target=self.record_audio)
        self.recording_thread.daemon = True
        self.recording_thread.start()
        
        # 开始更新波形定时器
        self.update_timer.start(self.update_interval)
    
    def stop_recording(self):
        """停止录音"""
        if self.is_recording:
            self.is_recording = False
            self.record_button.setText("开始录制")
            self.status_label.setText("处理录音...")
            
            # 停止定时器
            self.update_timer.stop()
            
            # 等待录音线程结束
            if self.recording_thread and self.recording_thread.is_alive():
                self.recording_thread.join()
                
            # 保存并处理录音
            self.save_audio()
            
            # 转换为文字
            threading.Thread(target=self.transcribe_audio).start()
    
    def record_audio(self):
        """录制音频数据"""
        try:
            logger.info("初始化音频流...")
            # 检查设备是否可用
            input_device = None
            
            try:
                device_count = self.p.get_device_count()
                logger.debug(f"找到 {device_count} 个音频设备")
                
                for i in range(device_count):
                    try:
                        device_info = self.p.get_device_info_by_index(i)
                        if device_info.get('maxInputChannels') > 0:
                            input_device = i
                            logger.info(f"选择设备 {i} 作为输入设备")
                            break
                    except Exception as device_err:
                        logger.error(f"检查设备 {i} 时出错: {str(device_err)}")
            except Exception as count_err:
                logger.error(f"获取设备数量时出错: {str(count_err)}")
            
            if input_device is None:
                logger.error("没有找到可用的音频输入设备")
                self.status_label.setText("错误: 没有找到可用的麦克风设备")
                return
                
            try:
                self.stream = self.p.open(
                    format=self.format,
                    channels=self.channels,
                    rate=self.sample_rate,
                    frames_per_buffer=self.chunk_size,
                    input=True,
                    input_device_index=input_device
                )
                logger.info("音频流已打开")
                
                try:
                    while self.is_recording:
                        # 使用异常处理包装每次读取
                        try:
                            data = self.stream.read(self.chunk_size, exception_on_overflow=False)
                            self.audio_frames.append(data)
                        except Exception as read_error:
                            logger.error(f"读取音频数据错误: {str(read_error)}")
                except Exception as loop_err:
                    logger.error(f"录音循环错误: {str(loop_err)}")
                    logger.error(traceback.format_exc())
                finally:
                    if self.stream:
                        logger.info("关闭音频流...")
                        try:
                            self.stream.stop_stream()
                            self.stream.close()
                            logger.info("音频流已关闭")
                        except Exception as close_err:
                            logger.error(f"关闭音频流错误: {str(close_err)}")
                        finally:
                            self.stream = None
            except Exception as stream_err:
                logger.error(f"打开音频流时出错: {str(stream_err)}")
                logger.error(traceback.format_exc())
                self.status_label.setText(f"初始化录音失败: {str(stream_err)}")
        except Exception as e:
            logger.error(f"录音总体错误: {str(e)}")
            logger.error(traceback.format_exc())
            self.status_label.setText(f"录音错误: {str(e)}")
    
    def update_waveform(self):
        """更新音频波形显示"""
        if self.is_recording and self.audio_frames:
            try:
                # 获取最近的音频数据用于波形显示
                recent_frame = self.audio_frames[-1]
                data = np.frombuffer(recent_frame, dtype=np.int16)
                self.waveform_canvas.update_waveform(data)
            except Exception as e:
                logger.error(f"更新波形错误: {str(e)}")
    
    def save_audio(self):
        """保存录音为WAV和MP3文件"""
        if not self.audio_frames:
            logger.warning("没有音频帧可保存")
            self.status_label.setText("未录制到音频")
            return
        
        try:
            # 保存为WAV文件
            logger.info(f"保存录音为WAV文件: {self.temp_wav_file}")
            with wave.open(self.temp_wav_file, 'wb') as wf:
                wf.setnchannels(self.channels)
                wf.setsampwidth(self.p.get_sample_size(self.format))
                wf.setframerate(self.sample_rate)
                wf.writeframes(b''.join(self.audio_frames))
            
            # 转换为MP3文件
            logger.info(f"转换录音为MP3文件: {self.output_mp3_file}")
            audio = AudioSegment.from_wav(self.temp_wav_file)
            audio.export(self.output_mp3_file, format="mp3")
            logger.info("录音保存和转换完成")
            self.status_label.setText("录音保存完成")
        except Exception as e:
            logger.error(f"保存音频文件错误: {str(e)}")
            self.status_label.setText(f"保存音频文件错误: {str(e)}")
    
    def transcribe_audio(self):
        """转写音频为文字"""
        try:
            logger.info(f"使用模型 {self.whisper_model_size} 转写音频")
            self.status_label.setText("转写中，请稍候...")
            
            # 首先确保WAV文件存在
            if not os.path.exists(self.temp_wav_file):
                error_msg = "找不到录制的WAV文件"
                logger.error(error_msg)
                self.transcription_ready.emit(f"转写错误: {error_msg}")
                return
            
            # 将WAV转换为16000 Hz采样率 (Whisper模型要求)
            try:
                optimized_wav = "whisper_input.wav"
                logger.info(f"转换WAV文件采样率为16000 Hz: {optimized_wav}")
                
                # 使用pydub转换音频格式
                sound = AudioSegment.from_file(self.temp_wav_file)
                sound = sound.set_frame_rate(16000)  # Whisper要求16kHz采样率
                sound = sound.set_channels(1)        # 单声道
                sound = sound.set_sample_width(2)    # 16位
                sound.export(optimized_wav, format="wav")
                logger.info(f"已优化音频: {optimized_wav}")
                
                # 转写音频
                logger.info(f"使用优化后的音频进行转写")
                text = transcribe_audio_with_whisper(
                    optimized_wav, 
                    model_size=self.whisper_model_size,
                    language=self.whisper_language
                )
                
                # 获取转写文本
                if text:
                    logger.info(f"转写结果: {text}")
                    self.transcription_ready.emit(text)
                else:
                    logger.warning("转写结果为空")
                    self.transcription_ready.emit("未能识别出语音内容")
                
                # 删除临时文件
                if os.path.exists(optimized_wav):
                    os.remove(optimized_wav)
                    logger.info(f"已删除临时文件: {optimized_wav}")
            except Exception as e:
                logger.error(f"音频格式转换或转写过程出错: {str(e)}")
                logger.error(traceback.format_exc())
                self.transcription_ready.emit(f"转写错误: {str(e)}")
        except Exception as e:
            logger.error(f"转写音频错误: {str(e)}")
            logger.error(traceback.format_exc())
            self.transcription_ready.emit(f"转写错误: {str(e)}")
    
    @Slot(str)
    def update_transcription(self, text):
        """更新转写结果到文本框"""
        self.transcription_text.setText(text)
        if "错误" in text or "失败" in text:
            self.status_label.setText("转写失败")
        else:
            self.status_label.setText("转写完成")
    
    def closeEvent(self, event):
        """关闭窗口时的清理工作"""
        # 清理资源
        if self.is_recording:
            self.stop_recording()
        if self.p:
            self.p.terminate()
        
        # 删除临时文件
        for temp_file in [self.temp_wav_file, self.output_mp3_file]:
            if os.path.exists(temp_file):
                try:
                    os.remove(temp_file)
                    logger.info(f"已删除文件: {temp_file}")
                except:
                    pass
        
        super().closeEvent(event)
    
    def on_refresh_models(self):
        """刷新模型列表按钮的事件处理"""
        logger.info("手动刷新模型列表")
        self.status_label.setText("正在刷新模型列表...")
        
        # 刷新模型列表
        available_models = self.refresh_model_list()
        
        if available_models:
            self.status_label.setText(f"发现 {len(available_models)} 个模型")
        else:
            self.status_label.setText("未找到模型文件，请下载或放入models文件夹")
        
        # 在后台预加载当前选择的模型
        if self.model_combo.currentData():
            threading.Thread(target=self.preload_whisper_model).start()
