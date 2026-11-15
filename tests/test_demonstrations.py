"""Analytical/independent checks of the explanatory acquisition model."""
import numpy as np
from dataclasses import replace
from demo_model import (DemoSettings,absorbance,averaged_intensity,build_demonstrations,
                        coherence,drive,harmonic_amplitudes,interferogram,shot_phases)


def test_zero_displacement_has_no_difference():
    nu=np.linspace(2100,1050,129);s=.5+np.linspace(0,1,129)
    reference=s*np.cos(2*np.pi*nu*2e-7*25)
    result=averaged_intensity(s,nu,np.zeros((7,3)),25)
    np.testing.assert_allclose(absorbance(result,reference),0,atol=2e-16)
    assert np.isnan(absorbance(np.array([0.,1.]),np.array([1.,0.]))).all()


def test_exact_shift_agrees_with_direct_physical_cosine_transform():
    # A dense physical sum evaluated independently at FFT-grid OPDs.
    n=256;B=1050.;nu=2*B-np.arange(n//2+1)*2*B/n
    s=np.exp(-((nu-1600)/170)**2)+.2
    x=np.fft.fftfreq(n)*n/(2*B);bias=25.;amplitude=2.
    weights=np.full(len(nu),2/n);weights[[0,-1]]=1/n
    direct=np.array([np.sum(weights*s*np.cos(2*np.pi*nu*(value+2e-7*(bias+amplitude)))) for value in x])
    transformed=np.fft.rfft(direct).real
    exact=averaged_intensity(s,nu,np.array([amplitude]),bias)[0]
    np.testing.assert_allclose(transformed,exact,atol=6e-13,rtol=6e-13)


def test_detector_gradient_is_physical_opd_derivative():
    nu=np.linspace(2100,1050,129);s=np.ones(129);x=np.array([0.,.0002,.0008])
    h=1e-9
    finite=(interferogram(s,nu,x+h)-interferogram(s,nu,x-h))/(2*h)
    np.testing.assert_allclose(finite,interferogram(s,nu,x,1),rtol=2e-7,atol=1e-7)
    assert abs(interferogram(s,nu,0.,1))<1e-10


def test_half_period_phase_pairing_averages_intensity_before_log():
    p=DemoSettings(amplitude_nm=20.)
    t=np.arange(2048)/2048/p.frequency_hz*1e6;nu=np.array([1697.])
    paired=drive(t,p,[0,np.pi]);k=2*np.pi*nu*2e-7
    reference=np.cos(k*p.common_bias_nm)
    mean_s=averaged_intensity(np.ones(1),nu,paired,p.common_bias_nm)
    # cos(b+a)+cos(b-a) = 2 cos(b) cos(a), independently of the bias.
    expected_ratio=np.cos(k[0]*drive(t,p)[:,0])
    np.testing.assert_allclose(mean_s[:,0]/reference[0],expected_ratio,atol=5e-16)
    mean_a=absorbance(mean_s,reference)[:,0]
    amplitudes=harmonic_amplitudes(mean_a)
    assert amplitudes[0]<1e-15 and amplitudes[1]>1e-5
    individual=[absorbance(averaged_intensity(np.ones(1),nu,paired[:,i:i+1],p.common_bias_nm),reference)[:,0] for i in range(2)]
    assert np.max(abs(np.mean(individual,axis=0)-mean_a))>1e-7


def test_commensurate_timing_does_not_reduce_coherent_intensity_harmonics():
    for count in [1,2,8,32]:
        phases=shot_phases(count,840.,10.)
        np.testing.assert_allclose([coherence(phases,m) for m in [1,2,3]],1,atol=2e-14)
    phases=shot_phases(8,840.,paired=True)
    assert coherence(phases,1)<1e-14 and coherence(phases,2)>1-1e-14
    assert coherence(shot_phases(8,840.,10.01),1)<.5


def test_even_response_and_small_displacement_second_harmonic():
    p=DemoSettings();t=np.arange(4096)/4096/p.frequency_hz*1e6;nu=np.array([1697.])
    signal=averaged_intensity(np.ones(1),nu,drive(t,p),0.)
    y=absorbance(signal,np.ones(1))[:,0];amplitudes=harmonic_amplitudes(y)
    k=2*np.pi*nu[0]*2e-7
    expected=(k*p.amplitude_nm)**2/(4*np.log(10))
    assert amplitudes[0]<1e-15
    np.testing.assert_allclose(amplitudes[1],expected,rtol=1e-5)


def test_bundle_is_finite_descending_and_agrees_with_production_small_shift():
    from ftir_sim import Settings,simulate
    d=build_demonstrations()
    assert np.all(np.diff(d['nu'])<0)
    assert np.isfinite(d['mirror_OD']).all() and np.isfinite(d['electrical_OD']).all()
    production=simulate(replace(Settings(),wobble=True,bias_nm=25.,coadds=1))
    # The only difference is exact cosine versus the production fourth-order
    # displacement expansion at the declared small phase excursion.
    error=np.max(abs(production['observed']-d['chemical_mirror_OD']))
    assert error<1e-9,error
    assert d['harmonic_amplitudes_OD']['Common bias'][0]>40*d['harmonic_amplitudes_OD']['Common bias'][1]
