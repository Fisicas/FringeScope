# Validation record

## Current release-pass scope (November 15, 2026)

The extracted LF-normalized source candidate passes 58 Python regression tests, CFF 1.2.0 schema validation and ORCID validation. All 307 copied notice hashes match the archived bytes. Both example CSV arrays reproduce exactly with `tools/generate_examples.py`; the underlying model and engine retain the v11 numerical content after newline normalization. `tools/check_release.py` checks the extracted distribution, rather than only the Windows working copy.

Version 0.11.0 was tagged at commit `b4a8a072dba68fd2f1ea9712d44f4cde56d8679d` (tree `9cd8ab483d00fbc4a59e0a5263ffbf3376124057`) and deployed to GitHub Pages from that commit. The Zenodo archive (DOI 10.5281/zenodo.24266818) was downloaded and found file-for-file identical to that tree; `tools/check_release.py` passes on it. The records below preserve earlier test chronology, environments and hashes. They are not exact-byte claims about a later normalized archive.

The release binaries were built from that extracted source. The portable build passed its frozen self-test, and the installer passed per-user install, in-place replacement with stale-file cleanup, export preservation and uninstall. All 36 bundled Qt/PySide6/shiboken6 binaries are byte-identical to the official 6.11.2 wheels, matching the attached Qt source archives; a copy with a substituted `Qt6Core.dll` passed the self-test. Unsigned binaries, untested real mobile devices, clean-second-host portability and a Qt rebuild from modified source remain limitations. Update checks are disabled in 0.11.0.

## Historical development and packaging checks

The v11 baseline passed 45 regression tests and standalone/installed smoke checks, plus installation, same-version replacement, stale-runtime removal, export preservation and uninstall on the development Windows 11 x64 workstation. The author completed hands-on usability testing of the native application on November 15, 2026; specific devices and display scales were not recorded, and no clean-second-host test was made.

The prepared release source adds MIT licensing, citation/release documentation and dependency notices, and removes three unused historical/static plotting functions. The numerical engine, model JSON and waveform defaults are unchanged. The prepared source passed all 45 regression tests. Its standalone executable passed startup, 21 offline theory elements in both themes, fixed demonstrations, tour restoration and finite descending export from a separate working directory. Synthetic example files and three screenshots were regenerated. The deterministic source-tree audit found no excluded measurement/document/font files, private home paths, credential patterns or broken local links in its checked scope. The final prepared installer also passed current-user installation, same-version replacement, stale-runtime cleanup, preservation of exported user files and uninstall of the dedicated test copy. See docs/VALIDATION_RESULTS.json for the public summary.

Tested baseline: Python 3.12.10 x64, NumPy 2.5.3, SciPy 1.18.1, Matplotlib 3.11.2, PySide6-Essentials 6.11.2 and packaging 26.3. Dependency ranges in metadata do not establish validation for all versions. Motion/electrical terms use bin centers; chemical/pulse bases use their declared integration rules. No experimental mechanism, confidence interval, calibrated optical response or temperature change is inferred.

The browser edition is recorded separately in docs/WEB_VALIDATION.md: 51/51 tests including six web-equivalence tests, and 20/20 browser-versus-native parity scenarios in Pyodide 314.0.8 (NumPy 2.4.6, SciPy 1.18.0) on this workstation. Real mobile-device trials are not yet done.

These historical checks did not themselves establish clean-second-host portability or the Qt binary checks described above. A live newer-release update was not tested. The installer is unsigned; update checks are disabled.

## Prepublication audit repairs

The repaired candidate passes 56 Python regression tests, including stale result-ID rejection, unique scratch-directory cleanup, preservation of existing files, exact browser/native free-fit tour restoration, and scrollable plots at 1280 × 640. The real-Chrome regression checks locked four-panel exports, export during pending calculation, exact tour fit restoration including worker export, and a 375 px Theory page without horizontal overflow. All 20 browser/native numerical parity scenarios pass. The shared science environment was not upgraded. Existing Matplotlib/Qt deprecation warnings remain in the pinned environment; no numerical failure is inferred from them.

The browser test script is web/tools/check_browser_repairs.py; its required Playwright package is an optional development tool, not an app dependency. Test browser inspection hooks exist only in substituted local test responses. Repaired binaries and their expanded self-test results are recorded in the local release-review packet after building. These tests did not publish a software release; network update checks are disabled.


## Repository cleanup verification (November 15, 2026)

The reorganized tree passes the same 56 Python regressions and 20 real-Chrome/native numerical scenarios. The engine, synthetic-model JSON and waveform defaults remain byte-identical to the reviewed v11 baseline. The web builder reads the shared scientific files from `desktop/`; browser exports, exact fitted-state tour restoration and the 375 px theory layout pass again.

The subsequent GitHub-equation repair raises the Python regression count to 58. All 15 public equations use native fenced math with equation numbers; both custom readers check them against the canonical expressions before displaying the bundled equations. The regenerated offline theory HTML is byte-identical to the preceding version. Real-Chrome checks and all 20 numerical parity scenarios pass again; these local checks do not assert a hosted GitHub preview has been inspected before pushing.

Source startup from outside the source folder and fresh standalone/installed checks verify both themes, all 21 offline theory assets, demonstrations, fitted-state restoration, short-window scrolling and finite descending exports. Isolated installer replacement removes a stale runtime file while preserving exported user data; uninstall also preserves those outputs. A clean extracted source archive rebuilds the same web manifest using only the Python standard library. These checks do not replace the remaining device, second-host or binary redistribution review gates above.
