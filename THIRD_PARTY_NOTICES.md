# Third-party notices and release review

Crystallographic Orthogonal Indexer is packaged using **PyInstaller** and **Inno Setup**.
Its runtime includes **CPython**, **Tcl/Tk**, **NumPy**, and binary dependencies
collected by their packaging hooks (potentially BLAS/Fortran/runtime libraries).

`tools/collect_notices.py` copies actual license/notice files from the approved
Windows build environment into the bundle's `licenses/` directory and writes a
hash inventory. It requires Python, Tcl, Tk and NumPy notices; if a distribution
omits them, authentic matching-version notices must be supplied using the
explicit supplemental directory option. Missing notices are not invented.

The NumPy wheel's complete license directory must remain intact, including
notices for bundled third-party libraries. The final DLL inventory and associated
obligations must be reviewed before broader redistribution. This automated
collection **is not a complete legal/license audit or a full SBOM**.

No publisher company, application copyright owner, EULA, commercial licensing
terms or code-signing identity has been assigned by this packaging task. Those
remain the owner's release decisions if public/commercial distribution is planned.
The request for a commercial-style installer does not itself mean the program
will be sold.

Primary references, checked October 24, 2026:
- CPython license: https://docs.python.org/3/license.html
- NumPy: https://numpy.org/doc/stable/license.html
- Tcl/Tk: https://www.tcl-lang.org/software/tcltk/license.html
- PyInstaller licensing exception: https://pyinstaller.org/en/stable/license.html
- Inno Setup license: https://jrsoftware.org/files/is/license.txt
- Inno Setup commercial licensing information: https://jrsoftware.org/isorder.php

PyInstaller documents an exception permitting distribution of bundled programs
under their own appropriate licenses, subject to dependency obligations. Inno
Setup asks commercial users to purchase a license; its official FAQ states
this is not strictly required. Check the actual license and intended use before
commercial distribution. No purchase or license agreement was made here.
