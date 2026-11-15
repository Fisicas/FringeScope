"""Plots shared by the desktop screen and reproducible example figures."""
import numpy as np
from display_format import number as display_number,ReadableScalarFormatter

IDEAL='#278b72';SIM='#d65d3f';HEAT='#268bd2';RP='#df8a25'

def clean(ax,title='',spectral=False,ylabel=None):
    ax.set_title(title,loc='left',fontsize=10,fontweight='bold',pad=10)
    ax.grid(alpha=.15)
    ax.spines[['top','right']].set_visible(False)
    ax.tick_params(labelsize=8)
    ax.xaxis.set_major_formatter(ReadableScalarFormatter());ax.yaxis.set_major_formatter(ReadableScalarFormatter())
    if spectral:ax.set_xlabel('Wavenumber (cm⁻¹)',fontsize=9)
    if ylabel:ax.set_ylabel(ylabel,fontsize=9)

def spectral_bounds(r):
    return float(np.max(r['nu'])),float(np.min(r['nu']))


def contour(ax,r,key,title,lo=None,hi=None,limit=None):
    full_hi,full_lo=spectral_bounds(r)
    lo=full_lo if lo is None else lo;hi=full_hi if hi is None else hi
    nu,t=r['nu'],r['t_us'];keep=(nu>=lo)&(nu<=hi)&r['valid']
    z=r[key][:,keep]*1e6
    if limit is None:limit=max(float(np.nanpercentile(np.abs(z),98.5)),1.)
    image=ax.pcolormesh(nu[keep],t,z,cmap='RdBu_r',vmin=-limit,vmax=limit,shading='auto',rasterized=True)
    ax.axhline(0,color='k',lw=.5,alpha=.4)
    clean(ax,title,True,'Time after flash (µs)');ax.set_xlim(hi,lo)
    return image

def overview(fig,r,p,fit,time_index=42,wavenumber=1697.,average=None,time_us=100.,high=None,low=None):
    full_hi,full_lo=spectral_bounds(r)
    high=full_hi if high is None else high;low=full_lo if low is None else low
    fig.clear();axs=fig.subplots(2,2)
    reference_scale=max(float(np.nanpercentile(abs(r['ideal'][:,r['valid']]*1e6),98.5)),1.)
    image=contour(axs[0,0],r,'observed','ΔA · clean-reference color scale',hi=high,lo=low,limit=reference_scale)
    fig.colorbar(image,ax=axs[0,0],label='µOD',pad=.02,extend='both')
    spectral_plot(axs[0,1],r,time_index,average,time_us)
    axs[0,1].set_xlim(high,low)
    j=int(np.argmin(np.abs(r['nu']-wavenumber)))
    ax=axs[1,0]
    ax.plot(r['t_us'],r['ideal'][:,j]*1e6,color=IDEAL,lw=2,label='Artifact-free PSI ΔA')
    ax.plot(r['t_us'],r['observed'][:,j]*1e6,color=SIM,lw=1.1,label='Effects applied')
    if fit is not None:ax.plot(r['t_us'],fit['reconstruction'][:,j]*1e6,color='#303945',ls='--',lw=1,label='2exp + offset projection')
    ax.axvline(0,color='k',lw=.6,alpha=.4)
    clean(ax,f'Kinetics · {display_number(r["nu"][j])} cm⁻¹',ylabel='ΔA (µOD)')
    ax.set_xlabel('Time after flash (µs)');ax.legend(fontsize=7)
    das_plot(axs[1,1],r,fit)
    axs[1,1].set_xlim(high,low)
    compact=fig.bbox.width<1050
    fig.subplots_adjust(left=.105 if compact else .07,right=.98,bottom=.11 if compact else .09,top=.94,wspace=.37 if compact else .27,hspace=.52 if compact else .42)
    actual=float(r['nu'][j])
    guides={'nu':axs[0,0].axvline(actual,color='#f2b24c',lw=1,ls='--'),
            'time':axs[0,0].axhline(time_us,color='#f2b24c',lw=1,ls='--'),
            'spectrum':axs[0,1].axvline(actual,color='#f2b24c',lw=.8,ls=':'),
            'kinetics':axs[1,0].axvline(time_us,color='#f2b24c',lw=.8,ls=':'),
            'das':axs[1,1].axvline(actual,color='#f2b24c',lw=.8,ls=':')}
    return {'axes':dict(zip(['contour','spectrum','kinetics','das'],axs.flat)),
            'spectrum_lines':axs[0,1].lines[:2],'kinetics_lines':axs[1,0].lines[:2],
            'fit_line':axs[1,0].lines[2] if fit is not None else None,'guides':guides}


