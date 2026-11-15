# Contributing

Report a reproducible issue with FringeScope version, OS, selected parameters, time/wavenumber selection and expected versus actual behavior. Use a minimal synthetic example. Do not upload unpublished measurements or identifying local paths by default.

Keep cm⁻¹ axes descending, mirror nm distinct from OPD cm, time in µs, and signed ΔA/DAS amplitudes explicit. Declare interpolation, bin integration, masks, fitting constraints and uncertainty treatment. Numerical agreement does not identify an experimental artifact mechanism. New physics needs an analytical/independent check and primary-source support or an explicit assumption.

Run the tests and the relevant offline figure/UI checks. Changes to startup, resources, dependencies or update behavior also need standalone/installed checks. Keep generated runs separate from source. Contributions should be compatible with the MIT application license; third-party licenses and scientific attribution remain applicable.
