# Browser edition

From the repository root:

```powershell
python -X utf8 web/build_web.py
python -X utf8 -m http.server 8000 --directory web/site
```

Open `http://localhost:8000/`. Building uses only Python's standard library;
the browser loads the pinned Pyodide runtime, NumPy and SciPy from jsDelivr.
The builder reads the engine, model, theory, figures and shared control help
from `../desktop/`. The generated, Git-ignored `site/` contains byte-identical
engine/model copies with SHA-256 manifests; no source paths are needed at run time.

- `src/`: interface templates, JavaScript, CSS, controls and parity fixtures.
- `web_kernel.py`: browser adapter around the shared scientific engine.
- `vendor/`: redistributed Plotly bundle and its license.
- `tools/`: native parity-fixture generator and real-browser regression checks.

The manual Pages workflow builds `web/site/` from a clean checkout and publishes
that directory. See [web validation](../docs/WEB_VALIDATION.md) and
[the edition plan](../docs/WEB_EDITION_PLAN.md).
