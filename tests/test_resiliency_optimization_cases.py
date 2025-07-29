import os
import pytest

from SDOM.io_manager import load_data, export_results
from SDOM.optimization_main import run_solver, initialize_model
from pyomo.environ import *

def test_optimization_model_ini_case_resiliency_24h():
    #INCLUDE YOUR TESTS HERE
    assert 1 == 1