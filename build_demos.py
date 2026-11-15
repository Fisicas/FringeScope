"""Generate local synthetic lessons and complete numerical provenance."""
from pathlib import Path
import json,platform,re
import numpy as np


def export_demonstrations(destination, data=None):
    from demo_model import build_demonstrations,metrics
    from demo_plots import draw,FILES
    from matplotlib.figure import Figure
    from matplotlib.backends.backend_agg import FigureCanvasAgg
    import matplotlib
    import branding
    root=Path(destination)
    if root.exists():raise FileExistsError('Preserve prior demonstration outputs: '+str(root))
    root.mkdir(parents=True)
    data=data if data is not None else build_demonstrations()
    record=metrics(data)
    record['application_version']=branding.VERSION
    record['versions']={'python':platform.python_version(),'numpy':np.__version__,'matplotlib':matplotlib.__version__}
    arrays={}
    def collect(prefix,value):
        if isinstance(value,np.ndarray):arrays[prefix]=value
        elif isinstance(value,dict):
            for key,item in value.items():collect(prefix+'__'+re.sub('[^a-zA-Z0-9]+','_',key),item)
    for key,value in data.items():collect(key,value)
    np.savez_compressed(root/'demonstration_arrays.npz',**arrays)
    (root/'metrics.json').write_text(json.dumps(record,indent=2,ensure_ascii=False),encoding='utf-8')
    np.savetxt(root/'reference_descending.csv',np.column_stack([data['nu'],data['s0'],data['reference_spectrum']]),delimiter=',',header='wavenumber_cm-1,ideal_reference_relative,biased_reference_relative')
    for i,name in enumerate(FILES):
        fig=Figure(figsize=(14,9),facecolor='white');FigureCanvasAgg(fig);draw(fig,data,i)
        fig.savefig(root/(name+'.png'),dpi=160,facecolor='white')
        fig.savefig(root/(name+'.svg'),facecolor='white')
        from ui_theme import style_figure
        style_figure(fig,'dark');fig.savefig(root/(name+'_dark.png'),dpi=160,facecolor=fig.get_facecolor())
    (root/'README.md').write_text('''# Original synthetic TRSS demonstrations

These figures are inspired by Rödig & Siebert (1999), DOI https://doi.org/10.1366/0003702991947595.
They do not reproduce that paper's experimental data or instrument. No measured arrays are included.
Exact settings, processing and assumptions are in metrics.json. Full numerical arrays are in demonstration_arrays.npz;
dictionary-valued data use double-underscore-separated array keys. Wavenumber is descending, time is in µs,
OPD is in cm, absorbance is in OD, and reference intensity is in relative units. Only the plotted AC detector
traces are divided by a single ideal IR IFG peak; no individual spectral/trace normalization or smoothing is applied.
The native 100 µs chemical spectrum is linearly interpolated between 99 and 105 µs bins. Graphical offsets
in the detector-trace figure are identified in its caption. No random noise is injected.

The baseline reference is stationary at the declared common bias; acquisition zero is not a laser flash.
The chemical example instead gates motion at the flash. Coaddition averages intensity before absorbance.
The exact cosine model assumes spatially uniform mirror displacement/coherent OPD phase and fixed-real readout.
The main app's OPD-dependent Taylor engine and magnitude readout are separate sensitivity models.
The electrical example retains an IR reference and assumes a ZPD-local coupling; it does not divide by a blocked beam.
All phase/frequency/harmonic examples are conditional mechanism illustrations, not instrument calibration.
''',encoding='utf-8')
    return root


def main():
    import matplotlib
    matplotlib.use('Agg')
    from ftir_sim import ROOT
    count=1
    while (ROOT/f'demonstrations_v{count:02}').exists():count+=1
    out=export_demonstrations(ROOT/f'demonstrations_v{count:02}')
    import shutil
    from demo_plots import FILES
    assets=ROOT/'demonstration_assets';assets.mkdir(exist_ok=True)
    for name in [*(item+'.png' for item in FILES),'metrics.json']:
        shutil.copyfile(out/name,assets/name)
    dark=ROOT/'demonstration_assets_dark';dark.mkdir(exist_ok=True)
    for name in FILES:shutil.copyfile(out/(name+'_dark.png'),dark/(name+'.png'))
    print(json.dumps({'output':str(out),'status':'generated'},indent=2))


if __name__=='__main__':main()
