"""Exercise the real UI/assets/exports in a source or frozen installation."""
from pathlib import Path
import json,sys,os

def run(application,w,destination):
    from PySide6 import QtTest
    from unittest.mock import patch
    import numpy as np
    import branding,updater
    root=Path(destination);root.mkdir(parents=True,exist_ok=True)
    assert w.result['artifact_rms_full_OD']<1e-12
    w.tabs.setCurrentWidget(w.theory_page)
    for _ in range(100):
        QtTest.QTest.qWait(50)
        if w.theory_page.reader.toHtml().count('<img')==21:break
    assert w.theory_page.reader.toHtml().count('<img')==21
    w.grab().save(str(root/'theory_dark.png'))
    w.appearance.setCurrentIndex(1);application.processEvents()
    w.grab().save(str(root/'theory_light.png'))
    w.tabs.setCurrentWidget(w.pages['Demonstrations']);application.processEvents()
    assert w.demo_data is not None
    w.tabs.setCurrentWidget(w.pages['Explore'])
    w.set_control('wobble',True);w.recompute();w.refit()
    saved_fit=w.fit;taus=saved_fit['taus'].copy();das=saved_fit['das'].copy()
    w.tour_button.click();application.processEvents();assert w.tour_step==0
    for _ in range(4):w.tour_panel.next.click();application.processEvents()
    assert w.tour_step==-1 and w.left.currentWidget() is w.scroll
    assert w.fit is saved_fit and np.array_equal(w.fit['taus'],taus) and np.array_equal(w.fit['das'],das)
    w.reset_ideal();w.resize(1280,640);QtTest.QTest.qWait(180)
    assert w.height()<=640 and w.pages['Explore'].plot_scroll.verticalScrollBar().maximum()>0
    w.grab().save(str(root/'short_window.png'))
    with patch('PySide6.QtWidgets.QFileDialog.getExistingDirectory',return_value=str(root)):w.export()
    run_dir=next(root.glob('FringeScope_run_*'))
    values=np.loadtxt(run_dir/'simulated_descending.dpt',delimiter=',')
    assert np.isfinite(values).all() and np.all(np.diff(values[:,0])<0)
    assert not updater.enabled()
    record={'status':'passed','version':branding.VERSION,'frozen':bool(getattr(sys,'frozen',False)),
        'executable':sys.executable,'resource_root':str(branding.ROOT),'cwd':os.getcwd(),
        'installed':updater.install_dir() is not None,'updates_enabled':False,
        'checks':['early Qt startup and synthetic default','21 offline equation/figure assets in both themes','fixed demonstrations','exact free-fit tour restoration','short-window scrollable plots','finite descending export in writable user-selected directory']}
    (root/'checks.json').write_text(json.dumps(record,indent=2),encoding='utf-8')
