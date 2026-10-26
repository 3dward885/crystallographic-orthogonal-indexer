"""Copy actual build-environment license files; fail if runtime notices absent.

This gathers evidence, not a complete legal/binary-dependency audit. Run only in
an approved Windows build environment. Does not download any files.
"""
from importlib import metadata
from pathlib import Path
import argparse
import hashlib
import json
import shutil
import sys


def license_candidate(path):
    return path.is_file() and (path.name.lower().startswith(('license', 'licence', 'copying', 'notice'))
                              or 'licenses' in (p.lower() for p in path.parts))


def collect(destination, extra=None):
    destination = Path(destination)
    destination.mkdir(parents=True, exist_ok=True)
    inventory = []
    categories = set()

    def copy_file(source, category, relative):
        target = destination/category/relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
        categories.add(category)
        inventory.append({'source': str(source), 'file': str(target.relative_to(destination)),
                          'sha256': hashlib.sha256(target.read_bytes()).hexdigest()})

    base = Path(sys.base_prefix)
    for p in base.glob('LICENSE*'):
        if p.is_file(): copy_file(p, 'Python', p.name)
    # Official Windows CPython includes Tcl/Tk; preserve matching runtime notices.
    tcl_root = base/'tcl'
    if tcl_root.is_dir():
        for p in sorted(tcl_root.rglob('*')):
            if license_candidate(p):
                relative = p.relative_to(tcl_root)
                category = 'Tk' if any(part.lower().startswith('tk') for part in relative.parts) else 'Tcl'
                copy_file(p, category, relative)
    for package in ('numpy', 'pyinstaller', 'pyinstaller-hooks-contrib'):
        dist = metadata.distribution(package)
        for relative in dist.files or ():
            source = Path(dist.locate_file(relative))
            if license_candidate(source):
                safe_parts = [p for p in relative.parts if p not in ('.', '..')]
                copy_file(source, package, Path(*safe_parts))
    # Optional exact-version upstream notices if a Windows distribution omitted them.
    if extra:
        for category in ('Python', 'Tcl', 'Tk', 'numpy'):
            folder = Path(extra)/category
            if folder.is_dir():
                for p in sorted(folder.rglob('*')):
                    if p.is_file(): copy_file(p, category, Path('supplemental')/p.relative_to(folder))
    required = {'Python', 'Tcl', 'Tk', 'numpy'}
    missing = required-categories
    if missing:
        raise SystemExit('Missing runtime license notices: '+', '.join(sorted(missing))+
                         '. Supply authentic matching-version notices with --extra DIR; do not fabricate them.')
    report = {'python': sys.version, 'base_prefix': str(base),
              'packages': {p: metadata.version(p) for p in ('numpy','pyinstaller','pyinstaller-hooks-contrib')},
              'files': inventory, 'complete_license_audit': False}
    (destination/'inventory.json').write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--out', required=True)
    parser.add_argument('--extra')
    args = parser.parse_args()
    collect(args.out, args.extra)
