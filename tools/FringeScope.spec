from pathlib import Path
REPO=Path(SPECPATH).parent
ROOT=REPO/'desktop'
folders=['assets','licenses','theory_assets','theory_assets_dark','evidence_assets','evidence_assets_dark','demonstration_assets','demonstration_assets_dark','model_assets','model_assets_dark']
files=['synthetic_model.json','waveform_defaults.json','release_config.json','THEORY.md','THEORY.html','REFERENCES.bib','MODEL_ASSUMPTIONS.md','TUTORIAL.md','THIRD_PARTY_NOTICES.md']
datas=[(str(ROOT/name),name) for name in folders]+[(str(ROOT/name),'.') for name in files]
datas += [(str(REPO/'docs'),'docs'),(str(REPO/'LICENSE'),'.'),(str(REPO/'CITATION.cff'),'.')]
a=Analysis([str(ROOT/'launch.pyw')],pathex=[str(ROOT)],datas=datas,
 hiddenimports=['app','bundle_selftest','matplotlib.backends.backend_qtagg','matplotlib.backends.backend_agg','PySide6.QtSvg'],
 excludes=['tkinter','torch','tensorflow','pandas','IPython','jupyter','notebook','pytest'],
 hooksconfig={'matplotlib':{'backends':['QtAgg','Agg']}},noarchive=False)
if any('windowsapps' in str(item[1]).lower() for item in a.binaries):
 raise RuntimeError('Refusing inherited desktop-tool DLLs in release bundle')
pyz=PYZ(a.pure)
exe=EXE(pyz,a.scripts,[],exclude_binaries=True,name='FringeScope',icon=str(ROOT/'assets/fringescope.ico'),console=False)
coll=COLLECT(exe,a.binaries,a.datas,name='FringeScope')
