"""Browser adapter for the unchanged FringeScope engine (runs under Pyodide).

Only presentation payloads are assembled here. Every simulated, fitted or
exported array comes from ftir_sim.simulate / fit_das / export_result, the same
functions the Windows application calls. The settings transformation mirrors
app.MainWindow.settings(); tests/test_web_edition.py checks that equivalence.
"""
from __future__ import annotations
from dataclasses import fields, replace, asdict
from pathlib import Path
import io, json, shutil, zipfile, tempfile
import numpy as np
import ftir_sim
from ftir_sim import Settings, simulate, fit_das, export_result, fold_display, laser_response, mirror_waveform

HERE = Path(__file__).resolve().parent
SOURCES = [('Mirror motion', 'wobble'), ('Globar leakage', 'globar'), ('532 nm actinic leakage', 'laser')]
SETTING_NAMES = {item.name for item in fields(Settings)}
INTEGER_CONTROLS = {'coadds', 'mains_harmonic'}
COMBO_CONTROLS = {'waveform', 'phase_mode', 'laser_route', 'electrical_mode', 'phase_readout'}
CHECK_CONTROLS = {'wobble', 'globar', 'laser', 'electrical', 'zpd'}
SPIN_DECIMALS = 12  # app.MainWindow.number(): QDoubleSpinBox.setDecimals(12)

_state = {}
_saved_session = None
_result_serial = 0


def _spin(value):
    """QDoubleSpinBox stores values rounded to its 12 displayed decimals."""
    return float(f'{float(value):.{SPIN_DECIMALS}f}')


def normalize_controls(controls):
    """Typed control values exactly as the desktop widgets would hold them."""
    out = {}
    for key, value in controls.items():
        if key in CHECK_CONTROLS or key == 'offset': out[key] = bool(value)
        elif key in COMBO_CONTROLS: out[key] = str(value)
        elif key in INTEGER_CONTROLS: out[key] = int(round(float(value)))
        else: out[key] = _spin(value)
    return out


def settings_from_controls(controls):
    """Mirror of app.MainWindow.settings() for a dict of desktop control values."""
    c = normalize_controls(controls)
    args = {key: value for key, value in c.items() if key in SETTING_NAMES}
    args.update(source='model', enabled=True, hene=False)
    args['coadds'] = int(args['coadds'])
    if not args['wobble']: args['bias_nm'] = 0.
    if c['electrical_mode'] == 'mains': args['electrical_frequency'] = 60*int(c['mains_harmonic'])
    return Settings(**args)


def fit_window(controls):
    c = normalize_controls(controls)
    return c['fit_start'], c['fit_stop'], c['fit_low'], c['fit_high'], c['offset']


def _limit(z):
    """plots.contour default: 98.5th percentile of |z| (µOD), at least 1."""
    return max(float(np.nanpercentile(np.abs(z), 98.5)), 1.)


def _summary(r, p, f, offset):
    active = [label for label, key in SOURCES if getattr(p, key)]
    active += ['Electrical pickup'] if p.electrical else []
    active += ['Return mismatch'] if p.zpd else []
    return dict(active=active, artifact_rms_full_uOD=r['artifact_rms_full_OD']*1e6,
                artifact_rms_roi_uOD=r['artifact_rms_OD']*1e6, taus=[float(v) for v in f['taus']],
                fit_rms_uOD=f['rms']*1e6, condition=f['condition'], fit_mode=f['fit_mode'], offset=bool(offset),
                converged=f['converged'], nfev=f['nfev'], warnings=list(r['warnings']), notes=list(f.get('notes', [])),
                laser_alias_cm1=r['laser_alias_cm1'], hene_alias_cm1=r['hene_alias_cm1'], dx_um=r['dx_um'],
                display_band_cm1=r['display_band_cm1'], settings=asdict(p), window=f['window'],
                laser_interferometric=bool(p.enabled and p.laser and p.laser_route == 'interferometric'))


def _f64(a):
    return np.ascontiguousarray(np.asarray(a, dtype='<f8'))


