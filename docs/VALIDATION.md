# Validation record

The v11 baseline passed 45 regression tests and standalone/installed smoke checks, plus installation, same-version replacement, stale-runtime removal, export preservation and uninstall on the development Windows 11 x64 workstation. The user reported successful stage-5 native usability testing on November 15, 2026. Specific devices/scales and a clean-second-host test were not reported.

The prepared release source adds MIT licensing, citation/release documentation and dependency notices, and removes three unused historical/static plotting functions. The numerical engine, model JSON and waveform defaults are unchanged. The prepared source passed all 45 regression tests. Its standalone executable passed startup, 21 offline theory elements in both themes, fixed demonstrations, tour restoration and finite descending export from a separate working directory. Synthetic example files and three screenshots were regenerated. The deterministic source-tree audit found no excluded measurement/document/font files, private home paths, credential patterns or broken local links in its checked scope. The final prepared installer also passed current-user installation, same-version replacement, stale-runtime cleanup, preservation of exported user files and uninstall of the dedicated test copy. See docs/VALIDATION_RESULTS.json for the public summary.

Tested baseline: Python 3.12.10 x64, NumPy 2.5.3, SciPy 1.18.1, Matplotlib 3.11.2, PySide6-Essentials 6.11.2 and packaging 26.3. Dependency ranges in metadata do not establish validation for all versions. Motion/electrical terms use bin centers; chemical/pulse bases use their declared integration rules. No experimental mechanism, confidence interval, calibrated optical response or temperature change is inferred.

The browser edition is recorded separately in docs/WEB_VALIDATION.md: 51/51 tests including six web-equivalence tests, and 20/20 browser-versus-native parity scenarios in Pyodide 314.0.8 (NumPy 2.4.6, SciPy 1.18.0) on this workstation. Real mobile-device trials are not yet done.

Remaining release gates: a clean second-host trial; final binary dependency/source/build-input and modified-library replacement review; and a live newer-release update after publication is authorized. The installer is unsigned. Review-build checks remain disabled; no remote publication or DOI work is implied by these tests.

## Prepublication audit repairs

The repaired candidate passes 56 Python regression tests, including stale result-ID rejection, unique scratch-directory cleanup, preservation of existing files, exact browser/native free-fit tour restoration, and scrollable plots at 1280 × 640. The real-Chrome regression checks locked four-panel exports, export during pending calculation, exact tour fit restoration including worker export, and a 375 px Theory page without horizontal overflow. All 20 browser/native numerical parity scenarios pass. The shared science environment was not upgraded. Existing Matplotlib/Qt deprecation warnings remain in the pinned environment; no numerical failure is inferred from them.

The browser test script is web/tools/check_browser_repairs.py; its required Playwright package is an optional development tool, not an app dependency. Test browser inspection hooks exist only in substituted local test responses. Repaired binaries and their expanded self-test results are recorded in the local release-review packet after building. Publication and update checks remain on hold.


## Repository cleanup verification (November 15, 2026)

The reorganized tree passes the same 56 Python regressions and 20 real-Chrome/native numerical scenarios. The engine, synthetic-model JSON and waveform defaults remain byte-identical to the reviewed v11 baseline. The web builder reads the shared scientific files from `desktop/`; browser exports, exact fitted-state tour restoration and the 375 px theory layout pass again.

The subsequent GitHub-equation repair raises the Python regression count to 58. All 15 public equations use native fenced math with equation numbers; both custom readers check them against the canonical expressions before displaying the bundled equations. The regenerated offline theory HTML is byte-identical to the preceding version. Real-Chrome checks and all 20 numerical parity scenarios pass again; these local checks do not assert a hosted GitHub preview has been inspected before pushing.

Source startup from outside the source folder and fresh standalone/installed checks verify both themes, all 21 offline theory assets, demonstrations, fitted-state restoration, short-window scrolling and finite descending exports. Isolated installer replacement removes a stale runtime file while preserving exported user data; uninstall also preserves those outputs. A clean extracted source archive rebuilds the same web manifest using only the Python standard library. These checks do not replace the remaining device, second-host or binary redistribution review gates above.
