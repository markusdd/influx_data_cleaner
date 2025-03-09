from PyInstaller.utils.hooks import collect_data_files
import platform

a = Analysis(
    ["influx_data_cleaner.py"],
    pathex=[],
    binaries=[],
    datas=[("app_icon.png", "."), ("logo_large.png", ".")],
    hiddenimports=["platformdirs", "ttkbootstrap", "darkdetect", "PIL._tkinter_finder"],
    hookspath=[],
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=None,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=None)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name="influx_data_cleaner",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    icon="logo_large.png"
)

if platform.system().lower() == "darwin":
    app = BUNDLE(
        exe,
        name="influx_data_cleaner.app",
        icon="logo_large.png",
        bundle_identifier="com.markusdd.influxdatacleaner"
    )