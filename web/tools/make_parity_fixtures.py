"""Native (desktop-environment) reference samples for the browser self-check.

Runs the same web_kernel.compute path natively and stores sampled rows/columns,
DAS, lifetimes and NaN masks with full float64 precision (repr). The browser
page site/validate.html recomputes every scenario in Pyodide and compares.

    python -X utf8 web/tools/make_parity_fixtures.py
"""
import json, sys, platform
from pathlib import Path
import numpy as np, scipy

WEB = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(WEB.parent), str(WEB)]
import web_kernel as K  # noqa: E402

spec = json.loads((WEB/'src'/'controls.json').read_text(encoding='utf-8'))


def base():
    state = {}
    def walk(s):
        if s.get('toggle'): state[s['toggle']] = False
        for c in s.get('controls', []): state[c['key']] = c['value']
        for d in s.get('details', [])+s.get('subsections', []): walk(d)
    for s in spec['sections']: walk(s)
    return state


def scenario(name, free=False, **changes):
    s = base(); s.update(changes); return dict(name=name, free=free, controls=s)


SCENARIOS = [
    scenario('Ideal signal (all sources off)'),
    scenario('Mirror: biased sine, 10 locked coadds', wobble=True),
    scenario('Mirror: zero bias (even response, 2f)', wobble=True, bias_nm=0, coadds=1),
    scenario('Mirror: composite f + 2f + 3f', wobble=True, waveform='harmonic3', coadds=1),
    scenario('Mirror: servo-like composite', wobble=True, waveform='servo', coadds=1),
    scenario('Mirror: envelope with drift', wobble=True, waveform='envelope', envelope_slope=1.2, quadrature_slope=.6, chirp_hz_per_ms=20, coadds=1),
    scenario('Mirror: random step/shot phase', wobble=True, phase_mode='random', coadds=4),
    scenario('Mirror: free running', wobble=True, phase_mode='free', coadds=3),
    scenario('Mirror: magnitude readout', wobble=True, phase_readout='magnitude', coadds=1),
    scenario('Globar: steady leakage', globar=True),
    scenario('Globar: changing leak + blocking', globar=True, leak_transient_ppm=500, blocking_od=.5),
    scenario('Actinic: OPD-modulated 532 nm (tour)', laser=True, laser_area_us=2e-6),
    scenario('Actinic: step-dependent bypass', laser=True, laser_route='bypass_scatter', laser_area_us=2e-4),
    scenario('Actinic: uniform bypass, delayed', laser=True, laser_route='bypass_uniform', laser_delay_us=2.5),
    scenario('Electrical: 14 × 60 Hz pickup', electrical=True),
    scenario('Electrical: free 1234 Hz', electrical=True, electrical_mode='free', electrical_frequency=1234),
    scenario('Return mismatch with jitter', zpd=True),
    scenario('Combination: all sources', wobble=True, globar=True, laser=True, electrical=True, zpd=True, coadds=2),
    scenario('Refit lifetimes: mirror', free=True, wobble=True, coadds=1),
    scenario('Refit lifetimes: ideal, no offset', free=True, offset=False),
]


def clean(a):
    return [None if not np.isfinite(v) else float(f'{v:.12g}') for v in np.asarray(a, float).ravel()]


def main():
    out = []
    for sc in SCENARIOS:
        meta, arrays = K.compute(json.dumps(sc['controls']), free=sc['free'])
        meta = json.loads(meta)
        nu, t = arrays['nu'], arrays['t_us']
        cols = sorted({int(np.argmin(abs(nu-w))) for w in (1697., meta['laser_alias_cm1'])})
        rows = [26, 42, 300]
        obs, rec = arrays['observed'], arrays['reconstruction']
        out.append(dict(name=sc['name'], free=sc['free'], controls=sc['controls'], rows=rows, cols=cols,
            observed_rows=[clean(obs[i]) for i in rows], observed_cols=[clean(obs[:, j]) for j in cols],
            reconstruction_cols=[clean(rec[:, j]) for j in cols[:1]], das=[clean(r) for r in arrays['das']],
            nan_columns=np.flatnonzero(np.all(~np.isfinite(obs), axis=0)).tolist(),
            nan_count=int((~np.isfinite(obs)).sum()), observed_nansum=float(np.nansum(obs)), taus=meta['taus'],
            fit_rms_uOD=meta['fit_rms_uOD'], artifact_rms_full_uOD=meta['artifact_rms_full_uOD'], warnings=meta['warnings']))
    doc = dict(generated_by='web/tools/make_parity_fixtures.py', platform=platform.platform(), python=platform.python_version(),
               numpy=np.__version__, scipy=scipy.__version__, scenarios=out)
    path = WEB/'src'/'parity_fixtures.json'
    path.write_text(json.dumps(doc, separators=(',', ':')), encoding='utf-8')
    print(json.dumps({'fixtures': str(path), 'scenarios': len(out), 'bytes': path.stat().st_size}))


if __name__ == '__main__':
    main()
