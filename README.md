<p align="center"><img src="desktop/assets/fringescope_128.png" width="96" alt="FringeScope magnifying lens logo"></p>

# FringeScope

**Time-resolved step-scan FTIR artifact simulator**

[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.24266818.svg)](https://doi.org/10.5281/zenodo.24266818)

[Open the browser app](https://Fisicas.github.io/FringeScope/) · [Theory and evidence](desktop/THEORY.md) · [Documentation](docs/README.md) · [Install on Windows](docs/INSTALLATION.md)

Explore how mirror motion, continuous out-of-band globar leakage and pulsed 532 nm actinic pickup change a synthetic flash-induced difference spectrum modeled on photosystem I (PSI). Linked contour, spectrum, kinetic and decay-associated spectrum (DAS) views let you compare the ideal signal with selected artifacts. All displayed signals are simulated.

FringeScope is a teaching and experiment-planning tool. It shows what a declared disturbance would do to a known signal, which helps when choosing controls for a real experiment. It does not analyze measured data or identify the cause of a feature in a measurement.

![FringeScope simulated ideal signal](docs/images/explore_dark.png)

## Start here

The current version is **0.11.0**. The browser app is deployed on GitHub Pages. Source, a Windows installer and a portable Windows build are the software distributions; their publication status is recorded on [GitHub Releases](https://github.com/Fisicas/FringeScope/releases).

Windows users can install the `FringeScope-setup.exe` without administrator privileges. The portable ZIP contains the standalone folder build. Keep its `FringeScope.exe` and `_internal` folder together. See [installation and troubleshooting](docs/INSTALLATION.md).

For source use, install Python 3.12 x64 and the pinned requirements in a new virtual environment, then run:

```powershell
py -3.12 -m venv .venv
& '.venv\Scripts\python.exe' -X utf8 -m pip install -r requirements/requirements-runtime-lock.txt
& '.venv\Scripts\python.exe' -X utf8 desktop/startup.py
```

The validation environment is recorded in [validation](docs/VALIDATION.md). Other dependency combinations and operating systems have not been established by those checks. `pip install .` is not the supported installation route for this source layout.

## Repository guide

| Folder | Contents |
| --- | --- |
| [desktop/](desktop/README.md) | Application modules, shared scientific model, bundled figures, theory and notices |
| [docs/](docs/README.md) | Installation, validation, release notes, development guides and synthetic examples |
| [web/](web/README.md) | Browser interface, worker adapter and static-site builder |
| [tools/](tools/README.md) | Windows build, installer and packaging checks |
| [tests/](tests) | Scientific, desktop and browser-contract regression tests |
| [requirements/](requirements/README.md) | Runtime pins and build dependencies |

Run the commands below from the repository root. The web build uses the shared files in `desktop/`; the Windows build collects their existing runtime paths. Generated runs, binaries and `web/site/` are excluded from Git.

## Explore an artifact

1. Begin with **Reset to ideal**, or select **Guided tour** to follow ideal → mirror → globar → actinic leakage.
2. Click a source button to turn it on. Click again to turn it off; its parameters are retained. Composite motion is an optional waveform within **Mirror motion**.
3. Click or drag on the contour to select a wavenumber and time. The default is 1697 cm⁻¹ and 100 µs. Displayed wavenumbers descend over the full sampled band, about 2106.39–1053.20 cm⁻¹.
4. Compare the spectrum, kinetics and signed DAS/offset. The time is bin-centered or explicitly labeled as interpolated. Use the prompt bin to inspect actinic pickup; the alias map itself is fixed by the OPD grid.
5. Export a new run folder to retain settings, grids, masks, spectra, fits and figures. [Tutorial](desktop/TUTORIAL.md) explains the controls and assumptions.

![FringeScope mirror example](docs/images/mirror_dark.png)

Dark appearance is the default; light appearance is available. Short desktop windows keep plots readable in a scrollable plot area. Web exports temporarily lock editing and wait for the committed calculation so figures and data share one state. Guided-tour exit restores any saved optimized fit exactly. Tooltips explain practical causes and the forward model. **Demonstrations** provides original synthetic lessons inspired by Rödig and Siebert's step-scan artifact experiments, with detector traces, artifact baselines, harmonics and coherent averaging.

## Scientific scope

The PSI-inspired difference signal has two bin-averaged exponential components and a causal non-decaying residual. It is an analytic approximation with declared archival influence and literature-guided thermal features; no measured spectral matrix or digitized literature curve is distributed. It is not a calibrated photochemical or temperature model.

Mirror motion changes OPD by twice the mirror displacement. The main engine uses a fourth-order displacement expansion with documented limits. Continuous leakage enters both reference and signal: it can dilute a genuine difference but does not create a flash transient in an unchanged stationary linear system. Optical-wavelength folding requires OPD-dependent coupling. Uniform bypass light has no optical fringe carrier. Electrical pickup, harmonics and return mismatch are optional sensitivity models. An illustrative 840 Hz oscillation, including its equality to 14 × 60 Hz, does not identify an experimental mechanism.

Read [theory and evidence](desktop/THEORY.md), the offline `THEORY.html` reading copy, [model assumptions](desktop/MODEL_ASSUMPTIONS.md) and [primary references](desktop/REFERENCES.bib). No smoothing, baseline subtraction or amplitude normalization is silently applied to the simulated ΔA. Nonpositive intensity reconstructions remain masked. Figures and text distinguish simulation, numerical checks, literature evidence and unverified apparatus assumptions.

## Reproduce and test

```powershell
& '.venv\Scripts\python.exe' -X utf8 -m pip install pytest
& '.venv\Scripts\python.exe' -X utf8 -m pytest -q tests
& '.venv\Scripts\python.exe' -X utf8 desktop/build_demos.py
& '.venv\Scripts\python.exe' -X utf8 desktop/hene_evidence.py
& '.venv\Scripts\python.exe' -X utf8 desktop/build_convergence.py
& '.venv\Scripts\python.exe' -X utf8 desktop/build_theory.py
```

Figure generators preserve numerical provenance. `desktop/build_convergence.py` re-renders bundled audit metrics; it does not independently rerun that audit. See [validation](docs/VALIDATION.md) and [Windows build instructions](docs/BUILDING_WINDOWS.md).

## Citation, license and development

Cite **Nelson, M. R. (2026). FringeScope: Time-resolved step-scan FTIR artifact simulator (version 0.11.0). Zenodo. [https://doi.org/10.5281/zenodo.24266818](https://doi.org/10.5281/zenodo.24266818)**. That DOI identifies version 0.11.0, released November 16, 2026; [10.5281/zenodo.24266817](https://doi.org/10.5281/zenodo.24266817) always resolves to the latest version. [CITATION.cff](CITATION.cff) provides machine-readable metadata. Cite the relevant primary spectroscopy papers for scientific claims.

Original FringeScope code, documentation and synthetic model inputs are under the [MIT license](LICENSE). Third-party components retain their own licenses; see [notices](desktop/THIRD_PARTY_NOTICES.md). No UFit code, proprietary font files or literature PDFs are included. See [contributing](docs/CONTRIBUTING.md), [changelog](docs/CHANGELOG.md) and [release notes](docs/RELEASE_NOTES_0.11.0.md).

## Browser edition

FringeScope Web runs the same `ftir_sim.py` in a phone, tablet or desktop browser through Pyodide (Python and NumPy/SciPy compiled to WebAssembly) in a background worker. No server or install is needed, and calculations stay on the device. It offers linked Explore views, the guided tour, the fixed demonstrations, a theory article generated from THEORY.md, and ZIP exports produced by the desktop export function. The Windows application remains the reference edition.

```powershell
& '.venv\Scripts\python.exe' -X utf8 web\build_web.py
& '.venv\Scripts\python.exe' -X utf8 -m http.server 8000 --directory web\site
```

Then open `http://localhost:8000/`. The first visit downloads about 20 MB of pinned runtime from jsDelivr. `validate.html` compares browser results with native desktop fixtures on your own device. See [web edition guide](docs/WEB_EDITION_PLAN.md) and [web validation](docs/WEB_VALIDATION.md). The Pages address is [Fisicas.github.io/FringeScope](https://Fisicas.github.io/FringeScope/). Deployment uses the manual **Deploy web edition (manual)** workflow; a source push does not deploy it automatically. The browser runtime is downloaded separately; a web ZIP is not a fully offline installation.
