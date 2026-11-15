"""Source-guided heating constraints and the shared synthetic PSI model."""
import numpy as np
from ftir_sim import Settings,build_truth
from demo_model import build_demonstrations


def test_literature_guided_heating_signs_and_quiet_low_wavenumber_tail():
    nu,t,truth,s0,spectra=build_truth(Settings())
    heating=spectra[0]
    for wn,sign in [(1699,-1),(1662,1),(1623,-1),(1561,-1),(1545,1),(1473,-1)]:
        index=np.argmin(abs(nu-wn))
        assert sign*heating[index]>1e-5,(wn,heating[index])
    tail=(nu>=1200)&(nu<=1400)
    assert np.max(abs(heating[tail]))<1e-12


def test_long_time_component_is_declared_mixture_not_independent_broad_lumps():
    nu,t,truth,s0,spectra=build_truth(Settings())
    np.testing.assert_allclose(spectra[2],.08*spectra[1]+.04*spectra[0],atol=2e-20)
    # By the last native bin, the prompt component has decayed and the remaining
    # difference is the declared offset plus a very small recombination tail.
    np.testing.assert_allclose(truth[-1],spectra[2],atol=4e-7)


def test_main_and_demonstration_share_the_identical_artifact_free_psi_signal():
    nu,t,truth,s0,spectra=build_truth(Settings())
    demo=build_demonstrations()
    np.testing.assert_array_equal(demo['chemical_time_us'],t)
    np.testing.assert_array_equal(demo['nu'],nu)
    np.testing.assert_array_equal(demo['chemical_clean_OD'],truth)
