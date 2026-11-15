# Installation and troubleshooting

## Windows

Run the prepared `FringeScope-setup.exe`. The per-user default is `%LOCALAPPDATA%\Programs\FringeScope`; administrator access is not required. The installer creates a Start menu entry and offers a desktop shortcut. To uninstall, use Windows Installed apps or the included `unins000.exe`.

For the standalone folder, retain all files beside `FringeScope.exe`, including `_internal`. A separate Python installation is unnecessary for either binary form. The current installer is unsigned; a publisher signature is not claimed.

Logs, Matplotlib cache and the initial export location are under `%LOCALAPPDATA%\FringeScope`, outside the application folder. Export also accepts a selected destination. Keep personal outputs outside the application directory; in-place replacement cleans obsolete runtime files. Uninstall preserves separately stored user outputs.

## Updates

The prepared review build has `updates_enabled: false`. Startup/manual checks stop before making a network request. Following an authorized public release, an installed release build can check for a newer stable GitHub release and offer installation. It downloads an expected `FringeScope-setup.exe`, verifies the published SHA-256 and exact size, replaces the installed app and relaunches it after confirmation. Source and standalone-folder copies do not self-update. No forced silent update of unsaved work is intended.

A digest checks integrity against the release metadata; it is not an independent publisher signature. Draft/prerelease versions are excluded. A live newer-release update has not yet been tested. Do not enable review-build network checks just to simulate a public release.

## Troubleshooting

- **Missing assets or startup failure:** retain the whole standalone folder, or reinstall. Inspect the newest log in the user-data directory. Do not copy individual DLLs from unrelated applications into FringeScope.
- **No change after actinic pickup:** inspect the early acquisition bin, coupling route and full band; a prompt optical pulse is not a millisecond-long signal. The alias map's wavelength/grid relationship does not change with leakage amplitude.
- **Nonfinite/blank values:** inspect the reference and masks. Nonpositive reconstructed intensities are masked instead of being replaced with an artificial positive floor.
- **Slow computation:** reduce optional acquisition complexity, close memory-intensive applications, and retain settings when reporting the issue. In the browser edition, the first visit downloads the Python runtime; later visits use the browser cache. Mobile-browser performance has not yet been measured on real devices; run `validate.html` there and report its environment text.
- **Export location inaccessible:** select a writable user folder. Export creates new versioned run directories.

The tested platform is Windows 11 x64 with the pinned scientific environment. A clean-second-host check remains separate from user acceptance of the UI. See VALIDATION.md.
