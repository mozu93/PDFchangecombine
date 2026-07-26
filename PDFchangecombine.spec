# -*- mode: python ; coding: utf-8 -*-

import glob

from PyInstaller.utils.hooks import collect_data_files

customtkinter_datas = collect_data_files('customtkinter')
tkinterdnd2_datas   = collect_data_files('tkinterdnd2')
# バージョンアップ時の「更新内容」ポップアップ表示用（release_notes.pyが探す）
release_notes_datas = [(f, '.') for f in glob.glob('RELEASE_NOTES_v*.md')]

a = Analysis(
    ['src/main.py'],
    pathex=['.', 'src'],
    binaries=[],
    datas=customtkinter_datas + tkinterdnd2_datas + release_notes_datas + [
        ('assets/icon.ico', 'assets'),
        ('assets/icon.png', 'assets'),
    ],
    hiddenimports=[
        'customtkinter',
        'tkinterdnd2',
        'PIL',
        'PIL.Image',
        'PIL.ImageTk',
        'reportlab',
        'reportlab.pdfgen.canvas',
        'reportlab.lib.pagesizes',
        'fitz',
        'docx',
        'docx.oxml',
        'openpyxl',
        'pptx',
        'packaging',
        'packaging.version',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['matplotlib', 'numpy', 'pandas', 'pytest', 'weasyprint', 'certifi'],
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='PDFConverter',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    icon='assets/icon.ico',
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='PDFConverter',
)
