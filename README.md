# Crystallographic Orthogonal Indexer 1.0

Python desktop calculator for signed Miller plane normals and orthonormal
Front/Right/Top frames, with explicit handedness and TXT export.

## Run

Use an existing Python runtime with NumPy and Tkinter:

```powershell
python main.py
```

No XYZ file, previous app package, VESTA, MATLAB or network connection is required.
Tool/dependency installation remains deferred until explicitly requested.

## Background tests

```powershell
python -B tools/run_source_validation.py --mode all --name local-check
```

Choose a new receipt name for each run; existing evidence is never overwritten.
The runner finds this project from its own location, keeps Tk windows hidden,
uses validation/temporary/ for scratch files, and writes JSON/log receipts under
validation/. It does not drive the desktop or open native file choosers.
A legitimate Tk display is still needed for real hidden-widget tests.

## Folder guide

| Location | Purpose |
|---|---|
| main.py | Application launcher |
| crystallographic_orthogonal_indexer.py | Scientific core and Tk GUI |
| tests/ | Source tests and unchanged accepted-reference fixture |
| tools/ | Background test runner and deferred build helpers |
| packaging/ | PyInstaller/Inno recipes, Windows metadata and existing icon |
| docs/PROJECT_STATE.json | Authoritative current state, conventions and next task |
| docs/DECISIONS.jsonl | Consolidated decision log with source provenance |
| docs/CHANGELOG_v1.0.txt | Product v1.0 source-change notes |
| docs/WORKSPACE_ORGANIZATION_2026-10-26.txt | Layout change and verification report |
| validation/ | Current source-test and integrity receipts |
| archive/ | Original handoff, legacy source, audits, receipts and state snapshots |

The active application is at the project root. Archived scripts and receipts
retain their historical text and paths; use the current tools/ runner for new
work. archive/organization-2026-10-26/path-map.json maps every original file to
its new location and records its original hash. All historical file contents
remain preserved. archive/ is ignored by Git by default while retained locally;
source tests include the required reference fixture independently of that archive.
No repository, commit or push is created by the workspace organization.

## Scientific contract

- Cell lengths are angstrom; angles are degrees: alpha=(b,c), beta=(a,c),
  gamma=(a,b). Cartesian ab′c* is right-handed: x parallel +a; y along the
  positive component of b perpendicular to a; z parallel a cross b.
- A=[a b c] contains direct-cell vectors as columns, using the positive Cholesky
  construction. Signed Miller PLANE normals satisfy A.T n=hkl in inverse
  angstrom, without 2π. A direct [uvw] direction would use A@[u,v,w]; no general
  direct-direction mode is implemented.
- Front-first Gram–Schmidt remains F=unit(nF),
  R=unit(unit(nR)-(F·unit(nR))F), U=F cross R.
  T=sign(unit(nT)·U)U. Original normals and all angular adjustments are reported.
- Reject abs(unit(nT)·U) <= max(1e-8,128*eps*cond(A)/sin(raw F,R angle)).
  Other cell/conditioning/parallel-input guards remain unchanged. Numerical
  guards and printed float64 precision are not experimental uncertainty.
- Physical D=[F R T] maps column components by v_xyz=D v_physical and
  v_physical=D.T v_xyz. Its determinant may be ±1. Q_standard=[F R U] is the
  separate right-handed reference. A left-handed D is not a proper EasySpin
  Euler/rotation frame; physical labels are never flipped to force +1.
- XYZ comparison assumes already-Cartesian angstrom coordinates with shared
  crystallographic/indexing convention. No setting transformation, reflection,
  molecular rotation or screen-based correction is inferred. This app does not
  infer a magnetic easy axis or independently establish experimental orientation.

The accepted reference is tests/fixtures/accepted_v1_1_Ho1_results.json (SHA-256
f2f006f8c6ff533727bf7250382993d495c1728e5c95d418a651b13545d625b1).
Its physical frame is left-handed after an explicitly accepted Top-only reversal.
The sample's actual signed Top hkl is absent; the partial GUI example leaves
Top blank. No experimental Top is invented by the tests or application.

The original integer-boundary fix, pip preflight guard and eight regression
methods are retained. Original integer values are checked before float conversion;
precision a caller already discarded cannot be recovered. Historical validation
and the unreproduced 96-case legacy comparison remain labelled in archive/.

## Deferred Windows distribution

Product version is 1.0 independently of legacy numbering; numeric Windows
file/product version is 1.0.0.0. No Windows executable or installer has been built
or installation-tested. Compilation, dependency/tool installation and installer
QA remain deferred until requested. Keep tests in the background without taking
control of the user's desktop; interactive chooser/high-DPI acceptance is pending.

The recipes retain PyInstaller onedir/windowed bundling and Inno per-user
LocalAppData installation. Stable AppId:
B11BE05C-E5E8-4447-8DB4-A8289A009D74. Existing icon artwork is unchanged.

Inherited intended pins remain unverified for current availability/compatibility:
CPython 3.13.17, pip 26.2.2, NumPy 2.3.5, PyInstaller 6.22.3, community hooks
2026.9, Inno Setup 7.1.0. Reverify official sources before any future downloads
or installations; coordinate approved changes across guards, tests and docs.
Do not use build_windows.ps1 as a source-test shortcut: it invokes the deferred
packaging process. Intended future artifacts are
CrystallographicOrthogonalIndexer.exe and
CrystallographicOrthogonalIndexer-1.0-windows-x64-Setup.exe.

USER_GUIDE.txt, WINDOWS_QA.md and THIRD_PARTY_NOTICES.md describe usage and future
acceptance/notices. No signing, complete redistribution review or public-release
readiness is claimed.
