# Building the Windows app locally

Use Windows x64, Python 3.12.10, pinned runtime requirements, PyInstaller 6.22.0 and Inno Setup 6. Create a dedicated build environment; do not upgrade a shared analysis environment. Install `requirements/requirements.txt` and `requirements/requirements-build.txt` there. The resulting application embeds its runtime and resources.

```powershell
py -3.12 -m venv .build-venv
& '.build-venv\Scripts\python.exe' -X utf8 -m pip install -r requirements/requirements-runtime-lock.txt -r requirements/requirements-build.txt
& '.build-venv\Scripts\python.exe' -X utf8 tools\build_windows.py --iscc 'C:\path\to\Inno Setup 6\ISCC.exe'
```

The build renders THEORY.html, records tested versions, sanitizes the dependency-collection PATH, runs PyInstaller, compiles the installer, and writes checksums. It does not upload files, create a release or enable update checks. Keep the collected license directory and notices beside the binary. Binary dependency/source obligations must be reviewed against the actual final package.

The source modules and shared resources are under `desktop/`; the freezer keeps their existing runtime relationships. Use a short absolute `--output` directory when building inside a deeply nested checkout: the Windows installer compiler can encounter legacy path-length limits when collecting license files. The builder normalizes the output path before passing it to external tools.

The prepared source uses MIT. Bundled Qt/PySide libraries keep their own terms. Source availability and replacing compatible shared Qt/PySide DLLs are described in [Qt source and replacement guide](../desktop/licenses/QT_SOURCE_AND_REPLACEMENT.md). Rebuild validation must include startup, both themes, offline theory, demonstrations, exports, installation/replacement/uninstall and relevant numerical tests. The package is not independently validated on a clean second host yet.

requirements/requirements-runtime-lock.txt records all 30 Python distributions seen in the validated module graph. It is a version snapshot, not a hash-locked wheel archive or proof of a bit-identical rebuild on another host. BUILD_ENVIRONMENT.json in the local review packet records the actual build.
