# Windows release acceptance — 1.0, still pending

Current Windows source tests are distinct from frozen-app and installation
acceptance. Keep tests in the background; do not drive the user's desktop.
Interactive chooser/visual checks require a later explicit change of scope or
an authorized isolated test desktop. Compilation, tool/dependency installation
and installation QA remain deferred until requested.

Exact tool versions below are inherited historical intent, not current
availability/compatibility verification. Reverify official releases before
downloads or installations and coordinate approved pin changes across files.

Run in an explicitly authorized Windows test environment. Building does not
itself authorize installing the app on Eduardo's laptop. Prefer a disposable
Windows VM without Python installed for end-user verification.

## Build evidence
- [ ] Official x64 CPython 3.13.17 (standard build, Tk enabled) and Inno Setup
      7.1.0 from their verified download pages; tool installations authorized.
- [ ] Build dependencies and pip match verified pins on both fresh and reused
      venv paths; `pip check` passes; dependency freeze saved.
- [ ] All tests pass, including native Tk; no skipped tests in Windows release.
- [ ] Frozen executable smoke receipt confirms Windows, bundled runtime,
      both NumPy/Tk availability, calculation, TXT saving and close callback.
- [ ] Review PyInstaller warnings and collected DLLs; review runtime notices.

## User-interface checks
- [ ] Launch the EXE without a terminal, from a directory containing spaces.
- [ ] Inspect normal/high-DPI displays and 780 x 680 minimum-size layout.
- [ ] Both physical handednesses; blank Top example; invalid and ambiguous input.
- [ ] Actual Save TXT chooser: select folder/name, cancel, overwrite decline,
      Unicode path, unwritable destination; prior file remains intact on failure.
- [ ] Editing invalidates old output; repeated calculate/save/clear and close.

## Installation (requires separate approval for the target)
- [ ] Standard, non-admin user; install needs no elevation.
- [ ] Start-menu entry, optional desktop shortcut unchecked by default.
- [ ] Installed app runs on a clean x64 Windows machine without system Python.
- [ ] Runtime licenses and user guide are present in the installed bundle.
- [ ] Install paths with spaces/non-ASCII characters.
- [ ] Cancel setup before installation; no misleading success claim.
- [ ] Reinstall/update with the stable AppId; test with the app already open.
- [ ] Windows Apps uninstall and Start-menu uninstall remove installed files
      and shortcuts, while preserving TXT reports in the user's documents.
- [ ] Record exact OS/build, install/uninstall logs and final SHA-256 values.
- [ ] Apply organizational malware/signature policy without bypassing controls.

## Signing/public release
- [ ] Determine real publisher, approved certificate/signing service and owner
      licensing choices if distributing more broadly. No identity is fabricated.
- [ ] If signing is authorized, sign app before installer compilation, sign the
      installer/uninstaller appropriately, timestamp, and verify signatures.
- [ ] Recompute checksums and repeat relevant QA after signing or repackaging.

Current status: NO Windows executable or installer has been built or tested.
A build receipt alone is not installation acceptance. Do not mark these boxes
complete based only on Linux unit tests or static configuration checks.
