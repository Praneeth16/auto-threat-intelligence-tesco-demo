"""Classical CTI layer: deterministic feature engineering, no model calls.

Pure-pandas transforms so they are locally testable against datagen output and
produce the same silver/gold reference tables the Lakeflow pipeline targets.
The division of labor (PLAN 7.2): the classical layer builds structured
features and the transparent score; the AI layer reasons over those features.
"""