def compute(controls_json, free=False):
    """Simulate and fit; returns (meta_json, arrays) for the Explore view."""
    controls = json.loads(controls_json)
    p = settings_from_controls(controls)
    start, stop, low, high, offset = fit_window(controls)
    if free and _state.get('settings') == asdict(p):
        r = _state['result']  # Refit re-uses the displayed simulation, as on desktop.
    else:
        r = simulate(p)
    f = fit_das(r, p, bool(free), start, stop, low, high, offset)
    global _result_serial
    _result_serial += 1
    _state.update(result=r, fit=f, p=p, controls=normalize_controls(controls), settings=asdict(p), result_id=_result_serial)
    return _payload()


def _payload():
    r, f, p = _state["result"], _state["fit"], _state["p"]
    offset = _state["controls"]["offset"]
    v = r['valid']
    meta = _summary(r, p, f, offset)
    meta['result_id'] = _state['result_id']
    meta['contour_limit_uOD'] = _limit(r['ideal'][:, v]*1e6)
    arrays = dict(nu=_f64(r['nu']), t_us=_f64(r['t_us']), valid=_f64(v), ideal=_f64(r['ideal']), observed=_f64(r['observed']),
                  reconstruction=_f64(f['reconstruction']), das=_f64(f['das']), truth_das=_f64(r['truth_das']))
    return json.dumps(meta), arrays


def check_result(result_id):
    if result_id is None or result_id != _state.get('result_id'):
        raise ValueError('Displayed result no longer matches the engine; wait for calculation and retry')


def save_session(result_id):
    # Keep an exact tour snapshot; computations replace rather than mutate results.
    global _saved_session
    check_result(result_id)
    if _saved_session is not None: raise ValueError('A tour snapshot is already saved')
    _saved_session = dict(_state)
    return result_id


def restore_session():
    global _saved_session
    if _saved_session is None: raise ValueError('No tour snapshot is available')
    _state.clear(); _state.update(_saved_session); _saved_session = None
    return _state['result_id']


def view(name, params_json='{}'):
    """Arrays for one secondary view of the current result (plots.py semantics)."""
    r, f, p = _state['result'], _state['fit'], _state['p']
    q = json.loads(params_json)
    v = r['valid']; meta = {}
    if name == 'compare':
        scale = _limit(r['ideal'][:, v]*1e6)
        meta = dict(limits=[scale, scale, _limit(r['difference'][:, v]*1e6)])
        arrays = dict(difference=_f64(r['difference']))
    elif name == 'das':
        rms = np.sqrt(np.nanmean(f['residual'][:, v]**2, axis=1))*1e6
        traces = []
        for wn in [1559, 1570, 1697, 1748]:
            traces.append(int(np.argmin(abs(r['nu']-wn))))
        meta = dict(residual_limit=_limit(f['residual'][:, v]*1e6), trace_index=traces, fit_rms_uOD=f['rms']*1e6, condition=f['condition'])
        arrays = dict(residual=_f64(f['residual']), residual_rms_uOD=_f64(rms))
    elif name == 'optical':
        jl = int(np.argmin(abs(r['nu']-r['laser_alias_cm1'])))
        meta = dict(laser_index=jl)
        arrays = dict(s0=_f64(r['s0']), ref=_f64(r['ref']), folded_leak=_f64(r['folded_leak']),
                      laser_signal_spectrum=_f64(r['laser_signal_spectrum']), signal=_f64(r['signal']))
    elif name == 'interferograms':
        arrays = dict(x_um=_f64(np.fft.fftshift(r['x_cm'])*1e4), reference_ifg=_f64(np.fft.fftshift(r['reference_ifg'])),
                      signal_ifg=_f64(np.fft.fftshift(r['signal_ifg'], axes=-1)),
                      displacement_nm=_f64(r['displacement_cm'][:, [0, 1, 3]].T/2e-7), signal=_f64(r['signal']),
                      ref=_f64(r['ref']), s0=_f64(r['s0']))
    elif name == 'waveform':
        t = r['t_us']; gate = (t >= 0)
        drive = mirror_waveform(t, p).reshape(-1)*p.mirror_nm*gate
        meta = dict(frequency_hz=p.frequency_hz, cycles=p.frequency_hz*3.378e-3)
        arrays = dict(drive_nm=_f64(drive), difference=_f64(r['difference']))
    elif name == 'optics':
        vv = np.linspace(0, 22000, 5000)
        early = np.linspace(-.03, max(1., 6*p.response_us), 3000)
        kt = (r['t_us'] >= -p.dt_us) & (r['t_us'] <= max(20, 6*p.response_us))
        ns = np.linspace(-10, 120, 1600)
        meta = dict(fold_width=p.fold_width, laser_nm=p.laser_nm, laser_cm1=1e7/p.laser_nm, dt_us=p.dt_us)
        arrays = dict(leak_nu=_f64(r['leak_nu']), leak_source=_f64(r['leak_source']), fold_v=_f64(vv), fold_alias=_f64(fold_display(vv, p.fold_width)),
                      s0=_f64(r['s0']), folded_leak=_f64(r['folded_leak']), early_us=_f64(early), early_response=_f64(laser_response(early, p)),
                      bin_t=_f64(r['t_us'][kt]), bin_response=_f64(r['laser_response'][kt]), inset_ns=_f64(ns),
                      inset_response=_f64(laser_response(ns*1e-3, replace(p, response_us=0))*1e-3))
    else:
        raise ValueError(f'Unknown view {name!r}')
    return json.dumps(meta), arrays


