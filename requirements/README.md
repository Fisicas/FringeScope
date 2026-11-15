# Dependencies

From the repository root, install `requirements/requirements-runtime-lock.txt`
in a dedicated Python 3.12 environment for the recorded runtime versions.
`requirements.txt` lists the direct application dependencies; the runtime lock
also records their validated transitive distributions. This is a version
snapshot, not a hash-locked wheel archive.

For Windows packaging, additionally install
`requirements/requirements-build.txt` in a separate build environment and
follow [the Windows build guide](../docs/BUILDING_WINDOWS.md).

The static web builder itself needs only Python's standard library.
