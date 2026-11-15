"""Web edition contract: same controls, same settings transformation, same engine."""
import os, sys, json, random, hashlib, re
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
from dataclasses import asdict
from pathlib import Path
import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT/'web'
DESKTOP = ROOT/'desktop'
sys.path.insert(0, str(WEB))
import web_kernel  # noqa: E402

SPEC = json.loads((WEB/'src'/'controls.json').read_text(encoding='utf-8'))


def spec_controls():
    out = {}
    def walk(section):
        for c in section.get('controls', []): out[c['key']] = c
        for d in section.get('details', []) + section.get('subsections', []): walk(d)
    for s in SPEC['sections']: walk(s)
    return out


def spec_toggles():
    keys = []
    def walk(section):
        if section.get('toggle'): keys.append(section['toggle'])
        for d in section.get('details', []) + section.get('subsections', []): walk(d)
    for s in SPEC['sections']: walk(s)
    return keys


def default_state():
    state = {k: c['value'] for k, c in spec_controls().items()}
    state.update({k: False for k in spec_toggles()})
    return state


@pytest.fixture(scope='module')
def window():
    from PySide6 import QtWidgets as Q
    app = Q.QApplication.instance() or Q.QApplication([])
    import app as desktop
    w = desktop.MainWindow()
    yield w
    w.updates.stop() if hasattr(w.updates, 'stop') else None
    w.close(); w.deleteLater(); app.processEvents()


def test_web_controls_match_desktop_widgets(window):
    from PySide6 import QtWidgets as Q
    spec = spec_controls()
    desktop = set(window.controls)
    assert desktop == (set(spec)-{'offset'})|set(spec_toggles())
    for key, c in spec.items():
        if key == 'offset':
            assert window.offset.isChecked() is c['value']; continue
        w = window.controls[key]
        if c['type'] == 'select':
            assert isinstance(w, Q.QComboBox)
            items = [[w.itemData(i), w.itemText(i)] for i in range(w.count())]
            assert items == c['items'], key
            assert w.currentData() == c['value'], key
        else:
            assert isinstance(w, Q.QSpinBox if c['type'] == 'integer' else Q.QDoubleSpinBox), key
            assert w.value() == pytest.approx(web_kernel._spin(c['value']), abs=0), key
            assert (w.minimum(), w.maximum(), w.singleStep()) == pytest.approx((c['min'], c['max'], c['step']), rel=1e-12), key
    for key in spec_toggles():
        assert window.controls[key].isChecked() is False


def _apply(window, state):
    for key, value in state.items():
        if key == 'offset': window.offset.setChecked(value)
        else: window.set_control(key, value)


def test_settings_transformation_matches_desktop(window):
    rng = random.Random(20261115)
    spec = spec_controls()
    states = [default_state()]
    for _ in range(40):
        s = default_state()
        for key in spec_toggles(): s[key] = rng.random() < .5
        for key, c in spec.items():
            if rng.random() < .5: continue
            if c['type'] == 'select': s[key] = rng.choice(c['items'])[0]
            elif c['type'] == 'checkbox': s[key] = rng.random() < .5
            elif c['type'] == 'integer': s[key] = rng.randint(c['min'], c['max'])
            else: s[key] = rng.uniform(c['min'], c['max'])
        states.append(s)
    for s in states:
        _apply(window, s)
        expected = asdict(window.settings())
        got = asdict(web_kernel.settings_from_controls(s))
        assert got == expected
        fit = (window.controls['fit_start'].value(), window.controls['fit_stop'].value(),
               window.controls['fit_low'].value(), window.controls['fit_high'].value(), window.offset.isChecked())
        assert web_kernel.fit_window(s) == fit
    _apply(window, default_state())