def selected_spectrum(result,key,time_us):
    t=result['t_us'];k=int(np.clip(np.searchsorted(t,time_us),1,len(t)-1))
    fraction=(time_us-t[k-1])/(t[k]-t[k-1])
    return (1-fraction)*result[key][k-1]+fraction*result[key][k]


def update_overview(handles,result,fit,wavenumber,time_us):
    """Update linked artists in place: keep zoom, contour scale and toolbar state."""
    j=int(np.argmin(abs(result['nu']-wavenumber)));actual=float(result['nu'][j])
    for line,key in zip(handles['spectrum_lines'],['ideal','observed']):line.set_ydata(selected_spectrum(result,key,time_us)*1e6)
    for line,key in zip(handles['kinetics_lines'],['ideal','observed']):line.set_ydata(result[key][:,j]*1e6)
    if handles['fit_line'] is not None:handles['fit_line'].set_ydata(fit['reconstruction'][:,j]*1e6)
    native=np.min(abs(result['t_us']-time_us))<1e-8
    font_size=9 if handles['axes']['spectrum'].figure.bbox.width<1050 else 10
    handles['axes']['spectrum'].set_title(f'Spectrum · {time_us:.1f} µs'+('' if native else ' (interpolated)'),loc='left',fontsize=font_size,fontweight='bold',pad=10)
    handles['axes']['kinetics'].set_title(f'Kinetics · {display_number(actual)} cm⁻¹',loc='left',fontsize=font_size,fontweight='bold',pad=10)
    for key in ['nu','spectrum','das']:handles['guides'][key].set_xdata([actual,actual])
    handles['guides']['time'].set_ydata([time_us,time_us]);handles['guides']['kinetics'].set_xdata([time_us,time_us])

def spectral_plot(ax,r,index=42,average=None,time_us=100.):
    index=int(np.clip(index,0,len(r['t_us'])-1))
    if average is not None:
        kt=(r['t_us']>=average[0])&(r['t_us']<=average[1])
        if not kt.any():kt[index]=True
        a=np.nanmean(r['ideal'][kt][:,r['valid']],axis=0);b=np.nanmean(r['observed'][kt][:,r['valid']],axis=0)
        nu=r['nu'][r['valid']]
        title=f'Mean spectrum · {r["t_us"][kt][0]:.0f} to {r["t_us"][kt][-1]:.0f} µs ({kt.sum()} bins)'
    else:
        nu=r['nu'];t=r['t_us'];q=float(t[index]) if time_us is None else float(time_us)
        k=int(np.clip(np.searchsorted(t,q),1,len(t)-1));fraction=(q-t[k-1])/(t[k]-t[k-1])
        a=(1-fraction)*r['ideal'][k-1]+fraction*r['ideal'][k]
        b=(1-fraction)*r['observed'][k-1]+fraction*r['observed'][k]
        title=f'Spectrum · {q:.1f} µs'
        if 1e-8<fraction<1-1e-8:title+=' (interpolated)'
    ax.plot(nu,a*1e6,color=IDEAL,lw=2,label='Artifact-free PSI ΔA')
    ax.plot(nu,b*1e6,color=SIM,lw=1,label='Effects applied')
    ax.axhline(0,color='k',lw=.5,alpha=.4)
    clean(ax,title,True,'ΔA (µOD)');ax.legend(fontsize=7)
    ax.set_xlim(*spectral_bounds(r))
    cfg=r.get('settings',{})
    if cfg.get('enabled') and cfg.get('laser') and cfg.get('laser_route')=='interferometric':
        ax.axvline(r['laser_alias_cm1'],ls=':',lw=1,color='#6c6175')
        ax.text(r['laser_alias_cm1']-4,.03,'Laser alias',transform=ax.get_xaxis_transform(),rotation=90,fontsize=7,va='bottom',color='#6c6175')

