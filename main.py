#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import os
import traceback
import logging
from PySide6.QtWidgets import QApplication, QMainWindow, QMessageBox
from audio_recorder import AudioRecorderApp


if __name__ == "__main__":
    try:
        print("启动语音录制与转写应用...")
        app = QApplication(sys.argv)
        window = AudioRecorderApp()
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