# The tour as first released (forward sequence in app.advance_tour); the shared tour.py must reproduce it.
LEGACY_TOUR = [{}, {'wobble': True, 'mirror_nm': 2, 'frequency_hz': 840, 'bias_nm': 25, 'phase_deg': -100, 'waveform': 'sine', 'coadds': 1, 'phase_mode': 'locked'},
               {'globar': True, 'globar_fraction': .1, 'blocking_od': 0, 'leak_transient_ppm': 0},
               {'laser': True, 'laser_route': 'interferometric', 'laser_area_us': 2e-6, 'laser_blocking_od': 0}]


def test_tour_steps_are_shared_and_reversible(window):
    """Desktop tour panel, the web replica (explore.js applyTourStep) and the original forward sequence agree."""
    import tour
    from ftir_sim import Settings
    defaults = asdict(Settings())
    before = {key: window.value(w) for key, w in window.controls.items()}, window.wn.value(), window.time.value()
    legacy = default_state(); legacy.update({key: defaults[key] for key in legacy if key in defaults}); legacy.update(tour.BASE)
    try:
        for k, step in enumerate(tour.STEPS):
            window.goto_tour_step(k)
            web = default_state(); web.update({key: defaults[key] for key in web if key in defaults}); web.update(tour.step_controls(k))
            legacy.update({key: False for key in tour.OFF}); legacy.update(LEGACY_TOUR[k])
            got = asdict(window.settings())
            assert got == asdict(web_kernel.settings_from_controls(web)) == asdict(web_kernel.settings_from_controls(legacy)), k
            assert web_kernel.fit_window(web) == (window.controls['fit_start'].value(), window.controls['fit_stop'].value(),
                                                  window.controls['fit_low'].value(), window.controls['fit_high'].value(), window.offset.isChecked())
            assert window.time.value() == step['time_us'] and window.left.currentWidget() is window.tour_scroll
            assert window.tour_panel.title.text() == step['title'] and window.tour_panel.items.count() == len(step['look'])
            if step['alias']: assert window.wn.value() == pytest.approx(window.result['laser_alias_cm1'])
        window.goto_tour_step(1)  # Back from the last step replays the same state as going forward.
        assert asdict(window.settings())['wobble'] and not asdict(window.settings())['laser']
        window.tour_panel.next.click(); window.tour_panel.next.click(); window.tour_panel.next.click()  # step 4, then Finish
        assert window.tour_step == -1 and window.left.currentWidget() is window.scroll
        assert ({key: window.value(w) for key, w in window.controls.items()}, window.wn.value(), window.time.value()) == before
    finally:
        if window.tour_step >= 0: window.end_tour(False)
        _apply(window, default_state())


def test_web_explore_payload_equals_desktop_calls():
    from ftir_sim import simulate, fit_das
    s = default_state(); s.update(wobble=True, globar=True)
    meta, arrays = web_kernel.compute(json.dumps(s))
    meta = json.loads(meta)
    p = web_kernel.settings_from_controls(s)
    r = simulate(p); f = fit_das(r, p, False, *web_kernel.fit_window(s))
    np.testing.assert_array_equal(arrays['observed'], r['observed'])
    np.testing.assert_array_equal(arrays['reconstruction'], f['reconstruction'])
    assert arrays['nu'][0] > arrays['nu'][-1] and len(arrays['nu']) == 513
    assert arrays['observed'].dtype == np.float64 and arrays['observed'].flags.c_contiguous
    assert meta['active'] == ['Mirror motion', 'Globar leakage']
    for name in ['compare', 'das', 'optical', 'interferograms', 'waveform', 'optics']:
        vmeta, varrays = web_kernel.view(name)
        json.loads(vmeta)
        assert all(a.dtype == np.float64 for a in varrays.values()), name
    meta2, arrays2 = web_kernel.compute(json.dumps(s), free=True)
    f2 = fit_das(r, p, True, *web_kernel.fit_window(s))
    np.testing.assert_allclose(json.loads(meta2)['taus'], f2['taus'], rtol=0, atol=0)


