"""Tests for the ``critical_load_MW`` override on outage dispatch (#73).

Covers the new keyword argument added to ``build_outage_dispatch``.
Runner and ``evaluate_resiliency`` forwarding tests are added by the
follow-up commits in this branch.
"""

from __future__ import annotations

import pandas as pd
import pytest

from sdom.resiliency import (
    OutageSpec,
    build_outage_dispatch,
)

from tests.test_resiliency_outage_dispatch import (
    _make_baseline_results,
    _make_designed_system,
)


def _build(start_hour=5, duration=4, recovery=4, n_hours=24, **kwargs):
    """Build a tiny outage LP and return ``(model, ds, br, start, duration)``.

    A non-flat baseline load (``10*t``) is injected so the override can be
    distinguished from the baseline value at every hour.
    """
    ds = _make_designed_system(n=n_hours, load_value=50.0)
    varying = pd.Series(
        [10.0 * t for t in range(1, n_hours + 1)],
        index=ds.load.index,
        name=ds.load.name,
    )
    ds = ds.__class__(
        storage_caps=ds.storage_caps,
        thermal_caps=ds.thermal_caps,
        solar_caps=ds.solar_caps,
        wind_caps=ds.wind_caps,
        load=varying,
        cf_solar=ds.cf_solar,
        cf_wind=ds.cf_wind,
        nuclear=ds.nuclear,
        hydro=ds.hydro,
        other_renewables=ds.other_renewables,
        import_cap=ds.import_cap,
        import_price=ds.import_price,
        export_cap=ds.export_cap,
        export_price=ds.export_price,
        phi_fix_t=ds.phi_fix_t,
        phi_var_t=ds.phi_var_t,
        month_of_hour=ds.month_of_hour,
    )
    br = _make_baseline_results(ds, soc_value=20.0)
    spec = OutageSpec(
        duration_hours=duration,
        recovery_hours=recovery,
        outaged_assets={"balancing_units": "all"},
    )
    model = build_outage_dispatch(
        br,
        start_hour=start_hour,
        outage_spec=spec,
        designed_system=ds,
        n_hours=n_hours,
        **kwargs,
    )
    return model, ds, br, start_hour, duration


def test_critical_load_default_is_baseline():
    """``critical_load_MW=None`` (default) must match ``designed_system.load``."""
    model, ds, _, _, _ = _build()
    for t in model.h:
        assert float(model.load_param[t]) == pytest.approx(float(ds.load.loc[t]))
    assert model._sdom_outage_meta["critical_load_MW"] is None


def test_critical_load_overrides_outage_window_only():
    crit = 123.5
    model, ds, _, start, duration = _build(critical_load_MW=crit)
    outage_end = start + duration - 1
    for t in model.h:
        expected = crit if start <= t <= outage_end else float(ds.load.loc[t])
        assert float(model.load_param[t]) == pytest.approx(expected), (
            f"hour {t}: got {float(model.load_param[t])}, expected {expected}"
        )


def test_critical_load_zero_is_valid():
    model, _, _, start, duration = _build(critical_load_MW=0.0)
    for t in range(start, start + duration):
        assert float(model.load_param[t]) == pytest.approx(0.0)
    assert model._sdom_outage_meta["critical_load_MW"] == 0.0


def test_critical_load_negative_raises():
    with pytest.raises(ValueError, match="critical_load_MW must be non-negative"):
        _build(critical_load_MW=-1.0)


def test_critical_load_metadata_round_trip():
    model, _, _, _, _ = _build(critical_load_MW=77.0)
    assert model._sdom_outage_meta["critical_load_MW"] == pytest.approx(77.0)
