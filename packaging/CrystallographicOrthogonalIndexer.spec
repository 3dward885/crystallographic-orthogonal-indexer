# Windows-only, one-directory bundle: installer carries the complete directory.
from pathlib import Path
import sys
if sys.platform != 'win32':
    raise SystemExit('Build this specification on Windows; PyInstaller is not a cross-compiler.')
root = Path(SPECPATH).parent
notices = root / '.build' / 'notices'
if not (notices / 'inventory.json').is_file():
    raise SystemExit('Run tools/collect_notices.py before building.')
a = Analysis(
    [str(root / 'main.py')], pathex=[str(root)], binaries=[],
    datas=[(str(root / 'USER_GUIDE.txt'), '.'),
           (str(root / 'THIRD_PARTY_NOTICES.md'), '.'),
           (str(notices), 'licenses')],
    hiddenimports=['numpy.linalg', 'tkinter.ttk', 'tkinter.filedialog'],
    hookspath=[], hooksconfig={}, runtime_hooks=[], excludes=[], noarchive=False,
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz, a.scripts, [], exclude_binaries=True,
    name='CrystallographicOrthogonalIndexer', debug=False, bootloader_ignore_signals=False,
    strip=False, upx=False, console=False, disable_windowed_traceback=False,
    version=str(root / 'packaging' / 'version_info.txt'),
    icon=str(root / 'packaging' / 'app.ico'), uac_admin=False,
    contents_directory='_internal',
)
coll = COLLECT(exe, a.binaries, a.datas, strip=False, upx=False,
               name='CrystallographicOrthogonalIndexer')
