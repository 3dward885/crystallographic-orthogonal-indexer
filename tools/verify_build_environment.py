"""Fail closed on wrong OS/architecture/versions; no installation side effects."""
from importlib import metadata
import json
import platform
import struct
import sys
import tkinter

EXPECTED = {'numpy': '2.3.5', 'pyinstaller': '6.22.3',
            'pyinstaller-hooks-contrib': '2026.9', 'pip': '26.2.2'}


def check():
    if sys.platform != 'win32' or struct.calcsize('P') != 8 or platform.machine().lower() not in ('amd64','x86_64'):
        raise SystemExit('Use native x64 Windows and 64-bit CPython; no cross-build is supported.')
    if sys.version_info[:3] != (3,13,17) or sysconfig_free_threaded():
        raise SystemExit('Pinned build requires standard (not free-threaded) CPython 3.13.17 x64.')
    versions = {name: metadata.version(name) for name in EXPECTED}
    if versions != EXPECTED:
        raise SystemExit(f'Build dependencies differ from the pins: {versions}')
    # Real Tcl/Tk display initialization is mandatory on the Windows build host.
    root = tkinter.Tk(); root.withdraw()
    tcl, tk = root.tk.call('info','patchlevel'), root.tk.call('package','require','Tk')
    root.destroy()
    print(json.dumps({'python':sys.version, 'platform':platform.platform(),
                      'packages':versions, 'tcl':tcl, 'tk':tk}, indent=2))


def sysconfig_free_threaded():
    import sysconfig
    return bool(sysconfig.get_config_var('Py_GIL_DISABLED'))


if __name__ == '__main__':
    check()
