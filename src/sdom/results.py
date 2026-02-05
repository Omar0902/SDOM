"""Module for SDOM optimization results data structures and utilities."""

import logging
from dataclasses import dataclass, field
from typing import Any

import pandas as pd
from pyomo.environ import sqrt

from .common.utilities import safe_pyomo_value
from .constants import MW_TO_KW


@dataclass
class OptimizationResults:
    """Data class containing all optimization results from SDOM.

    This class stores the complete results from an SDOM optimization run,
    organized into DataFrames for different result categories (generation,
    storage, summary) and provides convenient accessors for specific metrics.

    Attributes
    ----------
    termination_condition : str
        The solver termination condition (e.g., 'optimal', 'infeasible').
    solver_status : str
        The solver status (e.g., 'ok', 'warning').
    total_cost : float
        The total objective value (cost) from the optimization.
    gen_mix_target : float
        The generation mix target value used in this run.
    generation_df : pd.DataFrame
        Hourly generation dispatch results for all technologies.
    storage_df : pd.DataFrame
        Hourly storage operation results (charge, discharge, SOC).
    thermal_generation_df : pd.DataFrame
        Disaggregated hourly thermal generation by plant.
    installed_plants_df : pd.DataFrame
        Installed capacity for each individual power plant (solar, wind, thermal).
    summary_df : pd.DataFrame
        Summary metrics including capacities, costs, and totals.
    problem_info : dict
        Solver problem information (constraints, variables, etc.).
    capacity : dict
        Installed capacity by technology.
    storage_capacity : dict
        Storage capacity details (charge, discharge, energy).
    generation_totals : dict
        Total generation by technology.
    cost_breakdown : dict
        Detailed cost breakdown (CAPEX, OPEX, FOM, VOM).
    """

    # Solver information
    termination_condition: str = ""
    solver_status: str = ""

    # Main objective
    total_cost: float = 0.0
    gen_mix_target: float = 0.0

    # DataFrames for CSV export
    generation_df: pd.DataFrame = field(default_factory=pd.DataFrame)
    storage_df: pd.DataFrame = field(default_factory=pd.DataFrame)
    thermal_generation_df: pd.DataFrame = field(default_factory=pd.DataFrame)
    installed_plants_df: pd.DataFrame = field(default_factory=pd.DataFrame)
    summary_df: pd.DataFrame = field(default_factory=pd.DataFrame)

    # Problem info from solver
    problem_info: dict = field(default_factory=dict)

    # Capacity results
    capacity: dict = field(default_factory=dict)
    storage_capacity: dict = field(default_factory=dict)

    # Generation totals
    generation_totals: dict = field(default_factory=dict)

    # Cost breakdown
    cost_breakdown: dict = field(default_factory=dict)

    # ----------------------------------------------------------------------------------
    # Convenience properties for backward compatibility and easy access
    # ----------------------------------------------------------------------------------

    @property
    def is_optimal(self) -> bool:
        """Check if the solution is optimal."""
        return self.termination_condition == "optimal"

    # Capacity accessors
    @property
    def total_cap_thermal(self) -> float:
        """Total installed thermal capacity (MW)."""
        return self.capacity.get("Thermal", 0.0)

    @property
    def total_cap_pv(self) -> float:
        """Total installed solar PV capacity (MW)."""
        return self.capacity.get("Solar PV", 0.0)

    @property
    def total_cap_wind(self) -> float:
        """Total installed wind capacity (MW)."""
        return self.capacity.get("Wind", 0.0)

    @property
    def total_cap_storage_charge(self) -> dict:
        """Storage charging power capacity by technology (MW)."""
        return self.storage_capacity.get("charge", {})

    @property
    def total_cap_storage_discharge(self) -> dict:
        """Storage discharging power capacity by technology (MW)."""
        return self.storage_capacity.get("discharge", {})

    @property
    def total_cap_storage_energy(self) -> dict:
        """Storage energy capacity by technology (MWh)."""
        return self.storage_capacity.get("energy", {})

    # Generation accessors
    @property
    def total_gen_pv(self) -> float:
        """Total solar PV generation (MWh)."""
        return self.generation_totals.get("Solar PV", 0.0)

    @property
    def total_gen_wind(self) -> float:
        """Total wind generation (MWh)."""
        return self.generation_totals.get("Wind", 0.0)

    @property
    def total_gen_thermal(self) -> float:
        """Total thermal generation (MWh)."""
        return self.generation_totals.get("Thermal", 0.0)

    # ----------------------------------------------------------------------------------
    # DataFrame accessors
    # ----------------------------------------------------------------------------------

    def get_generation_dataframe(self) -> pd.DataFrame:
        """Get the hourly generation dispatch DataFrame.

        Returns
        -------
        pd.DataFrame
            DataFrame with columns: Scenario, Hour, Solar PV Generation (MW),
            Solar PV Curtailment (MW), Wind Generation (MW), Wind Curtailment (MW),
            All Thermal Generation (MW), Hydro Generation (MW), Nuclear Generation (MW),
            Other Renewables Generation (MW), Imports (MW), Storage Charge/Discharge (MW),
            Exports (MW), Load (MW).
        """
        return self.generation_df.copy()

    def get_storage_dataframe(self) -> pd.DataFrame:
        """Get the hourly storage operation DataFrame.

        Returns
        -------
        pd.DataFrame
            DataFrame with columns: Hour, Technology, Charging power (MW),
            Discharging power (MW), State of charge (MWh).
        """
        return self.storage_df.copy()

    def get_thermal_generation_dataframe(self) -> pd.DataFrame:
        """Get the disaggregated hourly thermal generation DataFrame.

        Returns
        -------
        pd.DataFrame
            DataFrame with columns: Hour, and one column per thermal plant.
        """
        return self.thermal_generation_df.copy()

    def get_summary_dataframe(self) -> pd.DataFrame:
        """Get the summary metrics DataFrame.

        Returns
        -------
        pd.DataFrame
            DataFrame with columns: Metric, Technology, Run, Optimal Value, Unit.
        """
        return self.summary_df.copy()

    def get_installed_plants_dataframe(self) -> pd.DataFrame:
        """Get the installed power plants capacity DataFrame.

        Returns
        -------
        pd.DataFrame
            DataFrame with columns: Plant ID, Technology, Installed Capacity (MW),
            Max Capacity (MW), Capacity Fraction.
        """
        return self.installed_plants_df.copy()

    # ----------------------------------------------------------------------------------
    # Problem info accessors
    # ----------------------------------------------------------------------------------

    def get_problem_info(self) -> dict:
        """Get solver problem information.

        Returns
        -------
        dict
            Dictionary with keys: Number of constraints, Number of variables,
            Number of binary variables, Number of objectives, Number of nonzeros.
        """
        return self.problem_info.copy()