def das_plot(ax,r,fit):
    if r.get('truth_das') is not None:
        for i,c in enumerate([HEAT,RP]):ax.plot(r['nu'],r['truth_das'][i]*1e6,color=c,lw=2,alpha=.5,label=['Input heating-like DAS','Input recombination DAS'][i])
        if len(r['truth_das'])>2:ax.plot(r['nu'],r['truth_das'][2]*1e6,color='#79627e',lw=2,alpha=.6,label='Unresolved residual + heating-like offset')
    if fit is not None:
        for i,c in enumerate([HEAT,RP]):ax.plot(r['nu'],fit['das'][i]*1e6,color=c,lw=1,ls='--',label=f'Projected {fit["taus"][i]:.2f} µs')
        if len(fit['das'])>2:ax.plot(r['nu'],fit['das'][2]*1e6,color='gray',lw=1,label='Fitted constant')
    ax.axhline(0,color='k',lw=.5,alpha=.4)
    clean(ax,'DAS and offset · signed amplitudes',True,'Amplitude at t = 0 (µOD)')
    ax.set_xlim(*spectral_bounds(r))
    ax.legend(fontsize=7,ncol=2)

def contours(fig,r):
    fig.clear();axs=fig.subplots(1,3)
    scale=max(np.nanpercentile(np.abs(r['ideal'][:,r['valid']]*1e6),98.5),1.)
    for ax,key,title,limit in zip(axs,['ideal','observed','difference'],['Clean reference','Effects applied · same scale','Artifact · own color scale'],[scale,scale,None]):
        im=contour(ax,r,key,title,limit=limit)
        fig.colorbar(im,ax=ax,label='µOD',pad=.03)
    fig.subplots_adjust(left=.06,right=.98,bottom=.13,top=.92,wspace=.46)

def das_detail(fig,r,fit):
    fig.clear();axs=fig.subplots(2,2)
    das_plot(axs[0,0],r,fit)
    image=contour(axs[0,1],dict(r,residual=fit['residual']),'residual','Residual from 2exp + offset model')
    fig.colorbar(image,ax=axs[0,1],label='µOD')
    for wn in [1559,1570,1697,1748]:
        j=np.argmin(abs(r['nu']-wn));axs[1,0].plot(r['t_us'],r['observed'][:,j]*1e6,label=f'{display_number(r["nu"][j])} cm⁻¹',lw=1)
    clean(axs[1,0],'Selected kinetic traces',ylabel='ΔA (µOD)');axs[1,0].set_xlabel('Time (µs)');axs[1,0].legend(fontsize=7)
    v=r['valid'];rms=np.sqrt(np.nanmean(fit['residual'][:,v]**2,axis=1))*1e6
    axs[1,1].plot(r['t_us'],rms,color=SIM)
    clean(axs[1,1],f'Fit RMS = {display_number(fit["rms"]*1e6)} µOD · basis condition = {display_number(fit["condition"])}',ylabel='Residual RMS (µOD)');axs[1,1].set_xlabel('Time (µs)')
    fig.subplots_adjust(left=.07,right=.98,bottom=.09,top=.94,wspace=.3,hspace=.45)

