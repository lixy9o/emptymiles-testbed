"""Reference emission & cost factors.

Illustrative values grounded in publicly published figures (UK DEFRA greenhouse-gas
conversion factors / the GLEC framework). REPLACE with the exact DEFRA row for the
vehicle class you are modelling before quoting any number externally - the point of
grounding them here is that the *physics* is real even though the *volumes* are synthetic.

Indicative diesel road-freight tailpipe factors (g CO2e per vehicle-km):
  - Van (<3.5t)        ~ 250 g/km
  - Rigid HGV          ~ 700 g/km
  - Articulated HGV    ~ 900 g/km
"""

VAN_G_PER_KM = 250.0
RIGID_HGV_G_PER_KM = 700.0
ARTIC_HGV_G_PER_KM = 900.0

# Placeholder operating cost (£ per vehicle-km). Swap for a real cost model later.
DEFAULT_COST_PER_KM = 1.20
