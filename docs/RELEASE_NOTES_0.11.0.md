# FringeScope 0.11.0

FringeScope compares an analytic photosystem I (PSI)-inspired difference signal with selected step-scan FTIR artifacts in linked contour, spectral, kinetic and signed DAS views. The Windows application and deployed [browser edition](https://Fisicas.github.io/FringeScope/) use the same scientific engine. The guided tour, synthetic demonstrations, theory, primary references and numerical exports are included.

Distribution formats are source, a per-user Windows installer, a portable Windows folder and a static web build. Windows binaries are unsigned. Keep the portable executable beside `_internal`; retain third-party notices and matching Qt/PySide source companions with binary distributions. The web edition downloads its pinned Pyodide runtime from jsDelivr.

All spectra are simulated. The source includes analytic model inputs and two documented CSV slices, rather than an experimental matrix or a full reference-case dataset. The simulations demonstrate consequences of specified coupling, waveform and response assumptions; numerical agreement cannot identify an experimental mechanism or calibrate optical power, detector response, mirror motion or temperature. The fourth-order displacement expansion has a bounded validity domain. The illustrative 840 Hz frequency is not a mechanism assignment.

Validation evidence and its chronology are in [VALIDATION.md](VALIDATION.md) and [WEB_VALIDATION.md](WEB_VALIDATION.md). Bundled Qt/PySide binaries are byte-identical to the official 6.11.2 wheels, matching source archives accompany the binaries, and a Qt-library substitution trial passed. Real mobile devices, a clean second Windows host and a Qt rebuild from modified source remain untested. Update checks are disabled in 0.11.0. No live newer-release update is claimed.

Original application code, documentation and synthetic inputs are MIT licensed. Third-party components retain their own terms. Citation metadata is in `CITATION.cff`. Released November 16, 2026; archived at Zenodo, DOI [10.5281/zenodo.24266818](https://doi.org/10.5281/zenodo.24266818).
