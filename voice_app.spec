# -*- mode: python ; coding: utf-8 -*-

import sys
import os
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

block_cipher = None

# 收集需要包含的模块
hidden_imports = [
    'matplotlib', 
    'matplotlib.backends.backend_qt5agg',
    'matplotlib.backends.backend_qtagg',
    'numpy',
    'pydub',
    'pydub.generators',
    'pyaudio',
    'pywhispercpp',
    'pywhispercpp.model', 
    'pywhispercpp.constants', 
    'pywhispercpp.utils',
    'model_loader',
    'whisper_manager',
    'audio_recorder_whisper',
    'wave',
    'tempfile',
    'traceback',
    'threading',
    'logging',
]

# 收集pywhispercpp所有子模块
hidden_imports.extend(collect_submodules('pywhispercpp'))

# 定义需要复制的文件和文件夹
datas = [
    ('icons', 'icons'),
    ('model_guide.md', '.'),
    ('download_model.py', '.'),
    ('model_loader.py', '.'),
    ('PACKAGED_README.md', 'README.md'),
]

# 添加models文件夹(如果存在)
if os.path.exists('models'):
    datas.append(('models', 'models'))

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=hidden_imports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='语音录制与转写工具',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='icons/microphone.ico',
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='语音录制与转写工具',
)