def export_zip(info_json, figures=None):
    """Desktop export_result + DAS/analysis/provenance files, returned as ZIP bytes."""
    info = json.loads(info_json)
    check_result(info.get('expected_result_id'))
    r, f, p, c = _state['result'], _state['fit'], _state['p'], _state['controls']
    name = 'FringeScope_run_'+info['stamp']
    with tempfile.TemporaryDirectory(prefix='fringescope-export-') as scratch:
        return _write_export(info, figures, Path(scratch))


def _write_export(info, figures, work):
    r, f, p, c = _state['result'], _state['fit'], _state['p'], _state['controls']
    name = 'FringeScope_run_'+info['stamp']
    dest = export_result(r, work/name)
    np.savetxt(dest/'DAS_and_offset.csv', np.column_stack([r['nu'], f['das'].T]), delimiter=',',
               header='wavenumber_cm-1,heating_OD,recombination_OD'+(',offset_OD' if len(f['das']) > 2 else ''))
    metadata = {key: value for key, value in f.items() if not isinstance(value, np.ndarray)}
    j = int(np.argmin(abs(r['nu']-info['wavenumber'])))
    metadata.update(taus_us=f['taus'].tolist(), selected_time_us=info['time_us'], requested_wavenumber_cm1=info['wavenumber'],
        actual_wavenumber_cm1=float(r['nu'][j]),
        selection_processing='Contour/slider snap to native bins. Numeric off-grid times use linear interpolation.',
        electrical_frequency_mode=c['electrical_mode'], mains_harmonic=int(c['mains_harmonic']),
        application_version=info['version'], application_edition='FringeScope Web (browser preview)', appearance=info['theme'],
        committed_result_id=_state['result_id'], selected_view=info.get('view'), browser_runtime=info.get('runtime'), kernel_files_sha256=info.get('kernel_sha256'),
        screen_figures='PNG captures of the panels shown in the browser; numerical data are in simulation.npz and the CSV/DPT files.')
    (dest/'analysis_settings.json').write_text(json.dumps(metadata, indent=2), encoding='utf-8')
    for fname in ['THEORY.md', 'REFERENCES.bib', 'synthetic_model.json', 'MODEL_ASSUMPTIONS.md']:
        source = HERE/fname
        if source.exists(): (dest/fname).write_bytes(source.read_bytes())
    if isinstance(figures, str):  # worker passes a folder of PNG captures
        figures = {path.name: path.read_bytes() for path in sorted(Path(figures).glob('*.png'))}
    for fname, data in (figures or {}).items():
        (dest/Path(fname).name).write_bytes(bytes(data))
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, 'w', zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(dest.rglob('*')):
            if path.is_file(): archive.write(path, path.relative_to(work).as_posix())
    return name+'.zip', buffer.getvalue()


def runtime_versions():
    import sys, scipy
    return json.dumps(dict(python=sys.version.split()[0], numpy=np.__version__, scipy=scipy.__version__,
                           public_mode=ftir_sim.public_mode()))
