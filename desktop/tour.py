"""Guided tour: the single source for the desktop application and the browser edition.

Each step starts from the Settings() defaults plus BASE, then applies the steps up to and
including itself (switching every source in OFF off before each). Statements under "look"
were checked against the engine output for these exact settings.
"""

OFF = ['wobble', 'globar', 'laser', 'electrical', 'zpd']
BASE = {'electrical_mode': 'mains', 'mains_harmonic': 14, 'fit_start': 0, 'fit_stop': 3378,
        'fit_low': 1200, 'fit_high': 1900, 'offset': True}
WAVENUMBER = 1697

# Targets: contour, spectrum, kinetics, das (Explore panels); o0-o3 (Optical contributions
# panels, row by row); source:<setting> (a source toggle).
STEPS = [
    {'title': 'Ideal signal', 'source': None, 'next': 'Next: mirror motion', 'time_us': 100, 'alias': False,
     'controls': {},
     'changed': 'All five artifact sources are off and the tour defaults are applied. '
                'Your own settings are kept and come back when the tour ends.',
     'look': [
         ('spectrum', 'Spectrum at 100 µs: the artifact-free curve and the effects-applied curve coincide.'),
         ('kinetics', 'Kinetics at 1697 cm⁻¹: they coincide over the whole decay. '
                      'The dashed line is the two-exponential + offset projection.'),
         ('das', 'DAS: the dashed projected spectra follow the input spectra. '
                 'The next three steps are compared with this.'),
         ('contour', 'Click the contour to choose another time and wavenumber; the other panels follow.')]},
    {'title': 'Mirror motion', 'source': 'wobble', 'next': 'Next: globar leakage', 'time_us': 100, 'alias': False,
     'controls': {'wobble': True, 'mirror_nm': 2, 'frequency_hz': 840, 'bias_nm': 25, 'phase_deg': -100,
                  'waveform': 'sine', 'coadds': 1, 'phase_mode': 'locked'},
     'changed': 'Mirror motion is on: a 2 nm, 840 Hz sine drive about a 25 nm common bias, '
                'temporal phase −100°. All other sources are off.',
     'look': [
         ('contour', 'Contour: broad horizontal bands that change sign with time. '
                     'The 840 Hz drive (period ≈ 1.19 ms) is sampled by 6 µs bins.'),
         ('kinetics', 'Kinetics at 1697 cm⁻¹: the effects-applied trace oscillates about the '
                      'artifact-free decay, by about ±100 µOD on a 600 µOD signal.'),
         ('spectrum', 'Spectrum at 100 µs: the artifact covers the whole band, including regions with no '
                      'chemical signal, and grows toward high wavenumber (about 140 µOD at the band edge, '
                      'against a 460 µOD peak signal).'),
         ('das', 'DAS: the projected DAS now differ from the input. '
                 'A fit would report part of the artifact as kinetics.'),
         ('source:wobble', 'Switch Mirror motion off and on to compare.')]},
    {'title': 'Globar leakage', 'source': 'globar', 'next': 'Next: actinic pickup', 'time_us': 100, 'alias': False,
     'controls': {'globar': True, 'globar_fraction': 0.1, 'blocking_od': 0, 'leak_transient_ppm': 0},
     'changed': 'Globar leakage is on: continuous leakage at fraction 0.1, blocking OD 0, '
                'no changing-leak term. Mirror motion is off again.',
     'look': [
         ('spectrum', 'Spectrum: the same shape, about 6–12 % smaller depending on wavenumber. A stable leak dilutes the real difference.'),
         ('kinetics', 'Kinetics: the decay keeps its timing. A stable leak does not create a transient '
                      'from an unchanged sample.'),
         ('o0', 'Optical contributions, reference intensity: the leak raises the single-beam reference '
                'above the ideal IR reference.'),
         ('o2', 'Optical contributions, intensity change: the chemical change ΔS is unchanged; '
                'dividing by the larger reference makes ΔA smaller.')]},
    {'title': 'Actinic (532 nm) pickup', 'source': 'laser', 'next': 'Finish', 'time_us': 3, 'alias': True,
     'controls': {'laser': True, 'laser_route': 'interferometric', 'laser_area_us': 2e-6, 'laser_blocking_od': 0},
     'changed': '532 nm actinic pickup is on: an assumed OPD-modulated return with pulse area '
                '2 × 10⁻⁶ IFG-peak·µs. The selection moves to the 3 µs bin and to the 532 nm alias '
                'channel (≈ 1946 cm⁻¹).',
     'look': [
         ('spectrum', 'Spectrum at 3 µs: a one-channel dip of about −65 µOD at the dotted laser-alias line, '
                      'where 532 nm light folds onto this sampling grid. Zoom in to see it.'),
         ('kinetics', 'Kinetics at the alias channel: a spike in the 3 µs bin only; the next bin is clean.'),
         ('contour', 'Contour: the crosshair marks the alias channel at early time. '
                     'A spectrum taken at 100 µs would miss this response.')]},
]


def step_controls(k):
    """Control values set by step k on top of Settings() defaults and BASE."""
    values = dict(BASE)
    for step in STEPS[:k+1]:
        values.update({key: False for key in OFF}); values.update(step['controls'])
    return values


def as_json():
    """Plain-JSON form for the browser edition."""
    return {'off': OFF, 'base': BASE, 'wavenumber': WAVENUMBER,
            'steps': [dict(step, look=[{'target': t, 'text': x} for t, x in step['look']]) for step in STEPS]}
