#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Whisper模型下载与管理工具 - 使用pywhispercpp
"""

import os
import sys
import logging
import tempfile
from pathlib import Path

# 导入pywhispercpp
try:
    from pywhispercpp.model import Model
    from pywhispercpp.constants import MODELS_DIR
    from pywhispercpp.utils import download_model as pywhisper_download_model
except ImportError:
    raise ImportError("请安装pywhispercpp库: pip install pywhispercpp")

import urllib.request
import re

logger = logging.getLogger('whisper_manager')

# 自定义模型目录(程序根目录下的models文件夹)
CUSTOM_MODELS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "models")
os.makedirs(CUSTOM_MODELS_DIR, exist_ok=True)

# 模型类型
MODEL_SIZES = ["tiny", "base", "small", "medium", "large"]

# 量化模型类型
QUANTIZED_TYPES = ["q4_0", "q4_1", "q5_0", "q5_1", "q8_0"]

# 模型下载URL
MODEL_URLS = {
    # 标准模型
    "tiny": "https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-tiny.bin",
    "base": "https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-base.bin",
    "small": "https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-small.bin", 
    "medium": "https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-medium.bin",
    "large": "https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-large.bin",
    
    # 英文模型
    "tiny.en": "https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-tiny.en.bin",
    "base.en": "https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-base.en.bin",
    "small.en": "https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-small.en.bin",
    "medium.en": "https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-medium.en.bin",
    
    # 量化模型(Q8_0)
    "tiny-q8_0": "https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-tiny-q8_0.bin",
    "base-q8_0": "https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-base-q8_0.bin",
    "small-q8_0": "https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-small-q8_0.bin",
    "medium-q8_0": "https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-medium-q8_0.bin",
    "large-q8_0": "https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-large-q8_0.bin",
    
    # 量化模型(Q5_0)
    "tiny-q5_0": "https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-tiny-q5_0.bin",
    "base-q5_0": "https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-base-q5_0.bin",
    "small-q5_0": "https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-small-q5_0.bin",
    "medium-q5_0": "https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-medium-q5_0.bin",
    "large-q5_0": "https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-large-q5_0.bin",
    
    # 量化模型(Q4_0)
    "tiny-q4_0": "https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-tiny-q4_0.bin",
    "base-q4_0": "https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-base-q4_0.bin",
    "small-q4_0": "https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-small-q4_0.bin",
    "medium-q4_0": "https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-medium-q4_0.bin",
    "large-q4_0": "https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-large-q4_0.bin",
}

def get_model_name(model_size):
    """解析模型名称规范，支持量化模型格式"""
    # 支持直接指定完整文件名
    if model_size.startswith("ggml-") and model_size.endswith(".bin"):
        return model_size
    
    # 检查是否是量化模型格式 (如small-q8_0)
    quantized_match = re.search(r'(tiny|base|small|medium|large)-(q\d+_\d+)', model_size)
    if quantized_match:
        size = quantized_match.group(1)
        quant = quantized_match.group(2)
        return f"ggml-{size}-{quant}.bin"
    
    # 检查是否是英文模型
    if model_size.endswith(".en"):
        return f"ggml-{model_size}.bin"
    
    # 标准模型
    return f"ggml-{model_size}.bin"

def get_available_models():
    """获取本地已下载的模型列表
    
    返回：
        字典，键为显示名称（如"small-q8_0"），值为完整文件名（如"ggml-small-q8_0.bin"）
    """
    available_models = {}
    
    # 确保目录存在
    os.makedirs(CUSTOM_MODELS_DIR, exist_ok=True)
    
    # 检查自定义目录中的模型
    if os.path.exists(CUSTOM_MODELS_DIR):
        for filename in os.listdir(CUSTOM_MODELS_DIR):
            if filename.startswith("ggml-") and filename.endswith(".bin"):
                # 从文件名解析模型规格
                base_name = filename[5:-4]  # 去掉"ggml-"前缀和".bin"后缀
                
                # 处理各种模型命名格式
                if base_name in MODEL_SIZES:
                    model_id = base_name  # 标准模型
                elif base_name.endswith(".en") and base_name[:-3] in MODEL_SIZES:
                    model_id = base_name  # 英文模型
                elif "-q" in base_name:
                    # 量化模型，如"small-q8_0"
                    parts = base_name.split("-q")
                    if len(parts) == 2 and parts[0] in MODEL_SIZES:
                        model_id = f"{parts[0]}-q{parts[1]}"
                    else:
                        model_id = base_name
                else:
                    model_id = base_name
                    
                available_models[model_id] = filename
    
    # 检查默认目录中的模型（如果与自定义目录不同）
    if os.path.exists(MODELS_DIR) and os.path.abspath(MODELS_DIR) != os.path.abspath(CUSTOM_MODELS_DIR):
        for filename in os.listdir(MODELS_DIR):
            if filename.startswith("ggml-") and filename.endswith(".bin"):
                # 从文件名解析模型规格（与上面相同的逻辑）
                base_name = filename[5:-4]  # 去掉"ggml-"前缀和".bin"后缀
                
                # 处理各种模型命名格式
                if base_name in MODEL_SIZES:
                    model_id = base_name  # 标准模型
                elif base_name.endswith(".en") and base_name[:-3] in MODEL_SIZES:
                    model_id = base_name  # 英文模型
                elif "-q" in base_name:
                    # 量化模型
                    parts = base_name.split("-q")
                    if len(parts) == 2 and parts[0] in MODEL_SIZES:
                        model_id = f"{parts[0]}-q{parts[1]}"
                    else:
                        model_id = base_name
                else:
                    model_id = base_name
                    
                # 仅当自定义目录中没有同名模型时添加
                if model_id not in available_models:
                    available_models[model_id] = filename
    
    logger.info(f"找到本地模型: {list(available_models.keys())}")
    return available_models

def find_model_in_directories(model_name):
    """在自定义目录和默认目录中查找模型文件"""
    # 首先检查自定义目录
    custom_path = os.path.join(CUSTOM_MODELS_DIR, model_name)
    if os.path.exists(custom_path):
        logger.info(f"在自定义目录找到模型: {custom_path}")
        return custom_path
    
    # 然后检查默认目录
    default_path = os.path.join(MODELS_DIR, model_name)
    if os.path.exists(default_path):
        logger.info(f"在默认目录找到模型: {default_path}")
        return default_path
    
    # 如果都找不到，返回自定义目录的路径(用于下载)
    return custom_path

def get_model_path(model_size="small"):
    """获取模型文件存储路径"""
    # 确保模型目录存在
    os.makedirs(CUSTOM_MODELS_DIR, exist_ok=True)
    
    # 解析模型名称
    model_name = get_model_name(model_size)
    
    # 查找模型文件
    return find_model_in_directories(model_name)

def download_progress(count, block_size, total_size):
    """下载进度回调函数"""
    percent = int(count * block_size * 100 / total_size)
    sys.stdout.write(f"\r下载进度: {percent}% [{count * block_size} / {total_size}]")
    sys.stdout.flush()

def list_available_models():
    """列出所有可用的模型选项"""
    models = []
    
    # 标准模型
    models.extend(MODEL_SIZES)
    
    # 英文模型
    models.extend([f"{size}.en" for size in MODEL_SIZES])
    
    # 量化模型
    for size in MODEL_SIZES:
        for quant in QUANTIZED_TYPES:
            models.append(f"{size}-{quant}")
    
    return models

def get_model_url(model_spec):
    """获取模型下载URL"""
    # 直接在字典中查找
    if model_spec in MODEL_URLS:
        return MODEL_URLS[model_spec]
    
    # 尝试从模型名称解析
    model_name = get_model_name(model_spec)
    base_url = "https://huggingface.co/ggerganov/whisper.cpp/resolve/main"
    
    return f"{base_url}/{model_name}"

def download_whisper_model(model_size="small", force_download=False, multilingual=True):
    """
    下载Whisper模型
    
    参数:
        model_size: 模型大小和类型，如"small", "small-q8_0", "small.en"等
        force_download: 是否强制重新下载
        multilingual: 是否使用多语言模型(支持中文)
    
    返回:
        模型文件路径
    """
    # 处理模型规格
    if not multilingual and ".en" not in model_size and "-" not in model_size:
        # 如果需要英文模型并且未指定，添加.en后缀
        download_model_size = f"{model_size}.en"
        logger.info(f"使用英文模型: {download_model_size}")
    else:
        download_model_size = model_size
        logger.info(f"使用指定模型: {download_model_size}")
    
    # 获取模型路径
    model_path = get_model_path(download_model_size)
    
    # 如果模型已存在且不强制下载，直接返回路径
    if os.path.exists(model_path) and not force_download:
        logger.info(f"模型已存在: {model_path}")
        return model_path
    
    # 模型不存在或强制下载，执行下载
    try:
        # 确保目录存在
        os.makedirs(os.path.dirname(model_path), exist_ok=True)
        
        logger.info(f"开始下载模型: {download_model_size}")
        print(f"开始下载Whisper模型: {download_model_size}")
        
        # 获取下载URL
        try:
            url = get_model_url(download_model_size)
            logger.info(f"模型下载URL: {url}")
        except Exception as url_error:
            logger.error(f"无法确定模型URL: {str(url_error)}")
            raise ValueError(f"不支持的模型: {download_model_size}，可用选项: {list_available_models()}")
        
        # 下载模型
        logger.info(f"从 {url} 下载到 {model_path}")
        print(f"从 {url} 下载到 {model_path}")
        urllib.request.urlretrieve(url, model_path, download_progress)
        print(f"\n模型下载完成: {model_path}")
        
        return model_path
    except Exception as e:
        logger.error(f"模型下载失败: {str(e)}")
        print(f"\n模型下载失败: {str(e)}")
        raise
    
    return model_path

def initialize_whisper(model_size="small", language="zh"):
    """
    初始化Whisper模型
    
    参数:
        model_size: 模型类型和大小，如"small"、"small-q8_0"等
        language: 语言，默认"zh"中文
        
    返回:
        初始化好的Whisper模型实例
    """
    try:
        logger.info(f"初始化Whisper模型: {model_size}")
        
        # 获取模型路径
        model_path = get_model_path(model_size)
        
        # 确认模型文件是否存在
        if not os.path.exists(model_path):
            logger.warning(f"模型文件不存在，尝试下载: {model_path}")
            model_path = download_whisper_model(model_size)
        
        logger.info(f"使用模型文件: {model_path}")
        
        # 创建模型实例，直接传入模型文件路径
        model = Model(model_path)
        
        return model
    except Exception as e:
        logger.error(f"Whisper初始化失败: {str(e)}")
        raise

def transcribe_audio_with_whisper(audio_file, model_size="small", language="zh"):
    """
    使用Whisper转写音频文件
    
    参数:
        audio_file: 音频文件路径(WAV格式)
        model_size: 模型大小，可选"tiny", "base", "small", "medium", "large"
        language: 语言，默认"zh"中文
        
    返回:
        转写文本
    """
    try:
        model = initialize_whisper(model_size, language)
        
        # 转写音频
        logger.info(f"开始转写音频: {audio_file}")
        
        # 获取文件的绝对路径
        audio_file_path = os.path.abspath(audio_file)
        logger.info(f"使用绝对路径进行转写: {audio_file_path}")
        
        # 检查音频文件是否存在
        if not os.path.exists(audio_file_path):
            error_msg = f"音频文件不存在: {audio_file_path}"
            logger.error(error_msg)
            raise FileNotFoundError(error_msg)
            
        # 检查并修复音频格式（如果需要）
        try:
            # 为了避免依赖问题，在这里添加简单的采样率检查
            import wave
            with wave.open(audio_file_path, 'rb') as wf:
                sample_rate = wf.getframerate()
                if sample_rate != 16000:
                    error_msg = f"WAV file must be 16000 Hz (current is {sample_rate} Hz)"
                    logger.error(error_msg)
                    raise ValueError(error_msg)
        except Exception as format_check_error:
            logger.error(f"检查音频格式时出错: {str(format_check_error)}")
            raise
        
        # 设置语言和转写参数
        # pywhispercpp的参数处理方式与原来的不同
        segments = model.transcribe(audio_file_path, language=language)
        
        # 收集所有转写文本
        text = " ".join([segment.text for segment in segments])
        
        logger.info("音频转写完成")
        return text.strip()
    except Exception as e:
        logger.error(f"音频转写失败: {str(e)}")
        raise