def interferograms(fig,r,index=26):
    fig.clear();axs=fig.subplots(2,2)
    x=np.fft.fftshift(r['x_cm'])*1e4
    ref=np.fft.fftshift(r['reference_ifg']);signal=np.fft.fftshift(r['signal_ifg'][index])
    axs[0,0].plot(x,ref,color=IDEAL,label='Reference',lw=1.7);axs[0,0].plot(x,signal,color=SIM,lw=.9,label='Selected time')
    axs[0,0].set_xlim(-100,100);clean(axs[0,0],'Reconstructed interferogram · near ZPD',ylabel='IFG (relative units)');axs[0,0].set_xlabel('OPD (µm)');axs[0,0].legend(fontsize=8)
    axs[0,1].plot(x,signal-ref,color=SIM);axs[0,1].set_xlim(-150,150)
    clean(axs[0,1],f'Interferogram change · {r["t_us"][index]:.1f} µs',ylabel='ΔIFG (relative units)');axs[0,1].set_xlabel('OPD (µm)')
    for j in [0,1,3]:axs[1,0].plot(r['t_us'],r['displacement_cm'][:,j]/2e-7,label=f'OPD index {j}')
    clean(axs[1,0],'Mean mirror displacement · OPD = 2 × mirror motion',ylabel='Mirror displacement (nm)');axs[1,0].set_xlabel('Time (µs)');axs[1,0].legend(fontsize=7)
    ds=r['signal'][index]-r['ref'];axs[1,1].plot(r['nu'],ds,color=SIM,label='ΔS');axs[1,1].plot(r['nu'],r['s0'],color='gray',alpha=.5,label='S₀')
    clean(axs[1,1],'Intensity domain · distinguish additive and gain artifacts',True,'Relative single-beam units');axs[1,1].legend(fontsize=8)
    axs[1,1].set_xlim(*spectral_bounds(r))
    fig.subplots_adjust(left=.07,right=.98,bottom=.09,top=.94,wspace=.3,hspace=.45)

def optics(fig,r,p):
    from ftir_sim import fold_display,laser_response
    fig.clear();axs=fig.subplots(2,2)
    axs[0,0].plot(r['leak_nu'],r['leak_source'],color=SIM);axs[0,0].axvspan(p.fold_width,2*p.fold_width,color=IDEAL,alpha=.1,label='Desired physical band')
    axs[0,0].set_xlim(6000,0);clean(axs[0,0],'Assumed out-of-band globar spectrum',ylabel='Weighted spectral intensity');axs[0,0].set_xlabel('True wavenumber (cm⁻¹)');axs[0,0].legend(fontsize=7)
    v=np.linspace(0,22000,5000);axs[0,1].plot(v,fold_display(v,p.fold_width),color=HEAT,lw=1)
    laser=1e7/p.laser_nm;axs[0,1].plot([laser],[r['laser_alias_cm1']],'o',color=SIM)
    axs[0,1].annotate(f'{p.laser_nm:g} nm → {r["laser_alias_cm1"]:.2f} cm⁻¹\nONLY if OPD-modulated',(laser,r['laser_alias_cm1']),xytext=(7000,1300),fontsize=8,arrowprops={'arrowstyle':'->','color':SIM})
    clean(axs[0,1],f'Alias map · ΔOPD = {display_number(r["dx_um"])} µm',ylabel='Displayed alias (cm⁻¹)');axs[0,1].set_xlabel('True wavenumber (cm⁻¹)')
    axs[1,0].plot(r['nu'],r['s0'],color=IDEAL,label='In-band S₀');axs[1,0].plot(r['nu'],r['folded_leak'],color=SIM,label='Folded constant leak L')
    clean(axs[1,0],'Constant leakage changes the denominator',True,'Relative single-beam units');axs[1,0].legend(fontsize=8)
    axs[1,0].set_xlim(*spectral_bounds(r))
    early=np.linspace(-.03,max(1.,6*p.response_us),3000)
    axs[1,1].plot(early,laser_response(early,p),color=HEAT,label='Optical pulse ⊗ assumed detector response')
    clean(axs[1,1],'Laser response · normalized area = 1',ylabel='Response (µs⁻¹)');axs[1,1].set_xlabel('Time (µs)')
    ax2=axs[1,1].twinx();kt=(r['t_us']>=-p.dt_us)&(r['t_us']<=max(20,6*p.response_us));ax2.step(r['t_us'][kt],r['laser_response'][kt],where='mid',color=SIM,label='Bin mean');ax2.set_ylabel(f'{p.dt_us:g} µs bin mean (µs⁻¹)',fontsize=8)
    axs[1,1].legend(fontsize=7,loc='upper right')
    from dataclasses import replace
    inset=axs[1,1].inset_axes([.54,.40,.42,.40])
    ns=np.linspace(-10,120,1600)
    inset.plot(ns,laser_response(ns*1e-3,replace(p,response_us=0))*1e-3,color=RP,lw=1)
    inset.set_title('Optical waveform only',fontsize=7);inset.set_xlabel('ns',fontsize=7);inset.tick_params(labelsize=6)
    inset.set_facecolor('#fffdf9')
    inset.yaxis.set_major_formatter(ReadableScalarFormatter())
    fig.subplots_adjust(left=.07,right=.93,bottom=.09,top=.94,wspace=.4,hspace=.45)