def collect_results_from_model(model, solver_result, case_name: str = "run") -> OptimizationResults:
    """Collect all optimization results from a solved Pyomo model.

    This function extracts all relevant results from a solved SDOM model and
    organizes them into an OptimizationResults dataclass. It combines the
    functionality previously split between collect_results() and export_results().

    Parameters
    ----------
    model : pyomo.core.base.PyomoModel.ConcreteModel
        The solved Pyomo model instance.
    solver_result : pyomo.opt.SolverResults
        The solver results object from solver.solve().
    case_name : str, optional
        Case identifier for the scenario column. Defaults to "run".

    Returns
    -------
    OptimizationResults
        A dataclass containing all optimization results.
    """
    logging.info("Collecting SDOM results...")

    results = OptimizationResults()

    # Extract solver information
    results.termination_condition = str(solver_result.solver.termination_condition)
    results.solver_status = str(solver_result.solver.status)

    # Extract problem info
    if solver_result.problem:
        problem = solver_result.problem[0]
        # Helper to extract value from Pyomo ScalarData objects
        def get_value(val):
            if hasattr(val, 'value'):
                return val.value
            return val
        
        results.problem_info = {
            "Number of constraints": get_value(problem.get("Number of constraints", 0)),
            "Number of variables": get_value(problem.get("Number of variables", 0)),
            "Number of binary variables": get_value(problem.get("Number of binary variables", 0)),
            "Number of objectives": get_value(problem.get("Number of objectives", 0)),
            "Number of nonzeros": get_value(problem.get("Number of nonzeros", 0)),
        }

    # Total cost
    results.total_cost = safe_pyomo_value(model.Obj.expr)
    results.gen_mix_target = float(model.GenMix_Target.value)

    # ----------------------------------------------------------------------------------
    # Collect capacity results
    # ----------------------------------------------------------------------------------
    logging.debug("Collecting capacity results...")

    # Generation capacities
    results.capacity = {
        "Thermal": safe_pyomo_value(model.thermal.total_installed_capacity),
        "Solar PV": safe_pyomo_value(model.pv.total_installed_capacity),
        "Wind": safe_pyomo_value(model.wind.total_installed_capacity),
    }
    results.capacity["All"] = (
        results.capacity["Thermal"] + results.capacity["Solar PV"] + results.capacity["Wind"]
    )

    # Storage capacities
    storage_tech_list = list(model.storage.j)

    charge_cap = {}
    discharge_cap = {}
    energy_cap = {}

    for tech in storage_tech_list:
        charge_cap[tech] = safe_pyomo_value(model.storage.Pcha[tech])
        discharge_cap[tech] = safe_pyomo_value(model.storage.Pdis[tech])
        energy_cap[tech] = safe_pyomo_value(model.storage.Ecap[tech])

    charge_cap["All"] = sum(charge_cap[t] for t in storage_tech_list)
    discharge_cap["All"] = sum(discharge_cap[t] for t in storage_tech_list)
    energy_cap["All"] = sum(energy_cap[t] for t in storage_tech_list)

    results.storage_capacity = {
        "charge": charge_cap,
        "discharge": discharge_cap,
        "energy": energy_cap,
    }

    # ----------------------------------------------------------------------------------
    # Collect generation totals
    # ----------------------------------------------------------------------------------
    logging.debug("Collecting generation totals...")

    results.generation_totals = {
        "Thermal": safe_pyomo_value(model.thermal.total_generation),
        "Solar PV": safe_pyomo_value(model.pv.total_generation),
        "Wind": safe_pyomo_value(model.wind.total_generation),
        "Other renewables": safe_pyomo_value(sum(model.other_renewables.ts_parameter[h] for h in model.h)) * safe_pyomo_value(model.other_renewables.alpha),
        "Hydro": safe_pyomo_value(sum(model.hydro.generation[h] for h in model.h)) * safe_pyomo_value(model.hydro.alpha),
        "Nuclear": safe_pyomo_value(sum(model.nuclear.ts_parameter[h] for h in model.h)) * safe_pyomo_value(model.nuclear.alpha),
    }

    # Storage discharge totals
    storage_discharge_total = 0.0
    for tech in storage_tech_list:
        tech_discharge = safe_pyomo_value(sum(model.storage.PD[h, tech] for h in model.h))
        results.generation_totals[tech] = tech_discharge
        storage_discharge_total += tech_discharge

    results.generation_totals["All"] = (
        results.generation_totals["Thermal"]
        + results.generation_totals["Solar PV"]
        + results.generation_totals["Wind"]
        + results.generation_totals["Other renewables"]
        + results.generation_totals["Hydro"]
        + results.generation_totals["Nuclear"]
        + storage_discharge_total
    )

    # ----------------------------------------------------------------------------------
    # Collect cost breakdown
    # ----------------------------------------------------------------------------------
    logging.debug("Collecting cost breakdown...")

    # CAPEX
    capex = {
        "Solar PV": safe_pyomo_value(model.pv.capex_cost_expr),
        "Wind": safe_pyomo_value(model.wind.capex_cost_expr),
        "Thermal": safe_pyomo_value(model.thermal.capex_cost_expr),
    }
    capex["All"] = capex["Solar PV"] + capex["Wind"] + capex["Thermal"]

    # Storage CAPEX
    power_capex = {}
    energy_capex = {}
    for tech in storage_tech_list:
        power_capex[tech] = safe_pyomo_value(model.storage.power_capex_cost_expr[tech])
        energy_capex[tech] = safe_pyomo_value(model.storage.energy_capex_cost_expr[tech])

    power_capex["All"] = sum(power_capex[t] for t in storage_tech_list)
    energy_capex["All"] = sum(energy_capex[t] for t in storage_tech_list)

    # FOM
    fom = {
        "Thermal": safe_pyomo_value(model.thermal.fixed_om_cost_expr),
        "Solar PV": safe_pyomo_value(model.pv.fixed_om_cost_expr),
        "Wind": safe_pyomo_value(model.wind.fixed_om_cost_expr),
    }
    fom_storage_total = 0.0
    for tech in storage_tech_list:
        fom[tech] = safe_pyomo_value(
            MW_TO_KW * model.storage.data["CostRatio", tech] * model.storage.data["FOM", tech] * model.storage.Pcha[tech]
            + MW_TO_KW * (1 - model.storage.data["CostRatio", tech]) * model.storage.data["FOM", tech] * model.storage.Pdis[tech]
        )
        fom_storage_total += fom[tech]
    fom["All"] = fom["Thermal"] + fom["Solar PV"] + fom["Wind"] + fom_storage_total

    # VOM
    vom = {
        "Thermal": safe_pyomo_value(model.thermal.total_vom_cost_expr),
    }
    vom_storage_total = 0.0
    for tech in storage_tech_list:
        vom[tech] = safe_pyomo_value(model.storage.data["VOM", tech] * sum(model.storage.PD[h, tech] for h in model.h))
        vom_storage_total += vom[tech]
    vom["All"] = vom["Thermal"] + vom_storage_total

    # Fuel cost
    fuel_cost = {
        "Thermal": safe_pyomo_value(model.thermal.total_fuel_cost_expr),
    }

    # Imports/Exports costs
    imports_cost = safe_pyomo_value(model.imports.total_cost_expr)
    exports_revenue = safe_pyomo_value(model.exports.total_cost_expr)

    results.cost_breakdown = {
        "capex": capex,
        "power_capex": power_capex,
        "energy_capex": energy_capex,
        "fom": fom,
        "vom": vom,
        "fuel_cost": fuel_cost,
        "imports_cost": imports_cost,
        "exports_revenue": exports_revenue,
    }

    # ----------------------------------------------------------------------------------
    # Build generation DataFrame
    # ----------------------------------------------------------------------------------
    logging.debug("Building generation DataFrame...")

    gen_data = {
        "Scenario": [],
        "Hour": [],
        "Solar PV Generation (MW)": [],
        "Solar PV Curtailment (MW)": [],
        "Wind Generation (MW)": [],
        "Wind Curtailment (MW)": [],
        "All Thermal Generation (MW)": [],
        "Hydro Generation (MW)": [],
        "Nuclear Generation (MW)": [],
        "Other Renewables Generation (MW)": [],
        "Imports (MW)": [],
        "Storage Charge/Discharge (MW)": [],
        "Exports (MW)": [],
        "Load (MW)": [],
        "Net Load (MW)": [],
    }

    for h in model.h:
        solar_gen = safe_pyomo_value(model.pv.generation[h])
        solar_curt = safe_pyomo_value(model.pv.curtailment[h])
        wind_gen = safe_pyomo_value(model.wind.generation[h])
        wind_curt = safe_pyomo_value(model.wind.curtailment[h])
        thermal_gen = sum(safe_pyomo_value(model.thermal.generation[h, bu]) for bu in model.thermal.plants_set)
        hydro = safe_pyomo_value(model.hydro.generation[h])
        nuclear = safe_pyomo_value(model.nuclear.alpha * model.nuclear.ts_parameter[h]) if hasattr(model.nuclear, "alpha") else 0
        other_renewables = safe_pyomo_value(model.other_renewables.alpha * model.other_renewables.ts_parameter[h]) if hasattr(model.other_renewables, "alpha") else 0
        imports = safe_pyomo_value(model.imports.variable[h]) if hasattr(model.imports, "variable") else 0
        exports = safe_pyomo_value(model.exports.variable[h]) if hasattr(model.exports, "variable") else 0
        load = safe_pyomo_value(model.demand.ts_parameter[h]) if hasattr(model.demand, "ts_parameter") else 0
        net_load = safe_pyomo_value(model.net_load[h]) if hasattr(model, "net_load") else 0
        power_to_storage = sum(safe_pyomo_value(model.storage.PC[h, j]) or 0 for j in model.storage.j) - sum(safe_pyomo_value(model.storage.PD[h, j]) or 0 for j in model.storage.j)

        if None not in [solar_gen, solar_curt, wind_gen, wind_curt, thermal_gen, hydro, imports, exports, load]:
            gen_data["Scenario"].append(case_name)
            gen_data["Hour"].append(h)
            gen_data["Solar PV Generation (MW)"].append(solar_gen)
            gen_data["Solar PV Curtailment (MW)"].append(solar_curt)
            gen_data["Wind Generation (MW)"].append(wind_gen)
            gen_data["Wind Curtailment (MW)"].append(wind_curt)
            gen_data["All Thermal Generation (MW)"].append(thermal_gen)
            gen_data["Hydro Generation (MW)"].append(hydro)
            gen_data["Nuclear Generation (MW)"].append(nuclear)
            gen_data["Other Renewables Generation (MW)"].append(other_renewables)
            gen_data["Imports (MW)"].append(imports)
            gen_data["Storage Charge/Discharge (MW)"].append(power_to_storage)
            gen_data["Exports (MW)"].append(exports)
            gen_data["Load (MW)"].append(load)
            gen_data["Net Load (MW)"].append(net_load)

    results.generation_df = pd.DataFrame(gen_data)

    # ----------------------------------------------------------------------------------
    # Build storage DataFrame
    # ----------------------------------------------------------------------------------
    logging.debug("Building storage DataFrame...")

    storage_data = {
        "Hour": [],
        "Technology": [],
        "Charging power (MW)": [],
        "Discharging power (MW)": [],
        "State of charge (MWh)": [],
    }

    for h in model.h:
        for j in model.storage.j:
            charge_power = safe_pyomo_value(model.storage.PC[h, j])
            discharge_power = safe_pyomo_value(model.storage.PD[h, j])
            soc = safe_pyomo_value(model.storage.SOC[h, j])
            if None not in [charge_power, discharge_power, soc]:
                storage_data["Hour"].append(h)
                storage_data["Technology"].append(j)
                storage_data["Charging power (MW)"].append(charge_power)
                storage_data["Discharging power (MW)"].append(discharge_power)
                storage_data["State of charge (MWh)"].append(soc)

    results.storage_df = pd.DataFrame(storage_data)

    # ----------------------------------------------------------------------------------
    # Build thermal generation DataFrame (disaggregated)
    # ----------------------------------------------------------------------------------
    logging.debug("Building thermal generation DataFrame...")

    if len(model.thermal.plants_set) > 1:
        thermal_data = {"Hour": []}
        for plant in model.thermal.plants_set:
            thermal_data[str(plant)] = []

        for h in model.h:
            thermal_data["Hour"].append(h)
            for plant in model.thermal.plants_set:
                thermal_data[str(plant)].append(safe_pyomo_value(model.thermal.generation[h, plant]))

        results.thermal_generation_df = pd.DataFrame(thermal_data)

    # ----------------------------------------------------------------------------------
    # Build installed power plants DataFrame
    # ----------------------------------------------------------------------------------
    logging.debug("Building installed power plants DataFrame...")

    installed_plants_data = {
        "Plant ID": [],
        "Technology": [],
        "Installed Capacity (MW)": [],
        "Max Capacity (MW)": [],
        "Capacity Fraction": [],
    }

    # Solar PV plants
    for plant in model.pv.plants_set:
        installed_cap = safe_pyomo_value(model.pv.plant_installed_capacity[plant])
        max_cap = safe_pyomo_value(model.pv.max_capacity[plant])
        cap_fraction = safe_pyomo_value(model.pv.capacity_fraction[plant])
        installed_plants_data["Plant ID"].append(str(plant))
        installed_plants_data["Technology"].append("Solar PV")
        installed_plants_data["Installed Capacity (MW)"].append(installed_cap)
        installed_plants_data["Max Capacity (MW)"].append(max_cap)
        installed_plants_data["Capacity Fraction"].append(cap_fraction)

    # Wind plants
    for plant in model.wind.plants_set:
        installed_cap = safe_pyomo_value(model.wind.plant_installed_capacity[plant])
        max_cap = safe_pyomo_value(model.wind.max_capacity[plant])
        cap_fraction = safe_pyomo_value(model.wind.capacity_fraction[plant])
        installed_plants_data["Plant ID"].append(str(plant))
        installed_plants_data["Technology"].append("Wind")
        installed_plants_data["Installed Capacity (MW)"].append(installed_cap)
        installed_plants_data["Max Capacity (MW)"].append(max_cap)
        installed_plants_data["Capacity Fraction"].append(cap_fraction)

    # Thermal plants
    for plant in model.thermal.plants_set:
        installed_cap = safe_pyomo_value(model.thermal.plant_installed_capacity[plant])
        max_cap = safe_pyomo_value(model.thermal.data["MaxCapacity", plant])
        # For thermal, capacity fraction is installed/max (there's no explicit fraction variable)
        cap_fraction = installed_cap / max_cap if max_cap > 0 else 0.0
        installed_plants_data["Plant ID"].append(str(plant))
        installed_plants_data["Technology"].append("Thermal")
        installed_plants_data["Installed Capacity (MW)"].append(installed_cap)
        installed_plants_data["Max Capacity (MW)"].append(max_cap)
        installed_plants_data["Capacity Fraction"].append(cap_fraction)

    results.installed_plants_df = pd.DataFrame(installed_plants_data)

    # ----------------------------------------------------------------------------------
    # Build summary DataFrame
    # ----------------------------------------------------------------------------------
    logging.debug("Building summary DataFrame...")

    results.summary_df = _build_summary_dataframe(model, results, storage_tech_list)

    return results


