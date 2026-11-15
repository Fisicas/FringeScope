"""Reproducible internal CW comparison for the theory, not an app control."""
from dataclasses import replace
import json,platform
import numpy as np
import matplotlib
matplotlib.use('Agg')
from matplotlib.figure import Figure
from matplotlib.backends.backend_agg import FigureCanvasAgg
from ftir_sim import ROOT,Settings,simulate
from display_format import ReadableScalarFormatter


def main():
    folder=ROOT/'evidence_assets';folder.mkdir(exist_ok=True)
    p=Settings();clean=simulate(p);steady=simulate(replace(p,hene=True))
    empty=simulate(replace(p,hene=True,heat_scale=0,rp_scale=0,offset_scale=0))
    mirror=simulate(replace(p,wobble=True,bias_nm=25))
    combined=simulate(replace(p,wobble=True,bias_nm=25,hene=True))
    roi=(clean['nu']>=1200)&(clean['nu']<=1900)
    steady_error=steady['observed']-clean['observed']
    motion_increment=combined['observed']-mirror['observed']
    assert np.nanmax(abs(empty['observed']))<1e-12
    assert np.sqrt(np.nanmean(steady_error**2))<1e-8
    records={'purpose':'Steady-CW cancellation and a conditional motion counterexample; not instrument measurements',
        'CW_zero_chemistry_max_abs_OD':float(np.nanmax(abs(empty['observed']))),
        'CW_full_band_rms_uOD':float(np.sqrt(np.nanmean(steady_error**2))*1e6),
        'CW_max_ROI_uOD':float(np.nanmax(abs(steady_error[:,roi]))*1e6),
        'CW_motion_increment_full_rms_uOD':float(np.sqrt(np.nanmean(motion_increment**2))*1e6),
        'CW_motion_increment_ROI_rms_uOD':float(np.sqrt(np.nanmean(motion_increment[:,roi]**2))*1e6),
        'CW_settings':steady['settings'],'motion_settings':combined['settings'],
        'spectral_axis':'descending','ROI_cm1':[1200,1900],
        'processing':'Maximum absolute difference over native time bins; no smoothing or normalization.',
        'versions':{'python':platform.python_version(),'numpy':np.__version__,'matplotlib':matplotlib.__version__}}
    fig=Figure(figsize=(11,6.8),layout='constrained');FigureCanvasAgg(fig);axes=fig.subplots(2,1)
    for ax,values,color,title in [
        (axes[0],steady_error,'#315c91','Steady CW: increment relative to artifact-free PSI ΔA'),
        (axes[1],motion_increment,'#b74e3e','Conditional counterexample: extra change when CW light follows mirror motion')]:
        ax.plot(clean['nu'],np.nanmax(abs(values),axis=0)*1e6,color=color,lw=1.4)
        ax.set_xlim(float(clean['nu'].max()),float(clean['nu'].min()))
        ax.set_title(title,loc='left',fontsize=11)
        ax.set_xlabel('Wavenumber (cm⁻¹)');ax.set_ylabel('Maximum |increment| (µOD)')
        ax.xaxis.set_major_formatter(ReadableScalarFormatter());ax.yaxis.set_major_formatter(ReadableScalarFormatter())
        ax.grid(alpha=.18);ax.spines[['top','right']].set_visible(False)
    fig.savefig(folder/'hene_cancellation.png',dpi=180,facecolor='white')
    from ui_theme import style_figure
    style_figure(fig,'dark');dark=ROOT/'evidence_assets_dark';dark.mkdir(exist_ok=True)
    fig.savefig(dark/'hene_cancellation.png',dpi=180,facecolor=fig.get_facecolor())
    (folder/'hene_comparison.json').write_text(json.dumps(records,indent=2),encoding='utf-8')
    print(json.dumps({key:value for key,value in records.items() if key.endswith(('OD','uOD'))},indent=2))


if __name__=='__main__':main()