def test_web_export_zip_contains_desktop_files(tmp_path,monkeypatch):
    monkeypatch.setattr(web_kernel.tempfile,"tempdir",str(tmp_path))
    import zipfile, io
    metadata, _ = web_kernel.compute(json.dumps(default_state()))
    info = dict(expected_result_id=json.loads(metadata)["result_id"], stamp='20261115_120000_000000', wavenumber=1697, time_us=100, version='0.11.0', theme='dark', view='Explore',
                runtime={'python': 'test'}, kernel_sha256={})
    name, data = web_kernel.export_zip(json.dumps(info), {'screen_contour.png': b'\x89PNG'})
    names = zipfile.ZipFile(io.BytesIO(data)).namelist()
    root = name[:-4]+'/'
    for expected in ['simulation.npz', 'simulated_descending.dpt', 'time_us.csv', 'exported_spectral_mask.csv',
                     'settings_and_provenance.json', 'DAS_and_offset.csv', 'analysis_settings.json', 'screen_contour.png']:
        assert root+expected in names


def test_static_site_build_is_complete_and_engine_files_are_identical(tmp_path, monkeypatch):
    import build_web
    from dataclasses import asdict as _asdict
    from ftir_sim import Settings
    monkeypatch.setattr(build_web, 'SITE', tmp_path/'site')
    build_web.main()
    site = tmp_path/'site'
    manifest = json.loads((site/'build_manifest.json').read_text(encoding='utf-8'))
    for name in ['ftir_sim.py', 'synthetic_model.json', 'release_config.json', 'THEORY.md', 'REFERENCES.bib', 'MODEL_ASSUMPTIONS.md']:
        assert (site/'py'/name).read_bytes() == (DESKTOP/name).read_bytes(), name
        assert manifest['kernel_sources'][name] == hashlib.sha256((DESKTOP/name).read_bytes()).hexdigest()
    assert (site/'py'/'web_kernel.py').read_bytes() == (WEB/'web_kernel.py').read_bytes()
    assert json.loads((site/'py'/'release_config.json').read_text(encoding='utf-8'))['public_mode'] is True
    pages = ['index.html', 'demonstrations.html', 'theory.html', 'tutorial.html', 'cite.html', 'validate.html', '404.html']
    for page in pages:
        text = (site/page).read_text(encoding='utf-8')
        assert '<meta name="viewport"' in text and 'All displayed spectra are simulated' in text
        for ref in re.findall(r'(?:src|href)="([^"#:]+)(?:\?[^"]*)?(?:#[^"]*)?"', text):
            assert (site/ref.split('?')[0]).exists(), f'{page} -> {ref}'
        for anchor in re.findall(r'href="#([^"]+)"', text):
            assert f'id="{anchor}"' in text, f'{page} -> #{anchor}'
    theory = (site/'theory.html').read_text(encoding='utf-8')
    assert theory.count('class="equation"') == 15 and theory.count('<figure class="fig">') == 6
    # Every equation and figure has a text alternative.
    assert not re.search(r'<img(?![^>]*\balt=")[^>]*>', theory)
    # The guided tour is reachable from the theory and tutorial pages, one deep link per step.
    import tour
    targets = {'contour', 'spectrum', 'kinetics', 'das', 'o0', 'o1', 'o2', 'o3'} | {'source:'+k for k in spec_toggles()}
    assert all(t in targets for step in tour.STEPS for t, _ in step['look'])
    assert all(key in spec_controls() or key in spec_toggles() for step in tour.STEPS for key in step['controls'])
    assert 'href="index.html#tour"' in theory
    tutorial = (site/'tutorial.html').read_text(encoding='utf-8')
    for n in range(1, len(tour.STEPS)+1): assert f'href="index.html#tour-{n}"' in tutorial
    config = json.loads(re.search(r'<script id="fs-config" type="application/json">(.*?)</script>', (site/'index.html').read_text(encoding='utf-8'), re.S)[1])
    assert config['settings_defaults'] == _asdict(Settings())
    assert config['tour'] == json.loads(json.dumps(tour.as_json()))
    assert config['manifest']['kernel'] == {k: v for k, v in manifest['kernel_sources'].items()}
