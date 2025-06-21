#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Whisper模型下载工具

使用方法: python download_model.py [模型类型]
模型类型示例: 
- 标准模型: tiny, base, small, medium, large
- 量化模型: small-q8_0, medium-q5_0
- 英文模型: small.en

默认下载tiny模型。
"""

import sys
import os
from whisper_manager import (
    download_whisper_model, MODEL_SIZES, QUANTIZED_TYPES, 
    get_model_path, CUSTOM_MODELS_DIR, list_available_models
)

def main():
    print("Whisper模型下载工具")
    print("===================")
    
    # 显示模型存储位置
    print(f"模型将被下载到: {CUSTOM_MODELS_DIR}")
    
    # 列出所有可用的模型选项
    print("\n可用模型类型:")
    print("1. 标准模型:")
    for size in MODEL_SIZES:
        print(f"   - {size} {'(推荐初次使用)' if size == 'tiny' else ''}")
    
    print("\n2. 量化模型(体积更小):")
    for quant in QUANTIZED_TYPES:
        print(f"   - small-{quant} {'(推荐平衡选择)' if quant == 'q8_0' else ''}")
    
    print("\n3. 英文模型(仅支持英文，体积更小):")
    print("   - tiny.en, base.en, small.en 等")
    
    # 获取模型参数
    model_choice = input("\n请选择要下载的模型 [tiny]: ").strip() or "tiny"
    
    # 询问是否强制重新下载
    model_path = get_model_path(model_choice)
    force_download = False
    if os.path.exists(model_path):
        force_download = input(f"模型文件已存在({model_path})，是否重新下载? [y/N]: ").strip().lower() in ["y", "yes"]
    
    print("\n开始下载过程...")
    try:
        downloaded_path = download_whisper_model(
            model_size=model_choice,
            force_download=force_download
        )
        print(f"\n模型下载成功: {downloaded_path}")
        print("您现在可以运行应用程序使用此模型进行语音识别。")
    except Exception as e:
        print(f"\n下载失败: {str(e)}")
        print("请检查网络连接，或尝试手动下载模型文件。")

if __name__ == "__main__":
    main()
