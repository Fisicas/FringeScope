"""Regressions for committed exports, reversible fitted sessions and small windows."""
import os,sys,json,io,zipfile
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
from pathlib import Path
import numpy as np
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'web'))
import web_kernel as k
from test_web_edition import default_state


def info(result_id):
    return dict(expected_result_id=result_id,stamp='20261115_120000_000001',wavenumber=1697,time_us=100,
                version='0.11.0',theme='dark',view='explore',runtime={},kernel_sha256={})


def test_export_rejects_a_stale_displayed_result(tmp_path,monkeypatch):
    monkeypatch.setattr(k.tempfile,"tempdir",str(tmp_path))
    old,_=k.compute(json.dumps(default_state()));old=json.loads(old)
    settings=default_state();settings['wobble']=True
    current,_=k.compute(json.dumps(settings));current=json.loads(current)
    with pytest.raises(ValueError,match='no longer matches'):k.export_zip(json.dumps(info(old['result_id'])))
    with pytest.raises(ValueError):k.export_zip(json.dumps(dict(info(None))))
    _,data=k.export_zip(json.dumps(info(current['result_id'])))
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        settings=json.loads(z.read(next(n for n in z.namelist() if n.endswith('settings_and_provenance.json'))))
        meta=json.loads(z.read(next(n for n in z.namelist() if n.endswith('analysis_settings.json'))))
        assert settings['settings']['wobble'] and meta['committed_result_id']==current['result_id']


def test_unique_export_scratch_preserves_existing_output_and_cleans_on_failure(tmp_path,monkeypatch):
    monkeypatch.setattr(k.tempfile,'tempdir',str(tmp_path))
    previous=tmp_path/'fringescope_export';previous.mkdir();sentinel=previous/'keep.txt';sentinel.write_text('user output')
    meta,_=k.compute(json.dumps(default_state()));request=json.dumps(info(json.loads(meta)['result_id']))
    k.export_zip(request);k.export_zip(request)
    assert sentinel.read_text()=='user output' and not list(tmp_path.glob('fringescope-export-*'))
    def fail(*args):raise RuntimeError('simulated write failure')
    monkeypatch.setattr(k,'export_result',fail)
    with pytest.raises(RuntimeError,match='simulated'):k.export_zip(request)
    assert sentinel.read_text()=='user output' and not list(tmp_path.glob('fringescope-export-*'))


def test_browser_session_restores_the_exact_free_fit():
    controls=default_state();controls['wobble']=True
    before,arrays=k.compute(json.dumps(controls),True);before=json.loads(before)
    saved={name:a.copy() for name,a in arrays.items()}
    k.save_session(before['result_id'])
    try:
        k.compute(json.dumps(default_state()))
        assert k.restore_session()==before['result_id']
        after,restored=k._payload();after=json.loads(after)
        assert after['fit_mode']==before['fit_mode'] and after['taus']==before['taus']
        for name,a in saved.items():np.testing.assert_array_equal(restored[name],a)
    finally:
        if k._saved_session is not None:k.restore_session()


def test_desktop_tour_restores_fit_after_timer_events():
    from PySide6 import QtWidgets as Q,QtTest
    import app as desktop
    application=Q.QApplication.instance() or Q.QApplication([]);w=desktop.MainWindow()
    try:
        w.set_control('wobble',True);w.recompute();w.refit()
        fit=w.fit;expected=fit['das'].copy();reconstruction=fit['reconstruction'].copy()
        w.goto_tour_step(0);w.goto_tour_step(1);w.end_tour(False);QtTest.QTest.qWait(350)
        assert w.fit is fit and w.fit['fit_mode'].startswith('free')
        np.testing.assert_array_equal(w.fit['das'],expected)
        np.testing.assert_array_equal(w.fit['reconstruction'],reconstruction)
    finally:w.close();w.deleteLater();application.processEvents()


def test_desktop_short_window_scrolls_plots_instead_of_crushing_them():
    from PySide6 import QtWidgets as Q,QtTest
    import app as desktop
    application=Q.QApplication.instance() or Q.QApplication([]);w=desktop.MainWindow()
    try:
        w.resize(1280,640);w.show();QtTest.QTest.qWait(250)
        assert w.height()<=640
        page=w.pages['Explore']
        assert page.canvas.height()>=520 and page.plot_scroll.verticalScrollBar().maximum()>0
    finally:w.close();w.deleteLater();application.processEvents()
