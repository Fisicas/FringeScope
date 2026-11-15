"""Original teaching figures; dark UI styling is applied by the caller only."""
import numpy as np
from display_format import number, ReadableScalarFormatter

VIEWS = ['OPD detector traces', 'Artifact-only baselines', 'Mirror harmonics and PSI', 'Coaddition and phase']
FILES = ['opd_detector_traces','artifact_baselines','mirror_harmonics_psi','coaddition_phase']
COLORS = ['#dc6654','#28876a','#337fba','#c58a24','#956bb0']


def style(ax,title,xlabel='',ylabel=''):
    ax.set_title(title,fontsize=11,weight='bold',pad=10)
    ax.set_xlabel(xlabel,fontsize=10);ax.set_ylabel(ylabel,fontsize=10)
    ax.grid(alpha=.17);ax.spines[['top','right']].set_visible(False)
    ax.xaxis.set_major_formatter(ReadableScalarFormatter())
    ax.yaxis.set_major_formatter(ReadableScalarFormatter())
    ax.tick_params(labelsize=9)


def finish(fig,title,footnote):
    fig.suptitle(title,fontsize=14,weight='bold',y=.98)
    fig.text(.5,.018,footnote,ha='center',va='bottom',fontsize=9,linespacing=1.35)


def harmonic_bars(ax,series):
    floor=1e-6;orders=np.arange(1,5);width=.78/len(series)
    for i,(label,values) in enumerate(series.items()):
        values=np.asarray(values)*1e6;positions=orders+(i-(len(series)-1)/2)*width
        shown=values>=floor
        ax.bar(positions[shown],values[shown],width*.92,color=COLORS[i],label=label)
        ax.scatter(positions[~shown],np.full((~shown).sum(),floor),marker='v',color=COLORS[i],s=26)
    ax.set_yscale('log');ax.set_ylim(bottom=floor*.45);ax.set_xticks(orders,['f','2f','3f','4f'])
    ax.grid(axis='y',alpha=.18,which='major');ax.legend(fontsize=8)
    ax.set_xlabel('Drive harmonic');ax.set_ylabel('Amplitude (µOD)')
    ax.set_title('One exact cycle · DC excluded · log scale',fontsize=11,weight='bold',pad=10)
    ax.tick_params(labelsize=9);ax.spines[['top','right']].set_visible(False)


def detector(fig,d):
    fig.clear();grid=fig.add_gridspec(2,2);left=fig.add_subplot(grid[0,0]);right=fig.add_subplot(grid[0,1]);traces=fig.add_subplot(grid[1,:])
    x=d['continuous_x_cm']*1e4;peak=d['ir_ifg_peak'];locations=d['selected_x_cm']*1e4
    left.plot(x,d['continuous_ifg']/peak,color='#586675',lw=.9)
    right.plot(x,d['continuous_slope']/peak*1e-4,color='#586675',lw=.9)
    for j,(value,color) in enumerate(zip(locations,COLORS)):
        left.plot(value,d['trace_reference'][j]/peak,'o',color=color,ms=5)
        right.plot(value,d['local_slope'][j]/peak*1e-4,'o',color=color,ms=5)
    style(left,'Analytic reference AC interferogram','OPD (µm)','I / ideal IR IFG peak')
    style(right,'Local slope sets the first-order response','OPD (µm)','Normalized slope (µm⁻¹)')
    left.set_xlim(-170,170);right.set_xlim(-170,170)
    values=d['detector_change']/peak*1e6;linear=d['linear_change']/peak*1e6
    gap=float(np.max(abs(values))*2.35)
    for j,(value,color) in enumerate(zip(locations,COLORS)):
        traces.plot(d['time_us']*1e-3,values[:,j]+j*gap,color=color,lw=1.5)
        traces.plot(d['time_us']*1e-3,linear[:,j]+j*gap,color='#67747d',lw=.8,ls='--')
    style(traces,'Detector changes at sampled OPDs · solid exact; dashed local-slope approximation',
          'Time from acquisition origin (ms)','ΔI / ideal IR IFG peak (ppm) + offsets')
    traces.set_yticks(np.arange(len(locations))*gap,[number(v)+' µm' for v in locations]);traces.set_xlim(0,d['time_us'][-1]*1e-3)
    fig.subplots_adjust(left=.12,right=.975,top=.88,bottom=.16,hspace=.62,wspace=.3)
    finish(fig,'How residual motion reaches the detector',
        f'2 nm mirror amplitude · 840 Hz · 25 nm common bias · no excitation or noise. All traces use the same IR IFG peak.\n'
        f'Graphical offset step = {number(gap)} ppm; y tick labels identify OPD. Only the AC detector component is modeled.')


