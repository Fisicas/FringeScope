# Desktop application and shared scientific resources

Run `python -X utf8 desktop/startup.py` from the repository root after installing
the pinned requirements in `requirements/requirements-runtime-lock.txt`.

The flat Python modules, model JSON, figures, logo, theory reading copy and
third-party notices form one self-contained runtime resource directory. The
web builder copies the scientific engine and its required model files from
here without modifying them. The Windows freezer retains the same resource
relationships inside the collected runtime. Guides are in `../docs/`.

See [the main README](../README.md), [theory](THEORY_GITHUB.md), [LaTeX source](THEORY.md),
[model assumptions](MODEL_ASSUMPTIONS.md), [tutorial](TUTORIAL.md),
[references](REFERENCES.bib) and [third-party notices](THIRD_PARTY_NOTICES.md).