def _build_summary_dataframe(model, results: OptimizationResults, storage_tech_list: list) -> pd.DataFrame:
    """Build the summary DataFrame from results.

    Parameters
    ----------
    model : pyomo.core.base.PyomoModel.ConcreteModel
        The solved Pyomo model instance.
    results : OptimizationResults
        The results object with collected data.
    storage_tech_list : list
        List of storage technology identifiers.

    Returns
    -------
    pd.DataFrame
        Summary DataFrame with metrics.
    """
    from .common.utilities import concatenate_dataframes

    # Total cost
    total_cost = pd.DataFrame.from_dict(
        {"Total cost": [None, 1, results.total_cost, "$US"]},
        orient="index",
        columns=["Technology", "Run", "Optimal Value", "Unit"],
    )
    total_cost = total_cost.reset_index(names="Metric")
    summary_results = total_cost

    # Capacity
    summary_results = concatenate_dataframes(summary_results, results.capacity, run=1, unit="MW", metric="Capacity")

    # Storage capacities
    summary_results = concatenate_dataframes(
        summary_results, results.storage_capacity["charge"], run=1, unit="MW", metric="Charge power capacity"
    )
    summary_results = concatenate_dataframes(
        summary_results, results.storage_capacity["discharge"], run=1, unit="MW", metric="Discharge power capacity"
    )

    # Average power capacity
    avgpocap = {}
    for tech in storage_tech_list:
        avgpocap[tech] = (results.storage_capacity["charge"][tech] + results.storage_capacity["discharge"][tech]) / 2
    avgpocap["All"] = sum(avgpocap[t] for t in storage_tech_list)
    summary_results = concatenate_dataframes(summary_results, avgpocap, run=1, unit="MW", metric="Average power capacity")

    # Energy capacity
    summary_results = concatenate_dataframes(
        summary_results, results.storage_capacity["energy"], run=1, unit="MWh", metric="Energy capacity"
    )

    # Duration
    dis_dur = {}
    for tech in storage_tech_list:
        dis_dur[tech] = safe_pyomo_value(
            sqrt(model.storage.data["Eff", tech]) * model.storage.Ecap[tech] / (model.storage.Pdis[tech] + 1e-15)
        )
    summary_results = concatenate_dataframes(summary_results, dis_dur, run=1, unit="h", metric="Duration")

    # Generation
    summary_results = concatenate_dataframes(
        summary_results, results.generation_totals, run=1, unit="MWh", metric="Total generation"
    )

    # Imports/Exports totals
    imp_exp = {}
    imp_exp["Imports"] = safe_pyomo_value(sum(model.imports.variable[h] for h in model.h)) if hasattr(model.imports, "variable") else 0
    imp_exp["Exports"] = safe_pyomo_value(sum(model.exports.variable[h] for h in model.h)) if hasattr(model.exports, "variable") else 0
    summary_results = concatenate_dataframes(summary_results, imp_exp, run=1, unit="MWh", metric="Total Imports/Exports")

    # Storage discharge
    stodisch = {tech: results.generation_totals.get(tech, 0.0) for tech in storage_tech_list}
    stodisch["All"] = sum(stodisch[t] for t in storage_tech_list)
    summary_results = concatenate_dataframes(summary_results, stodisch, run=1, unit="MWh", metric="Storage energy discharging")

    # Demand
    dem = {"demand": sum(model.demand.ts_parameter[h] for h in model.h)}
    summary_results = concatenate_dataframes(summary_results, dem, run=1, unit="MWh", metric="Total demand")

    # Storage charging
    stoch = {}
    for tech in storage_tech_list:
        stoch[tech] = safe_pyomo_value(sum(model.storage.PC[h, tech] for h in model.h))
    stoch["All"] = sum(stoch[t] for t in storage_tech_list)
    summary_results = concatenate_dataframes(summary_results, stoch, run=1, unit="MWh", metric="Storage energy charging")

    # CAPEX
    summary_results = concatenate_dataframes(
        summary_results, results.cost_breakdown["capex"], run=1, unit="$US", metric="CAPEX"
    )

    # Power CAPEX
    summary_results = concatenate_dataframes(
        summary_results, results.cost_breakdown["power_capex"], run=1, unit="$US", metric="Power-CAPEX"
    )

    # Energy CAPEX
    summary_results = concatenate_dataframes(
        summary_results, results.cost_breakdown["energy_capex"], run=1, unit="$US", metric="Energy-CAPEX"
    )

    # Total CAPEX (storage)
    tcapex = {}
    for tech in storage_tech_list:
        tcapex[tech] = results.cost_breakdown["power_capex"][tech] + results.cost_breakdown["energy_capex"][tech]
    tcapex["All"] = sum(tcapex[t] for t in storage_tech_list)
    summary_results = concatenate_dataframes(summary_results, tcapex, run=1, unit="$US", metric="Total-CAPEX")

    # FOM
    summary_results = concatenate_dataframes(summary_results, results.cost_breakdown["fom"], run=1, unit="$US", metric="FOM")

    # VOM
    summary_results = concatenate_dataframes(summary_results, results.cost_breakdown["vom"], run=1, unit="$US", metric="VOM")

    # Fuel cost
    summary_results = concatenate_dataframes(
        summary_results, results.cost_breakdown["fuel_cost"], run=1, unit="$US", metric="Fuel-Cost"
    )

    # OPEX
    opex = {}
    opex["Thermal"] = results.cost_breakdown["fom"]["Thermal"] + results.cost_breakdown["vom"]["Thermal"]
    opex["Solar PV"] = results.cost_breakdown["fom"]["Solar PV"]
    opex["Wind"] = results.cost_breakdown["fom"]["Wind"]
    opex_storage_total = 0.0
    for tech in storage_tech_list:
        opex[tech] = results.cost_breakdown["fom"][tech] + results.cost_breakdown["vom"][tech]
        opex_storage_total += opex[tech]
    opex["All"] = opex["Thermal"] + opex["Solar PV"] + opex["Wind"] + opex_storage_total
    summary_results = concatenate_dataframes(summary_results, opex, run=1, unit="$US", metric="OPEX")

    # Imports/Exports costs
    cost_revenue = {"Imports Cost": results.cost_breakdown["imports_cost"]}
    summary_results = concatenate_dataframes(summary_results, cost_revenue, run=1, unit="$US", metric="Cost")
    cost_revenue = {"Exports Revenue": results.cost_breakdown["exports_revenue"]}
    summary_results = concatenate_dataframes(summary_results, cost_revenue, run=1, unit="$US", metric="Revenue")

    # Equivalent number of cycles
    cyc = {}
    for tech in storage_tech_list:
        cyc[tech] = safe_pyomo_value(results.generation_totals.get(tech, 0.0) / (model.storage.Ecap[tech] + 1e-15))
    summary_results = concatenate_dataframes(summary_results, cyc, run=1, unit="-", metric="Equivalent number of cycles")

    # VRE Curtailment
    pv_curtailment = safe_pyomo_value(model.pv.total_curtailment) if hasattr(model.pv, "total_curtailment") else 0.0
    wind_curtailment = safe_pyomo_value(model.wind.total_curtailment) if hasattr(model.wind, "total_curtailment") else 0.0
    pv_generation = safe_pyomo_value(model.pv.total_generation) if hasattr(model.pv, "total_generation") else 0.0
    wind_generation = safe_pyomo_value(model.wind.total_generation) if hasattr(model.wind, "total_generation") else 0.0
    
    total_vre_curtailment_mwh = pv_curtailment + wind_curtailment
    total_vre_availability = pv_generation + wind_generation + pv_curtailment + wind_curtailment
    total_vre_curtailment_pct = (total_vre_curtailment_mwh / total_vre_availability * 100) if total_vre_availability > 0 else 0.0
    
    vre_curt_mwh = {"Solar PV": pv_curtailment, "Wind": wind_curtailment, "All": total_vre_curtailment_mwh}
    summary_results = concatenate_dataframes(summary_results, vre_curt_mwh, run=1, unit="MWh", metric="Total VRE curtailment")
    
    vre_curt_pct = {"All": total_vre_curtailment_pct}
    summary_results = concatenate_dataframes(summary_results, vre_curt_pct, run=1, unit="%", metric="VRE curtailment percentage")

    return summary_results
