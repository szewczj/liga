# -*- mode: python ; coding: utf-8 -*-
import os


project_dir = os.path.abspath(SPECPATH)

a = Analysis(
    [os.path.join(project_dir, "gui.py")],
    pathex=[project_dir],
    binaries=[],
    datas=[
        (os.path.join(project_dir, "voxelowa_postac.png"), "."),
    ],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    exclude_binaries=False,
    name="LigaPilkarska",
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
    icon=os.path.join(project_dir, "voxelowa_postac.ico"),
)