def baselines(fig,d):
    fig.clear();axes=fig.subplots(2,2);nu=d['nu'];t=d['time_us']*1e-3
    period_us=1e6/d['settings']['frequency_hz']
    selected=[int(np.argmin(abs(d['time_us']-period_us*q))) for q in [.25,.5,.75]]
    for row,(key,label) in enumerate([('mirror_OD','Uniform biased mirror'),('electrical_OD','Assumed ZPD-local electrical pickup')]):
        z=d[key]*1e6;limit=float(np.max(abs(z)))
        image=axes[row,0].imshow(z,origin='lower',extent=(nu[0],nu[-1],t[0],t[-1]),aspect='auto',cmap='RdBu_r',vmin=-limit,vmax=limit,rasterized=True)
        style(axes[row,0],label+' · own color scale','Wavenumber (cm⁻¹)','Acquisition time (ms)')
        fig.colorbar(image,ax=axes[row,0],pad=.02,label='µOD',format=ReadableScalarFormatter())
        for i,index in enumerate(selected):
            axes[row,1].plot(nu,z[index],color=COLORS[i],lw=1.4,label=number(t[index])+' ms')
        style(axes[row,1],'Signed spectral slices · native acquisition bins','Wavenumber (cm⁻¹)','ΔA (µOD)')
        axes[row,1].set_xlim(nu[0],nu[-1]);axes[row,1].legend(fontsize=8)
    fig.subplots_adjust(left=.075,right=.97,top=.88,bottom=.16,hspace=.6,wspace=.35)
    finish(fig,'Unexcited sample: two different routes to baseline artifacts',
        '840 Hz · stationary reference at 25 nm common bias · exact real readout. No chemistry, optical leakage, or random noise.\n'
        'Mirror: 2 nm sinusoidal drive. Electrical: 200 ppm of IR IFG peak, Gaussian coupling of width 0.5 OPD step. IR reference remains present.')


