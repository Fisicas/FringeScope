# Windows build and packaging

Run `tools/build_windows.py` from the repository root using the prepared build
environment and an explicit `--iscc` path. See the complete
[build instructions](../docs/BUILDING_WINDOWS.md).

- `FringeScope.spec` collects modules and runtime resources from `../desktop/`
  and the documentation from `../docs/`.
- `FringeScope.iss` creates the per-user Windows installer; its application ID
  and install/update paths are preserved across the repository reorganization.
- `fringescope-install.json` identifies installations created by this installer.
- `qa_installation.py` verifies isolated installation, replacement, exports and
  uninstall. Use the documented isolated test directories; it must not replace
  a normal user installation.

Build outputs are excluded from Git. These tools do not upload or publish assets.
