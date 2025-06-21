#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import os
import traceback
import logging
import threading
from PySide6.QtWidgets import QApplication, QMainWindow, QMessageBox, QSplashScreen
from PySide6.QtGui import QPixmap
from PySide6.QtCore import Qt

# 尝试导入模型加载模块
try:
    from model_loader import ensure_model_exists
except ImportError:
    pass  # 如果没有找到，就跳过

# 尝试导入应用主类
try:
    from audio_recorder_whisper import AudioRecorderApp
except ImportError:
    from audio_recorder import AudioRecorderApp


if __name__ == "__main__":
    try:
        print("启动语音录制与转写应用...")
        
        # 初始化应用
        app = QApplication(sys.argv)
        
        # 显示启动画面
        splash_pixmap = None
        if os.path.exists('icons/microphone.png'):
            try:
                splash_pixmap = QPixmap('icons/microphone.png')
            except Exception:
                pass
                
        if splash_pixmap and not splash_pixmap.isNull():
            splash = QSplashScreen(splash_pixmap)
            splash.show()
            app.processEvents()
            
            # 显示启动信息
            splash.showMessage("正在初始化应用程序...", 
                               Qt.AlignBottom | Qt.AlignCenter, Qt.white)
            app.processEvents()
        else:
            splash = None
        
        # 检查模型文件
        if 'ensure_model_exists' in globals():
            if splash:
                splash.showMessage("正在检查语音识别模型...", 
                                  Qt.AlignBottom | Qt.AlignCenter, Qt.white)
                app.processEvents()
            
            # 检查模型是否存在
            ensure_model_exists()
        
        # 创建并显示主窗口
        if splash:
            splash.showMessage("正在加载主界面...", 
                              Qt.AlignBottom | Qt.AlignCenter, Qt.white)
            app.processEvents()
            
        window = AudioRecorderApp()
        
        # 关闭启动画面并显示主窗口
        if splash:
            splash.finish(window)
        
        window.show()
        sys.exit(app.exec())
    except Exception as e:
        print(f"应用程序启动错误: {str(e)}")
        traceback.print_exc()
        
        msg = QMessageBox()
        msg.setIcon(QMessageBox.Critical)
        msg.setText("应用程序启动失败")
        msg.setInformativeText(str(e))
        msg.setWindowTitle("错误")
        msg.setDetailedText(traceback.format_exc())
        msg.exec()
        
        with open('error.log', 'w', encoding='utf-8') as f:
            f.write(f"错误: {str(e)}\n")
            f.write(traceback.format_exc())
            
        sys.exit(1)
