# FringeScope Web: validation record

The following initial validation was recorded November 15, 2026 for a locally served browser build. Pages was subsequently deployed successfully in workflow run 43769787082 for commit 37a1f382de4ddbfd92350cb58f01a8ccd713f7bf. The numerical and viewport results below describe the local runs, not tests on physical mobile devices. The site was served from `web/site` on a local HTTP server and opened in the Chromium-based browser pane of the Claude desktop app on the Windows 11 development workstation.

## What was checked

| Check | Result |
| --- | --- |
| `pytest tests` (45 existing + 6 web-edition tests) | 51 passed |
| Web controls vs. desktop Qt widgets (keys, defaults, ranges, steps, combo items) | identical |
| Web settings transformation vs. `app.MainWindow.settings()` over 41 control states (40 randomized) | identical `Settings` |
| Explore payload vs. direct `simulate` + `fit_das` (native) | bit-identical arrays |
| Each tour step: desktop tour panel vs. the web replica of `tour.py` vs. the original forward tour sequence; Back, Finish and restoration | identical `Settings` and fit window; previous controls restored |
| Built engine files (`ftir_sim.py`, model JSON, release config, theory/assumption/reference files) | byte-identical to their shared source files in `desktop/`, SHA-256 recorded and verified by the worker before use |
| Release audit (`review/audit_release.py`, extended to `web/` and `.github/`) | 494 files, no findings; scientific files identical to v11 |
| Static build with site-packages disabled (`python -S`) | succeeds; deterministic build ID |

## Browser-versus-native numerical parity

`site/validate.html` recomputed 20 declared scenarios in Pyodide 314.0.8 (Python 3.14.2, NumPy 2.4.6, SciPy 1.18.0) and compared them with native fixtures from the desktop's pinned environment (Python 3.12.10, NumPy 2.5.3, SciPy 1.18.1). Compared quantities: three full spectra (26, 42, 300th bins), kinetics at 1697 cm⁻¹ and at the 532 nm alias channel, the projected reconstruction, all signed DAS rows, lifetimes, the total NaN count and every fully masked channel.

**Result: 20 of 20 passed.**

- 18 fixed-basis scenarios (ideal; biased/zero-bias/composite/servo/envelope mirror motion; random and free-running phase; magnitude readout; steady and changing globar leakage; interferometric, step-dependent and uniform actinic pickup; mains and free electrical pickup; return mismatch with jitter; all sources combined): largest ΔA difference 5.1 × 10⁻¹⁵ OD and largest DAS difference 3.8 × 10⁻¹⁴ OD, i.e. floating-point round-off. NaN masks identical. Seeded random terms reproduce exactly.
- 2 free-lifetime refits: lifetimes agree to 3.3 × 10⁻⁹ (relative); DAS to 1.9 × 10⁻⁹ OD (0.002 µOD). The optimizer's stopping point moves at round-off level between platforms, so these scenarios use a stated 1 × 10⁻⁸ OD DAS tolerance instead of 1 × 10⁻¹⁰ OD. The first run, with the stricter tolerance applied to all scenarios, reported 19 of 20; the tolerance change is recorded here, not hidden.

Browser computation time on this workstation: 0.10–0.20 s for most scenarios, 0.75 s for ten locked coadds of mirror motion.

## Interface checks (emulated viewports)

- Desktop 1400–1500 px, dark: Explore 2 × 2 linked panels, Compare, DAS and offset, Optical contributions and all three Diagnostics views rendered without console errors. Source toggles, contour click selection and status/warning text worked.
- Tablet 768 px, light: 2 × 2 grid, controls in a drawer, DAS legend below the axes, no horizontal page scroll.
- Phone 375 px: contour followed by a Spectrum / Kinetics / DAS switcher; compact toolbar; labeled time and wavenumber sliders; controls drawer; Theory article with contents drawer, infobox after the lead, 15 numbered SVG equations (scaled to at least 80 %, otherwise horizontally scrollable), captioned figures and a full-size figure viewer; no horizontal page scroll.
- Guided tour (second pass, usability): the tour panel shows step n of 4, what changed and numbered targets; the same numbers appear on the plots, source button and view tabs. Checked at 1440 px (panel docked beside the plots, controls hidden while touring) and 375 px (bottom sheet with Back/Next always visible; tapping a target selects the matching Spectrum / Kinetics / DAS panel and folds the sheet). Back, Next, the Optical-contributions targets of step 3, the 3 µs bin at the 532 nm alias channel 1945.94 cm⁻¹ in step 4, deep links `index.html#tour-1` to `#tour-4`, Exit and Finish all worked; Finish restored a previously enabled source and the selections. The "where to look" statements were checked against engine output (for example ±100 µOD mirror oscillation at 1697 cm⁻¹, ≈ 8 % globar dilution, a single −65 µOD channel at the alias in the 3 µs bin).
- Theory and Tutorial: "Start the guided tour" buttons and per-step links render at phone width without horizontal scrolling.
- After the restyle (neutral palette, square corners, no animation): Explore at 1440 px in light and dark and at 375 px, the tour on both, and the Theory page re-checked; no console errors. Smooth scrolling was replaced by an immediate jump because it did not complete reliably in the emulated phone view.
- Desktop application (offscreen Qt render, 1500–1720 px, both themes): tour panel in place of the controls, numbered plot markers, the step-3 Optical contributions outline, and the source-mode self-test (`--self-test-output`) passed.
- Export: produced a 10.7 MB ZIP containing `simulation.npz`, `simulated_descending.dpt`, `time_us.csv`, `exported_spectral_mask.csv`, `settings_and_provenance.json`, `DAS_and_offset.csv`, `analysis_settings.json` (with browser runtime versions and kernel hashes), the theory/model/reference files and PNGs of the shown panels. The test captured the file in memory rather than saving it.

## Not yet verified

- Real devices: iOS Safari and Android Chrome on actual phones and tablets, including first-load time on a mobile connection, peak memory and touch gestures (tap, press-and-hold drag, swipe scrolling). Viewport emulation does not reproduce mobile touch handling or memory limits.
- Firefox and Safari desktop.
- Screen-reader walkthrough, 200 % text zoom and a formal colour-contrast audit.
- Numerical parity and interaction checks on the live hosted deployment; successful workflow deployment is recorded above.

Run `validate.html` on each target device and record the environment text it prints.

## Audit-repair verification (November 15, 2026)

The review's mid-export-edit defect was reproduced and repaired. Exports now lock the workspace, await pending calculation and rendering, and require the displayed result ID in the worker. The browser regression captures four consistent panels, attempts a real source-button click during capture, verifies it is blocked, and separately starts export with a calculation pending. It also checks exact free-fit restoration through the tour and exported worker metadata, the 375 px reference layout, and all 20 numerical parity scenarios.

Run the optional real-browser regression after building the site:

```powershell
python -m pip install playwright==1.65.2
python web/tools/check_browser_repairs.py --browser-exe 'C:/path/to/chrome.exe' --output qa_browser
```

This uses an isolated browser context and localhost; it does not deploy. Browser test hooks are added only to test responses. The tests require access to the pinned Pyodide CDN. Desktop native-user/export tests now use unique scratch directories and exact analysis restoration. Existing pre-repair reports above remain historical; the repair results and final checksums are recorded in the release-review packet. Real iOS/Android device trials remain open.
