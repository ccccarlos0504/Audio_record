import os
import sys
import logging
import threading
from PySide6.QtWidgets import QApplication, QMessageBox, QProgressDialog
from PySide6.QtCore import QThread, Signal as pyqtSignal, Qt

# 添加当前路径到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

try:
    from whisper_manager import download_whisper_model, get_available_models
except ImportError:
    QMessageBox.critical(None, "错误", "找不到whisper_manager模块，应用程序无法初始化。")
    sys.exit(1)

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    filename='model_loader.log',
    filemode='w',
    encoding='utf-8'
)
logger = logging.getLogger('model_loader')

class ModelDownloadThread(QThread):
    """模型下载线程"""
    progress_signal = pyqtSignal(int)
    finished_signal = pyqtSignal(bool, str)
    
    def __init__(self, model_size):
        super().__init__()
        self.model_size = model_size
    
    def run(self):
        try:
            # 模拟进度
            for i in range(0, 101, 5):
                if i == 50:
                    # 实际下载
                    download_whisper_model(self.model_size, force_download=False)
                self.progress_signal.emit(i)
                self.msleep(200)  # 休眠一段时间
                
            self.finished_signal.emit(True, "模型下载完成")
        except Exception as e:
            logger.error(f"下载模型出错: {str(e)}")
            self.finished_signal.emit(False, str(e))

def ensure_model_exists():
    """确保至少有一个可用的模型文件"""
    try:
        # 检查是否有可用的模型
        available_models = get_available_models()
        
        if not available_models:
            logger.info("没有找到可用的模型，将尝试下载tiny模型")
            app = QApplication(sys.argv)
            
            msg_box = QMessageBox()
            msg_box.setIcon(QMessageBox.Information)
            msg_box.setWindowTitle("模型下载")
            msg_box.setText("未找到语音识别模型文件，需要下载初始模型。")
            msg_box.setInformativeText("将下载最小的tiny模型(约75MB)。是否继续？")
            msg_box.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
            msg_box.setDefaultButton(QMessageBox.Yes)
            
            if msg_box.exec() == QMessageBox.Yes:
                progress = QProgressDialog("正在下载语音识别模型...", "取消", 0, 100)
                progress.setWindowTitle("模型下载")
                progress.setWindowModality(Qt.WindowModal)
                progress.setMinimumDuration(0)
                
                # 创建下载线程
                download_thread = ModelDownloadThread("tiny")
                download_thread.progress_signal.connect(progress.setValue)
                download_thread.finished_signal.connect(
                    lambda success, msg: handle_download_result(success, msg, progress)
                )
                
                # 开始下载
                download_thread.start()
                progress.exec()
                
                # 等待线程结束
                download_thread.wait()
            else:
                logger.info("用户取消了模型下载")
                QMessageBox.warning(None, "警告", "没有可用的模型文件，语音识别功能将无法使用。")
        else:
            logger.info(f"找到可用的模型: {list(available_models.keys())}")
    except Exception as e:
        logger.error(f"检查和下载模型时出错: {str(e)}")

def handle_download_result(success, message, dialog):
    """处理下载结果"""
    dialog.setValue(100)
    
    if success:
        QMessageBox.information(None, "下载完成", "模型下载成功！现在可以使用语音识别功能。")
    else:
        QMessageBox.critical(None, "下载失败", f"模型下载失败: {message}\n请手动下载模型文件。")
    
    dialog.close()

if __name__ == "__main__":
    ensure_model_exists()
