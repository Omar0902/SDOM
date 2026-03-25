# cuOpt Integration — Summary & Setup Guide

## Overview

[NVIDIA cuOpt](https://github.com/NVIDIA/cuopt) is a GPU-accelerated LP/MILP solver.
This document summarises the code changes made to add cuOpt support to SDOM and provides step-by-step instructions for running the cuOpt tests on this laptop.

---

## Hardware / Driver Summary (this laptop)

| Property | Value |
|---|---|
| GPU | NVIDIA RTX 2000 Ada Generation |
| Compute Capability | 8.9 (≥ 7.0 required ✅) |
| CUDA Version | 12.4 ✅ |
| Driver Version | 552.74 ✅ |
| OS | Windows 11 (WDDM) |

> **Important:** cuOpt only supports **Linux and Windows via WSL2**. Native Windows is **not** supported. WSL2 must be installed first (see instructions below).

---

## Code Changes Made

### 1. `pyproject.toml` — Pyomo version bump

The `cuopt_direct` solver plugin was introduced in Pyomo **6.10**. The minimum version constraint was updated accordingly.

```diff
- "pyomo==6.9.5",
+ "pyomo>=6.10",
```

### 2. `src/sdom/optimization_main.py`

#### 2a. New import

```python
from pyomo.common.errors import ApplicationError
```

Required to catch the exception Pyomo raises when the cuOpt Python bindings are missing (instead of letting it propagate as an unhandled error).

#### 2b. `configure_solver` — graceful unavailability handling

```python
# Before
if not solver.available():
    raise RuntimeError(...)

# After
try:
    if not solver.available():
        raise RuntimeError(...)
except ApplicationError as e:
    raise RuntimeError(f"Solver '{solver_config_dict['solver_name']}' is not available on this system: {e}")
```

#### 2c. `get_default_solver_config_dict` — new `cuopt` branch

```python
elif solver_name == "cuopt":
    # cuopt is a Python-direct solver (requires NVIDIA GPU + cuopt Python package)
    solver_dict["solver_name"] = "cuopt"
```

Usage:
```python
from sdom import get_default_solver_config_dict, run_solver

solver_dict = get_default_solver_config_dict(solver_name="cuopt", executable_path="")
results = run_solver(model, solver_dict)
```

### 3. `tests/test_no_resiliency_optimization_cases_cuopt.py` — new test file

Eight tests mirroring the existing HiGHS / CBC tests across all four data scenarios:

| Test | Data scenario | Hours |
|---|---|---|
| `test_model_ini_cuopt_no_resiliency_24h` | Run-of-river | 24 |
| `test_optimization_res_cuopt_no_resiliency_24h` | Run-of-river | 24 |
| `test_model_ini_cuopt_no_resiliency_730h_monthly_budget` | Monthly hydro budget | 730 |
| `test_optimization_res_cuopt_no_resiliency_730h_monthly_budget` | Monthly hydro budget | 730 |
| `test_model_ini_cuopt_no_resiliency_168h_daily_budget` | Daily hydro budget | 168 |
| `test_optimization_res_cuopt_no_resiliency_168h_daily_budget` | Daily hydro budget | 168 |
| `test_model_ini_cuopt_no_resiliency_168h_daily_budget_imp_exp` | Daily hydro budget + imports/exports | 168 |
| `test_optimization_res_cuopt_no_resiliency_168h_daily_budget_imp_exp` | Daily hydro budget + imports/exports | 168 |

All tests are decorated with `pytestmark = pytest.mark.skipif(not _cuopt_available, ...)` so they:
- **Skip automatically** on machines without a GPU or without the `cuopt` package installed.
- **Run automatically** once cuOpt is properly installed — no code changes needed.

---

## Setup Instructions (this laptop)

### Step 1 — Install WSL2

Open **PowerShell as Administrator** and run:

```powershell
wsl --install
```

This installs WSL2 with Ubuntu and takes a few minutes. **A reboot is required.**

> After rebooting, Ubuntu will ask you to create a Linux username and password. Complete that setup before continuing.

### Step 2 — Verify GPU is accessible from WSL2

Open a WSL2 terminal (Ubuntu) and run:

```bash
nvidia-smi
```

You should see the RTX 2000 Ada listed. The NVIDIA Windows driver exposes the GPU to WSL2 automatically — no separate Linux driver install is needed.

### Step 3 — Install cuOpt in WSL2

```bash
# Inside WSL2 Ubuntu terminal
pip install \
  --extra-index-url=https://pypi.nvidia.com \
  nvidia-cuda-runtime-cu12==12.9.* \
  cuopt-cu12==26.06.*
```

Verify the install:

```bash
python -c "import cuopt; print(cuopt.__version__)"
```

### Step 4 — Run the cuOpt tests from WSL2

Navigate to the repo (the Windows filesystem is mounted at `/mnt/c/`):

```bash
cd /mnt/c/Users/smachado/repositories/pySDOM/SDOM
uv run pytest tests/test_no_resiliency_optimization_cases_cuopt.py -v
```

Expected output when cuOpt is available:

```
tests/test_no_resiliency_optimization_cases_cuopt.py::test_model_ini_cuopt_no_resiliency_24h PASSED
tests/test_no_resiliency_optimization_cases_cuopt.py::test_optimization_res_cuopt_no_resiliency_24h PASSED
...
8 passed in Xs
```

### Step 5 — Run the full test suite

```bash
uv run pytest tests/ \
  --ignore=tests/test_no_resiliency_optimization_cases_xpress_local.py \
  --ignore=tests/test_docs_build.py \
  --ignore=tests/test_resiliency_optimization_cases.py \
  -v
```

---

## Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| Tests still skipped after install | `cuopt` not importable in the venv | Ensure you installed inside the venv: `uv run pip install ...` |
| `nvidia-smi` fails in WSL2 | Driver or WSL2 CUDA not set up | Update Windows NVIDIA driver to ≥ 525.60; reboot |
| `cuopt` import error about CUDA runtime | CUDA runtime mismatch | Install `nvidia-cuda-runtime-cu12==12.9.*` alongside cuopt |
| CBC/HiGHS tests fail after Pyomo upgrade | Pyomo 6.10 API break | Check `uv run pytest tests/test_no_resiliency_optimization_cases.py` — should still pass |

---

## References

- [NVIDIA cuOpt GitHub](https://github.com/NVIDIA/cuopt)
- [Pyomo PR #3620 — cuopt_direct plugin](https://github.com/Pyomo/pyomo/pull/3620)
- [cuOpt Documentation](https://docs.nvidia.com/cuopt/user-guide/latest/introduction.html)
- [cuOpt pip packages (pypi.nvidia.com)](https://pypi.nvidia.com)
