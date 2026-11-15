# FringeScope Web: GitHub Pages edition

Status (November 15, 2026): **implemented locally as a preview and validated on the development workstation (see [docs/WEB_VALIDATION.md](docs/WEB_VALIDATION.md)); not deployed.** Nothing has been pushed, Pages is not enabled and no hosted preview exists. The intended project URL `https://Fisicas.github.io/FringeScope/` is not claimed to exist. Zenodo and DOI work stay deferred. The Windows application, its scientific engine and its prepared 0.11.0 binaries are unchanged by this work.

## Decision

Yes, a browser edition and the standalone application can coexist in one repository. GitHub Pages serves static files only, so the browser edition computes on the visitor's device:

- **One scientific kernel.** The browser runs the repository's own `ftir_sim.py` with `synthetic_model.json` and `release_config.json` under Pyodide (CPython compiled to WebAssembly), in a module Web Worker. No formula is re-implemented in JavaScript. The build copies these files byte-for-byte and records their SHA-256 in `site/build_manifest.json`.
- **Pinned runtime.** Pyodide 314.0.8 (Python 3.14.2, NumPy 2.4.6, SciPy 1.18.0) is loaded from jsDelivr at a fixed version. Desktop validation used NumPy 2.5.3 / SciPy 1.18.1, so numerical identity is not assumed; it is tested (below).
- **Static, private by construction.** No account, server, upload, analytics or cookies. The page stores only the theme choice in local storage. GitHub and jsDelivr still receive ordinary request logs (IP address, user agent); the site says so.
- **Plots.** Plotly.js cartesian bundle, vendored and pinned (MIT), for touch-capable zoom/pan and PNG export. Arrays are transferred as float64; no display decimation.
- **Theory as an article.** `THEORY.md` is the single source. A stdlib-only builder renders it as a responsive, Wikipedia-like article: serif headings, numbered SVG equations with text alternatives, tap-to-enlarge figures, a sticky contents panel on desktop and a contents drawer on phones, anchors and back-to-top links.

## Site map (five destinations)

| Page | Contents | Needs Python runtime |
| --- | --- | --- |
| Explore (`index.html`) | Source toggles, linked contour / spectrum / kinetics / DAS, other views, controls drawer, guided tour, export ZIP | Yes |
| Demonstrations | The four fixed lessons rendered by `build_demos.py`, light and dark, labeled **precomputed** | No |
| Theory | Article generated from `THEORY.md` | No |
| Tutorial | How the tour works, the four steps with a live link to each (`index.html#tour-N`), and the desktop notes from `TUTORIAL.md` | No |
| Download / Cite | Desktop downloads (after publication), citation, license, web-runtime notices and privacy | No |

## Interaction contract

- Same defaults as desktop: ideal signal, 1697 cm⁻¹, 100 µs, full descending band, the same control ranges and the same settings transformation (`bias_nm = 0` when mirror motion is off, mains harmonic × 60 Hz, HeNe off). Control help text is generated from `ui_help.py`.
- Phone: contour first, then one selected Spectrum / Kinetics / DAS panel; controls in a drawer. Tablet/desktop: 2 × 2 linked panels with a side panel.
- Contour gestures: a tap selects; press-and-hold then drag moves the crosshair; an ordinary swipe scrolls the page. Pan/zoom is a separate, visible mode. Numeric inputs and sliders give keyboard and touch alternatives. Help uses tappable (?) buttons, not hover.
- Guided tour: steps and text come from `tour.py`, shared with the desktop application, whose tour panel works the same way (tested to reproduce the original tour's control states). A tour panel (in place of the controls on a computer, a collapsible bottom sheet on phones and tablets) shows the step number, what changed and a numbered "where to look" list; the same numbers mark the plots, source buttons and view tabs, and each item shows and outlines its target. Back, Next and End tour are always visible; ending or finishing restores the previous controls and selections. Theory and Tutorial carry "Start the guided tour" buttons.
- Appearance: the interface palette matches the desktop `ui_theme.py` (neutral greys, one muted blue accent, square corners, no decorative animation).
- Busy indicator, latest-request-wins queue (stale results ignored), reset view, reset to ideal, theme toggle, reduced-motion respected.
- Export runs the desktop `export_result` inside the worker and downloads a ZIP: NPZ arrays and masks, finite-channel DPT, time axis, DAS CSV, settings/provenance JSON with the browser runtime versions, the theory/assumption/reference files and PNGs of the shown panels.

## Verification gates

1. `pytest tests/test_web_edition.py`: the web settings mapping equals the desktop `MainWindow.settings()` for many control states and for every tour step; web control defaults/ranges equal the desktop widgets; kernel payloads are finite, descending and correctly masked; the builder output has no broken local links.
2. Browser parity page (`site/validate.html`) runs declared scenarios in Pyodide (ideal, biased mirror, composite/servo, random and free-running phase, globar steady/transient, interferometric/bypass actinic, electrical, mismatch with jitter, noise, magnitude readout, combinations, and the free lifetime refit), and compares them with native fixtures from `web/tools/make_parity_fixtures.py`.
3. Layout checks at phone (375 px), tablet (768 px) and desktop widths in both themes. Real iOS Safari / Android Chrome trials remain a user step and are reported as unverified until done.

Results so far: 51/51 tests passed; browser parity 20/20 scenarios (fixed-basis agreement ≈ 10⁻¹⁵ OD; free refits within the stated optimizer tolerance); emulated phone/tablet/desktop layouts, tour restoration and export checked. Real-device trials remain open.

## Source layout

- `web/web_kernel.py`: browser adapter (settings mapping, view payloads, ZIP export) around the unchanged engine.
- `web/src/`: page fragments, `controls.json` (mirror of the desktop controls), CSS and JavaScript (`explore.js`, `worker.js`, `common.js`, `validate.js`) and `parity_fixtures.json`.
- `web/vendor/`: pinned Plotly.js cartesian bundle and its MIT license.
- `web/build_web.py`: stdlib-only builder writing the git-ignored `web/site/`.
- `web/tools/make_parity_fixtures.py`: regenerates native fixtures (needs the pinned scientific environment).
- `tests/test_web_edition.py`: desktop-equivalence and build-integrity tests.

## Deployment (not performed)

`.github/workflows/pages.yml` is manual-only (`workflow_dispatch`). It builds `web/site` with the standard library and deploys it. Enabling Pages, pushing or running the workflow needs explicit approval. An offline PWA shell is deferred until after the first release.

## Primary technical sources consulted

- [GitHub Pages: what it hosts](https://docs.github.com/en/pages/getting-started-with-github-pages/what-is-github-pages) and [limits](https://docs.github.com/en/pages/getting-started-with-github-pages/github-pages-limits).
- [Pyodide in a module Web Worker](https://pyodide.org/en/stable/usage/webworker.html) and [available packages](https://pyodide.org/en/stable/usage/packages-in-pyodide.html); package versions were read from the pinned `pyodide-lock.json`.
