"""Shared constants for resiliency-related tests (MEA case)."""

from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]

INPUTS_DIR_MEA = REPO_ROOT / "res_runs_paper" / "inputs" / "inputs_csv" / "Paper_MEA 1"
SNAPSHOT_DIR_MEA = REPO_ROOT / "res_runs_paper" / "inputs" / "outputs_CEM" / "For_simulations_MEA"

YEAR = 2030
SCENARIO_ID = 1
N_HOURS_SMOKE = 24