def optical_contributions(fig,r,p,time_us=100.,wavenumber=1697.):
    """Applied, unnormalized optical effects; CW and pulse remain distinct."""
    fig.clear();axs=fig.subplots(2,2);nu=r['nu'];t=r['t_us']
    axs[0,0].plot(nu,r['s0'],color=IDEAL,label='Ideal IR reference')
    axs[0,0].plot(nu,r['ref'],color=SIM,label='Reference with selected effects')
    clean(axs[0,0],'Reference intensity',True,'Relative single-beam units');axs[0,0].legend(fontsize=7)
    axs[0,1].plot(nu,r['folded_leak'],color=RP,label='Globar leakage')
    axs[0,1].plot(nu,selected_spectrum(r,'laser_signal_spectrum',time_us),color=SIM,label=f'532 nm at {time_us:g} µs')
    clean(axs[0,1],'Isolated optical readouts · actual amplitudes',True,'Relative single-beam units');axs[0,1].legend(fontsize=7)
    j=np.argmin(abs(nu-wavenumber));ideal_ds=r['s0'][j]*(10**(-r['ideal'][:,j])-1)
    axs[1,0].plot(t,ideal_ds,color=IDEAL,label='Ideal chemical ΔS')
    axs[1,0].plot(t,r['signal'][:,j]-r['ref'][j],color=SIM,label='Total signal − reference')
    clean(axs[1,0],f'Intensity change · {display_number(nu[j])} cm⁻¹',ylabel='Relative intensity change');axs[1,0].set_xlabel('Time after flash (µs)');axs[1,0].legend(fontsize=7)
    jl=np.argmin(abs(nu-r['laser_alias_cm1']))
    axs[1,1].plot(t,r['laser_signal_spectrum'][:,jl],color=SIM,label=f'Actinic at {nu[jl]:.2f} cm⁻¹')
    axs[1,1].axvline(0,color='k',lw=.6,alpha=.5)
    clean(axs[1,1],'Flash pickup · acquired bin means',ylabel='Isolated single-beam readout');axs[1,1].set_xlabel('Time after flash (µs)');axs[1,1].legend(fontsize=7)
    for ax in axs[0,:]:ax.set_xlim(*spectral_bounds(r))
    fig.subplots_adjust(left=.075,right=.98,bottom=.09,top=.94,wspace=.32,hspace=.42)



def waveform_view(fig,r,p,wavenumber=1697.):
    from ftir_sim import mirror_waveform
    fig.clear();axs=fig.subplots(2,1)
    t=r['t_us'];gate=(t>=0)
    drive=mirror_waveform(t,p).reshape(-1)*p.mirror_nm*gate
    axs[0].plot(t,drive,color=SIM,label='Declared mirror drive')
    axs[0].set_ylabel('Mirror displacement (nm)');axs[0].set_title('Drive hypothesis · not a measured displacement',loc='left')
    axs[0].legend(fontsize=8);axs[0].grid(alpha=.2)
    j=np.argmin(abs(r['nu']-wavenumber))
    axs[1].plot(t,r['difference'][:,j]*1e6,color=HEAT,label=f'Artifact at {r["nu"][j]:.2f} cm⁻¹')
    axs[1].set_ylabel('Artifact ΔA (µOD)');axs[1].set_xlabel('Time after flash (µs)');axs[1].legend(fontsize=8);axs[1].grid(alpha=.2)
    axs[1].set_title(f'Carrier {display_number(p.frequency_hz)} Hz · {p.frequency_hz*3.378e-3:.2f} cycles in 3.38 ms; readout can generate harmonics',loc='left',fontsize=9)
    fig.subplots_adjust(left=.09,right=.98,bottom=.1,top=.92,hspace=.4)