def harmonics(fig,d):
    fig.clear();axes=fig.subplots(2,2);nu=d['nu'];t=d['time_us']*1e-3
    for i,(label,values) in enumerate(d['harmonic_traces_OD'].items()):
        axes[0,0].plot(t,values*1e6,color=COLORS[i],label=label,lw=1.4)
    style(axes[0,0],'Pure sine displacement · '+number(d['selected_actual_cm1'])+' cm⁻¹','Acquisition time (ms)','ΔA (µOD)')
    axes[0,0].legend(fontsize=8,loc='lower left');axes[0,0].set_xlim(t[0],t[-1])
    inset=axes[0,0].inset_axes([.58,.65,.38,.28]);inset.plot(t,d['harmonic_traces_OD']['Zero bias']*1e6,color=COLORS[0],lw=.9)
    inset.set_title('Zero bias · enlarged',fontsize=7);inset.tick_params(labelsize=6);inset.set_ylabel('µOD',fontsize=7)
    inset.xaxis.set_major_formatter(ReadableScalarFormatter());inset.yaxis.set_major_formatter(ReadableScalarFormatter())
    harmonic_bars(axes[0,1],d['harmonic_amplitudes_OD'])
    ct=d['chemical_time_us'];selected=d['settings']['spectrum_us'];channel=d['selected_channel']
    clean=np.array([np.interp(selected,ct,d['chemical_clean_OD'][:,j]) for j in range(len(nu))])*1e6
    affected=np.array([np.interp(selected,ct,d['chemical_mirror_OD'][:,j]) for j in range(len(nu))])*1e6
    axes[1,0].plot(nu,clean,color=COLORS[1],label='Artifact-free PSI ΔA · same model',lw=1.7)
    axes[1,0].plot(nu,affected,color=COLORS[0],label='Plus biased mirror',lw=1.1)
    style(axes[1,0],'Shared PSI ΔA · 100 µs (linear time interpolation)','Wavenumber (cm⁻¹)','ΔA (µOD)')
    axes[1,0].set_xlim(nu[0],nu[-1]);axes[1,0].legend(fontsize=8)
    axes[1,1].plot(ct*1e-3,d['chemical_clean_OD'][:,channel]*1e6,color=COLORS[1],label='Artifact-free PSI ΔA',lw=1.7)
    axes[1,1].plot(ct*1e-3,d['chemical_mirror_OD'][:,channel]*1e6,color=COLORS[0],label='Plus biased mirror',lw=1.1)
    style(axes[1,1],'Chemical kinetics · '+number(d['selected_actual_cm1'])+' cm⁻¹','Time after flash (ms)','ΔA (µOD)')
    axes[1,1].legend(fontsize=8)
    fig.subplots_adjust(left=.075,right=.97,top=.88,bottom=.16,hspace=.6,wspace=.29)
    finish(fig,'A sinusoidal drive can produce multiple spectral frequencies',
        '2 nm at 840 Hz; common bias 0 versus 25 nm. Harmonics are measured over one exact cycle; triangles denote < 10⁻⁶ µOD.\n'
        'Chemical panels: two bin-averaged exponential components + causal offset; motion sampled at bin centers and gated at the flash.')


def averaging(fig,d):
    fig.clear();axes=fig.subplots(2,2);counts=d['coadd_counts'];t=d['time_us']*1e-3
    for i,(label,transfer) in enumerate(d['coherence'].items()):
        mask=(counts%2==0) if label=='180° pairs' else np.ones(len(counts),bool)
        for order in range(2):
            axes[0,order].plot(counts[mask],transfer[order,mask],color=COLORS[i],marker='o',ms=3,lw=1.2,label=label)
        axes[1,0].plot(t,d['averaged_traces_OD'][label]*1e6,color=COLORS[i],lw=1.4,label=label)
    for order in range(2):
        style(axes[0,order],['Fundamental intensity coherence |C₁|','Second-harmonic intensity coherence |C₂|'][order],
            'Records coadded at each OPD','|mean exp(i mφ)|')
        axes[0,order].set_ylim(-.04,1.08);axes[0,order].set_xlim(1,32);axes[0,order].legend(fontsize=8)
    style(axes[1,0],'Eight records · average intensity, then take log','Acquisition time (ms)','ΔA (µOD)')
    axes[1,0].legend(fontsize=8,loc='lower left');axes[1,0].set_xlim(t[0],t[-1])
    harmonic_bars(axes[1,1],d['averaged_harmonics_OD'])
    fig.subplots_adjust(left=.075,right=.97,top=.88,bottom=.16,hspace=.6,wspace=.29)
    finish(fig,'Coaddition depends on timing and harmonic order',
        '840 Hz · 2 nm · 25 nm bias. 10 Hz gives 84 cycles/record; 10.01 Hz gives phase walk. 180° pairing uses even record counts.\n'
        'Common OPD phase is imposed to isolate shot timing; no free-running step-phase schedule. No 1/√N attenuation is assumed.')


def draw(fig,data,index):
    [detector,baselines,harmonics,averaging][index](fig,data)
