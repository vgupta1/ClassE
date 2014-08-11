"""Handles the platform specific import of hte optimizer"""

## Import platform specific model
from platform import system
if "WINDOWS" in system().upper():
    from optimizer_gurobi import * #uses gurobi, for windows
else:
    from optimizer_cplex import * #uses cplex, for mac osx
