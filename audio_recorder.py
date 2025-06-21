#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
语音录制与转写应用
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
import speech_recognition as sr
from pydub import AudioSegment
from PySide6.QtCore import Qt, QTimer, Signal, Slot
from PySide6.QtWidgets import (
    QMainWindow, QPushButton, QVBoxLayout, QHBoxLayout, 
    QWidget, QTextEdit, QLabel, QMessageBox
)
from PySide6.QtGui import QFont
import logging
import traceback

# 配置日志
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    filename='voice_app.log',
    filemode='w'
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
        
        # 设置UI
        self.init_ui()
        
        # 实时更新定时器
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.update_waveform)
        self.update_interval = 100  # 毫秒
        
        # 连接信号
        self.transcription_ready.connect(self.update_transcription)
    
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
        self.setWindowTitle("语音录制与识别")
        self.setMinimumSize(600, 500)
        
        # 主布局
        main_layout = QVBoxLayout()
        
        # 标题标签
        title_label = QLabel("语音录制与转写工具")
        title_label.setFont(QFont("SimHei", 16, QFont.Bold))
        title_label.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(title_label)
        
        # 波形显示
        self.waveform_canvas = WaveformCanvas(self, width=5, height=2)
        main_layout.addWidget(self.waveform_canvas)
        
        # 录制按钮
        self.record_button = QPushButton("开始录制")
        self.record_button.setFont(QFont("SimHei", 12))
        self.record_button.setMinimumHeight(50)
        self.record_button.clicked.connect(self.toggle_recording)
        main_layout.addWidget(self.record_button)
        
        # 状态标签
        self.status_label = QLabel("就绪")
        self.status_label.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(self.status_label)
        
        # 转写结果文本框
        self.transcription_text = QTextEdit()
        self.transcription_text.setFont(QFont("SimHei", 11))
        self.transcription_text.setPlaceholderText("录音转写内容将显示在这里...")
        self.transcription_text.setMinimumHeight(150)
        main_layout.addWidget(self.transcription_text)
        
        # 设置中心部件
        central_widget = QWidget()
        central_widget.setLayout(main_layout)
        self.setCentralWidget(central_widget)
    
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
        
        # 保存为WAV文件
        try:
            logger.info(f"保存WAV文件: {self.temp_wav_file}")
            wf = wave.open(self.temp_wav_file, 'wb')
            wf.setnchannels(self.channels)
            wf.setsampwidth(self.p.get_sample_size(self.format))
            wf.setframerate(self.sample_rate)
            wf.writeframes(b''.join(self.audio_frames))
            wf.close()
            logger.info("WAV文件已保存")
            
            # 转换为MP3
            logger.info(f"转换为MP3: {self.output_mp3_file}")
            audio = AudioSegment.from_wav(self.temp_wav_file)
            audio.export(self.output_mp3_file, format="mp3")
            logger.info("MP3文件已保存")
            
            # 注意：不要删除WAV文件，语音识别需要用到它
            
            self.status_label.setText(f"录音已保存为: {self.output_mp3_file}")
        except Exception as e:
            logger.error(f"保存录音失败: {str(e)}")
            logger.error(traceback.format_exc())
            self.status_label.setText(f"保存录音失败: {str(e)}")
    
    def transcribe_audio(self):
        """将音频转换为文字"""
        self.status_label.setText("正在将语音转换为文字...")
        logger.info("开始语音转文字...")
        
        try:
            # SpeechRecognition库只支持WAV、AIFF和FLAC格式
            # 确保WAV文件存在
            if not os.path.exists(self.temp_wav_file):
                logger.error("找不到WAV文件用于转写")
                self.transcription_ready.emit("错误: 找不到WAV格式录音文件")
                return
                
            logger.info(f"使用文件进行转写: {self.temp_wav_file}")
            
            # 初始化识别器
            recognizer = sr.Recognizer()
            
            try:
                # 打开音频文件
                logger.info("打开音频文件")
                with sr.AudioFile(self.temp_wav_file) as source:
                    logger.info("读取音频数据")
                    audio_data = recognizer.record(source)
                    
                    logger.info("开始Google语音识别")
                    text = recognizer.recognize_google(
                        audio_data, 
                        language='zh-CN'
                    )
                    
                    logger.info("语音识别成功")
                    self.transcription_ready.emit(text)
            except ValueError as ve:
                logger.error(f"音频文件格式错误: {str(ve)}")
                
                # 尝试重新转换WAV格式
                logger.info("尝试重新转换音频格式...")
                try:
                    converted_wav = "converted_recording.wav"
                    logger.info(f"转换到新WAV文件: {converted_wav}")
                    
                    # 使用pydub重新转换
                    sound = AudioSegment.from_file(self.temp_wav_file)
                    sound = sound.set_frame_rate(16000)  # 设置标准采样率
                    sound = sound.set_channels(1)  # 单声道
                    sound = sound.set_sample_width(2)  # 16位
                    
                    # 保存为新的WAV文件
                    sound.export(converted_wav, format="wav")
                    logger.info("文件转换完成")
                    
                    # 使用转换后的文件进行识别
                    logger.info("使用转换后的文件进行识别")
                    with sr.AudioFile(converted_wav) as source:
                        audio_data = recognizer.record(source)
                        text = recognizer.recognize_google(audio_data, language='zh-CN')
                        logger.info("识别成功")
                        self.transcription_ready.emit(text)
                        
                    # 清理转换后的临时文件
                    if os.path.exists(converted_wav):
                        os.remove(converted_wav)
                        logger.info(f"已删除临时转换文件: {converted_wav}")
                except Exception as conv_err:
                    logger.error(f"音频格式转换失败: {str(conv_err)}")
                    logger.error(traceback.format_exc())
                    self.transcription_ready.emit(f"语音转文字失败: 音频格式转换错误")
        except sr.UnknownValueError:
            logger.warning("Google语音识别无法理解音频")
            self.transcription_ready.emit("无法识别语音内容，请重新录制")
        except sr.RequestError as e:
            logger.error(f"Google语音识别服务请求失败: {str(e)}")
            self.transcription_ready.emit(f"语音识别服务错误: {e}")
        except Exception as e:
            logger.error(f"转写过程中出现错误: {str(e)}")
            logger.error(traceback.format_exc())
            self.transcription_ready.emit(f"转写过程中出现错误: {str(e)}")
        finally:
            # 转写完成后删除临时WAV文件
            try:
                if os.path.exists(self.temp_wav_file):
                    os.remove(self.temp_wav_file)
                    logger.info(f"已删除临时WAV文件: {self.temp_wav_file}")
            except Exception as del_err:
                logger.warning(f"无法删除临时WAV文件: {str(del_err)}")
    
    @Slot(str)
    def update_transcription(self, text):
        """更新界面上的转写结果"""
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
