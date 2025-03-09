from PyInstaller.utils.hooks import collect_data_files
import platform

a = Analysis(
    ["influx_data_cleaner.py"],
    pathex=[],
    binaries=[],
    datas=[("app_icon.png", "."), ("logo_large.png", ".")],
    hiddenimports=["platformdirs", "ttkbootstrap", "darkdetect"],
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
    name="influx_data_cleaner",  # Base name for all platforms
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,  # Ensures windowed app and .app bundle on macOS
    icon="logo_large.png"  # PNG icon for all platforms; PyInstaller handles conversion
)

# Create macOS application bundle
if platform.system().lower() == "darwin":
    app = BUNDLE(
        exe,
        name="influx_data_cleaner.app",
        icon="logo_large.png",  # Use PNG directly for macOS bundle
        bundle_identifier="com.markusdd.influxdatacleaner"  # Optional: Add a unique bundle identifier
    )