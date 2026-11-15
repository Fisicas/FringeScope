# Changelog

## 0.11.0 — prepared initial release; not yet published

- Synthetic PSI-inspired difference model with two exponential components and a causal residual; no experimental dataset selector or measured arrays.
- Independent on/off controls for mirror motion, globar leakage and 532 nm actinic pickup; optional electrical and registration effects.
- Linked contour selections, individual spectra, kinetics and signed DAS/offset; full descending sampled band.
- Original detector/OPD, artifact-baseline, harmonic and coherent-averaging demonstrations.
- Dark/light appearance, selected magnifying-lens branding, startup splash and reversible guided tour.
- Guided tour panel (desktop and browser): replaces the controls while touring, states what changed at each step, numbers the plots and source buttons to inspect (clicking an item outlines its plot), and offers Back, Next and End tour. Tour steps and text live in one file, `tour.py`, shared by both editions; the control states are unchanged from the original tour (tested).
- Plainer interface styling in both editions: neutral greys with one muted blue accent, square corners, sentence-case labels, no glow or pulse animations. Plot colours and the logo are unchanged.
- Offline theory with numbered equations, primary references, synthetic figures and declared approximation limits.
- Per-user Windows installer, standalone folder, persistent user-data directories and verified-update mechanism. Review builds retain the no-network publication hold.
- MIT license, citation metadata, release documentation and collected third-party notices.
- Browser edition (preview, not deployed): the unchanged engine under pinned Pyodide in a Web Worker; responsive Explore, Demonstrations, Theory, Tutorial and Download/Cite pages; desktop-equivalent controls, tour and export; tour entry points and per-step links on the Theory and Tutorial pages; on-device numerical self-check; manual-only GitHub Pages workflow.

The prepared source removes unused experimental-replay/static plotting functions. The scientific engine, model JSON and waveform defaults remain identical to the user-reviewed v11 baseline. Earlier numbered development folders are local development history, not claimed public releases.

### Prepublication audit repairs (November 15, 2026)

- Web export waits for committed computation/rendering, locks editing through capture, and checks a result ID in the worker so PNGs, settings, fit and arrays come from one state.
- Desktop and web tours restore the exact saved analysis, including a free-lifetime fit, instead of rerunning a fixed projection.
- Desktop plots scroll at short window sizes; the initial window respects the available work area. Startup update timers are owned by the window and stop when it closes.
- Browser-adapter exports use unique temporary directories with cleanup; native tests select their own temporary root. Phone reference URLs wrap within the page.
- Added numerical/export/tour/sizing regressions and a reproducible optional Playwright browser check. Scientific engine/model files are unchanged; publication and update checks remain on hold.

### Repository organization (November 15, 2026)

- Grouped application modules and shared runtime resources in `desktop/`, guides and synthetic examples in `docs/`, and dependency lists in `requirements/`. Added navigation pages and direct README links to the browser app and theory.
- Updated the static-site builder, fixture generator, Python source configuration, test imports, Windows freezer and installer icon path. Frozen resource relationships, installer identity and persistent user-data paths are retained.
- Scientific engine and model inputs are byte-identical to the reviewed baseline; this update changes source organization and build paths.

### GitHub theory formatting

- Replaced private equation placeholders in `desktop/THEORY.md` with native GitHub math blocks and explicit equation numbers. Offline and browser readers validate those expressions against the canonical equation definitions and retain their existing numbered figure layout.
- Added regressions for complete public equations and rejection of formula/number mismatches. The numerical engine and scientific expressions are unchanged.
