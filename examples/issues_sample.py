"""This deliberately contains issues to demonstrate static analysis.

The analyzer reads this file but never executes it.
"""

import math
import os


def calculate(values=[]):
    try:
        return math.sqrt(values[0] / 0)
    except:
        return 0
