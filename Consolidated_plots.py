# -*- coding: utf-8 -*-
"""
SDOM Plots — Two-Use-Case 2×2 Dashboard + Annualized System Cost (split by use cases)

• Regular summary files define scenarios (capacity stacks and duration).
• Phase1 summary files are supplementary: they provide transparent dashed-outline outage bars
  layered on top of their matching regular scenarios (a/c capacity panels), paired by filename tag.

Automatic file discovery scans common roots and optional env vars:
  SDOM_BASE_DIR, SDOM_DATA_DIR
Optional explicit override:
  SDOM_SUMMARY_FILES  (semicolon-separated absolute file paths)

Created: Apr 28, 2026
Author: M. Koleva & Copilot

Dependencies:
    - pandas
    - numpy
    - plotly (and kaleido to export PNGs)
"""

import os
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
import plotly.io as pio
import plotly.graph_objects as go
from plotly.subplots import make_subplots


# ---------------------------------------------------------------------------
# Helper functions (simple names; defined at top to avoid NameError issues)
# ---------------------------------------------------------------------------
def infer_tag_from_filename(path_str: str):
    #-> Optional"""Return a simple tag for pairing (e.g., 'PGnE', 'MEA') based on the filename."""
    if not isinstance(path_str, str):
        return None
    name = Path(path_str).name.lower()
    # Remove non-alphanumeric to capture PG&E/PGE/PGnE variants robustly
    norm = "".join(ch for ch in name if ch.isalnum())
    if "pgne" in norm or "pge" in norm:
        return "PGnE"
    if "mea" in norm:
        return "MEA"
    return None


def is_phase1_file(path_str: str) -> bool:
    """Return True if the path contains 'Phase1' (case-insensitive)."""
    if not isinstance(path_str, str):
        return False
    return "phase1" in path_str.lower()


# ---------------------------------------------------------------------------
# Discovery utilities (NO WILDCARDS; exact filename matching)
# ---------------------------------------------------------------------------
def candidate_roots() -> List[Path]:
    """
    Buildlausible search roots:
      • env SDOM_BASE_DIR, SDOM_DATA_DIR
      • current working directory
      • script directory (if running from file)
      • user home
      • ~/Documents, ~/Downloads
    """
    roots: List[Path] = []
    for var in ("SDOM_BASE_DIR", "SDOM_DATA_DIR"):
        val = os.environ.get(var)
        if val:
            try:
                roots.append(Path(val).expanduser().resolve())
            except Exception:
                pass

    # Current working directory
    roots.append(Path.cwd().resolve())

    # Script folder (if __file__ exists)
    try:
        script_dir = Path(__file__).resolve().parent
        roots.append(script_dir)
    except Exception:
        pass

    # User home and common subfolders
    home = Path.home().resolve()
    roots.append(home)
    for sub in ("Documents", "Downloads"):
        p = home / sub
        if p.exists():
            roots.append(p.resolve())

    # De-duplicate while preserving order and only keep existing
    seen = set()
    uniq: List[Path] = []
    for r in roots:
        if r not in seen and r.exists():
            uniq.append(r)
            seen.add(r)
    return uniq


def discover_exact_filenames(
    filenames: List[str],
    roots: Optional[List[Path]] = None,
) -> Tuple[List[Path], List[str]]:
    """
    Discover files by exact basename match (NO wildcards).
    Walk each root recursively with os.walk and match Path(name).name == target filename.

    Returns: (resolved_paths_in_order, unmatched_absolute_hints)
      - Order is preserved based on the order of input 'filenames'.
      - unmatched_absolute_hints shows the first plausible absolute path for user guidance.
    """
    if roots is None:
        roots = candidate_roots()

    resolved_in_order: List[Path] = []
    unmatched: List[str] = []

    for fname in filenames:
        target = fname.strip()
        found_path: Optional[Path] = None

        for root in roots:
            # Walk recursively without using any glob/wildcard
            for dirpath, _dirnames, filenames_in_dir in os.walk(root):
                # Exact basename comparison
                if target in filenames_in_dir:
                    found_path = Path(dirpath) / target
                    break
            if found_path:
                break

        if found_path:
            resolved_in_order.append(found_path.resolve())
        else:
            hint_root = roots[0] if roots else Path.cwd()
            unmatched.append(str((hint_root / target).resolve()))

    # De-duplicate while preserving first occurrence
    seen = set()
    uniq: List[Path] = []
    for p in resolved_in_order:
        if p not in seen:
            uniq.append(p)
            seen.add(p)

    return uniq, unmatched


# ---------------------------------------------------------------------------
# Main plotting class
# ---------------------------------------------------------------------------
class SDOMPlots:
    """
    SDOM plotting utilities:
      • 2×2 dashboard:
          (a) UC1 Capacity  |  (b) UC1 Duration
          (c) UC2 Capacity  |  (d) UC2 Duration
        with transparent Phase1 outage “minimum” bars (black dashed outline) per technology in (a/c),
        paired by filename tag (e.g., PGnE → PGnE).
      • Annualized system cost stacked bars split by use case (left/right).
    """

    def __init__(
        self,
        csv_summary_paths: List[Path],               # resolved paths (regular + Phase1)
        csv_storage_paths: Optional[List[Path]] = None,
        renderer: str = "browser",
        use_cases: Optional[Dict[str, List[str]]] = None,
        outage_requirement_metric_name: str = "Discharge power capacity",
        outage_requirement_techs: Optional[List[str]] = None,   # e.g., ["H2"] or ["H2","Vanadium"]
        outage_source_keyword: str = "Phase1",                  # phase1 marker in filenames
        scenario_labels_map: Optional[Dict[str, str]] = None,   # e.g., {"1": "PGnE — 3 MW, 24 h outage", "2": "MEA — land constrained"}
    ):
        pio.renderers.default = renderer

        # Load data (robust)
        self.df_all, self.loaded_summary, self.missing_summary, self.summary_registry = \
            self._load_summary_data(csv_summary_paths)

        self.df_storage_all, self.loaded_storage, self.missing_storage = \
            self._load_storage_data(csv_storage_paths or [])

        if self.df_all.empty:
            raise ValueError(
                "[Summary] No summary data loaded.\n"
                f"Tried {len(csv_summary_paths)} inputs, found {len(self.loaded_summary)}.\n"
                f"Missing or unreadable: {self.missing_summary}\n"
                "Please verify file paths."
            )

        # Scenario titles from regular (non-Phase1) records.
        # Allow custom overrides via scenario_labels_map.
        regular_scenarios = sorted(
            map(str, self.df_all.loc[self.df_all["__is_phase1__"] == False, "File_Scenario"].unique()),
            key=lambda s: int(s)
        )
        default_titles = {s: f"Scenario {s}" for s in regular_scenarios}
        self.scenario_titles = default_titles if scenario_labels_map is None else {**default_titles, **scenario_labels_map}

        # Colors and markers
        self.color_map = {
            "Li-Ion": "navy",
            "Vanadium": "gold",
            "PHS": "#CC0079",
            "H2": "deepskyblue",
            "GasCC": "#5E1688",
            "Solar PV": "#FFC903",
            "Wind": "#00B6EF",
            "Other renewables": "#32CD32",
            "Hydro": "#187F94",
            "Nuclear": "#820000",
            "Grid": "#9ECE42",
            "Diesel": "darkorange",
        }
        self.marker_symbols = {
            "Li-Ion": "circle",
            "LiIon": "circle",
            "Vanadium": "diamond",
            "PHS": "square",
            "H2": "triangle-up",
            "GasCC": "star",
            "VRB": "hexagon",
            "Diesel": "star",
        }
        self.storage_technologies = ["LiIon", "Li-Ion", "Vanadium", "PHS", "H2"]

        self.plot_config = {
            "displayModeBar": False,
            "staticPlot": True,
            "doubleClick": False,
            "showTips": False,
            "showAxisDragHandles": False,
            "showAxisRangeEntryBoxes": False,
        }

        # Use cases
        self.use_cases = use_cases if use_cases is not None else self._build_default_use_cases()

        # Outage sources
        self.outage_req_metric = outage_requirement_metric_name
        self.outage_requirement_techs = outage_requirement_techs or ["H2","Li-Ion","Vanadium"]
        self.outage_source_keyword = outage_source_keyword

        # Map: each regular scenario → tag (e.g., 1 → PGnE, 2 → MEA)
        self.scenario_to_tag: Dict[str, Optional[str]] = self._build_scenario_to_tag_map()

    # ----------------------- Loaders -----------------------
    def _safe_read_csv(self, path_obj: Path) -> Optional[pd.DataFrame]:
        try:
            df = pd.read_csv(path_obj, encoding="utf-8", on_bad_lines="skip")
            df["__source_file__"] = str(path_obj)
            df["__tag__"] = infer_tag_from_filename(str(path_obj))
            df["__is_phase1__"] = is_phase1_file(str(path_obj))
            return df
        except Exception as e:
            print(f"[ReadCSV] Skipped '{path_obj}': {e}")
            return None

    def _load_summary_data(self, summary_paths: List[Path]) -> Tuple[pd.DataFrame, List[str], List[str], List[Dict]]:
        dfs, loaded, missing, registry = [], [], [], []
        regular_counter = 0

        print("[Summary] Resolved paths:")
        for p in summary_paths:
            print("  →", p)

        for p in summary_paths:
            df = self._safe_read_csv(p)
            if df is None:
                missing.append(str(p))
                continue

            is_phase1 = bool(df["__is_phase1__"].iloc[0]) if "__is_phase1__" in df.columns else False
            tag = df["__tag__"].iloc[0] if "__tag__" in df.columns else None

            if not is_phase1:
                regular_counter += 1
                df["File_Scenario"] = regular_counter
                registry.append({"file": str(p), "scenario": str(regular_counter), "tag": tag, "is_phase1": False})
            else:
                df["File_Scenario"] = -1  # sentinel; Phase1 rows excluded from plots but used for overlays
                registry.append({"file": str(p), "scenario": None, "tag": tag, "is_phase1": True})

            if "Optimal Value" in df.columns:
                df["Optimal Value"] = pd.to_numeric(df.get("Optimal Value"), errors="coerce")

            loaded.append(str(p))
            dfs.append(df)

        if not dfs:
            return pd.DataFrame(), loaded, summary_paths, registry

        combined_df = pd.concat(dfs, ignore_index=True)
        print(f"[Load] Summary: wanted {len(summary_paths)} inputs, loaded {len(loaded)}, missing {len(missing)}")
        return combined_df, loaded, missing, registry

    def _load_storage_data(self, storage_paths: List[Path]) -> Tuple[pd.DataFrame, List[str], List[str]]:
        if not storage_paths:
            return pd.DataFrame(), [], []

        dfs, loaded, missing = [], [], []
        print("[Storage] Resolved paths:")
        for p in storage_paths:
            print("  →", p)

        for i, p in enumerate(storage_paths, start=1):
            try:
                df = pd.read_csv(p, encoding="utf-8", on_bad_lines="skip")
                df["File_Scenario"] = i
                if "State of charge (MWh)" in df.columns:
                    df["State of charge (MWh)"] = pd.to_numeric(df["State of charge (MWh)"], errors="coerce")
                loaded.append(str(p))
                dfs.append(df)
            except Exception as e:
                print(f"[ReadCSV] Skipped '{p}': {e}")
                missing.append(str(p))

        if not dfs:
            return pd.DataFrame(), loaded, storage_paths

        combined_df = pd.concat(dfs, ignore_index=True)
        print(f"[Load] Storage: wanted {len(storage_paths)} inputs, loaded {len(loaded)}, missing {len(missing)}")
        return combined_df, loaded, missing
    
    
    def _text_color_for_bg(self, hex_color):
        """Return black or white text depending on brightness of bar fill color."""
        c = hex_color.lstrip('#')
        r, g, b = int(c[0:2], 16), int(c[2:4], 16), int(c[4:6], 16)
        brightness = (0.299 * r + 0.587 * g + 0.114 * b)
        return "white" if brightness < 150 else "black"

    def _text_color_for_bg(self, hex_color: str) -> str:
        """Return black or white depending on perceived brightness of the bar color."""
        hex_color = hex_color.lstrip("#")
        r = int(hex_color[0:2], 16)
        g = int(hex_color[2:4], 16)
        b = int(hex_color[4:6], 16)
        brightness = 0.299*r + 0.587*g + 0.114*b
        return "white" if brightness < 150 else "black"

    # ----------------------- Defaults & helpers -----------------------
    def _build_default_use_cases(self) -> Dict[str, List[str]]:
        scenarios = sorted(
            map(str, self.df_all.loc[self.df_all["__is_phase1__"] == False, "File_Scenario"].unique()),
            key=lambda s: int(s)
        )
        if len(scenarios) <= 2:
            uc_map = {"Off-grid": [scenarios[0]] if scenarios else [],
                      "Grid": [scenarios[1]] if len(scenarios) > 1 else []}
        else:
            uc_map = {"Off-grid": [s for s in scenarios if int(s) % 2 == 1],
                      "Grid": [s for s in scenarios if int(s) % 2 == 0]}
        print(f"[UseCases] Auto: {uc_map}")
        return uc_map

    def _build_scenario_to_tag_map(self) -> Dict[str, Optional[str]]:
        """Map each regular scenario ID → tag (e.g., 1 → PGnE, 2 → MEA)."""
        mapping: Dict[str, Optional[str]] = {}
        df_regular = self.df_all[self.df_all["__is_phase1__"] == False]
        for scen in df_regular["File_Scenario"].unique():
            tag = df_regular[df_regular["File_Scenario"] == scen]["__tag__"].dropna().astype(str)
            mapping[str(int(scen))] = tag.iloc[0] if not tag.empty else None
        return mapping

    def _convert_units_and_get_label(self, values, base_unit: str = "MWh"):
        try:
            vals = [float(v) for v in values if pd.notna(v)]
        except Exception:
            vals = []
        if not vals:
            return values, base_unit
        mx = max(abs(v) for v in vals)
        if base_unit == "MWh":
            if mx >= 10_000_000:
                return [v / 1_000_000 for v in vals], "TWh"
            elif mx >= 10_000:
                return [v / 1_000 for v in vals], "GWh"
            else:
                return vals, "MWh"
        elif base_unit == "MW":
            if mx >= 10_000_000:
                return [v / 1_000_000 for v in vals], "TW"
            elif mx >= 10_000:
                return [v / 1_000 for v in vals], "GW"
            else:
                return vals, "MW"
        else:
            return vals, base_unit

    def _get_standard_layout(self) -> dict:
        return dict(
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
            xaxis=dict(showgrid=False, zeroline=False),
            yaxis=dict(
                showgrid=True,
                gridcolor="rgba(128,128,128,0.3)",
                zeroline=True,
                zerolinecolor="rgba(128,128,128,0.5)",
                zerolinewidth=1,
            ),
            title=dict(x=0.5, xanchor="center", font=dict(size=16)),
            margin=dict(t=80),
        )

    def _filter_data_by_metric(self, metric: str, exclude_all: bool = True,
                           positive_only: bool = False, keep_zero: bool = False):

    #-> pd.DataFrame:
        """Filter df_all by metric for regular scenarios only; exclude Phase1 rows."""
        df = self.df_all[
            (self.df_all["Metric"].astype(str).str.strip().str.lower() == metric.lower())
            & (self.df_all["__is_phase1__"] == False)
        ].copy()

        if exclude_all and "Technology" in df.columns:
            agg = {"all", "all technologies", "all generation", "all storage"}
            df = df[~df["Technology"].astype(str).str.strip().str.lower().isin(agg)]

        df["Scenario"] = df["File_Scenario"].astype(str)
        df["Optimal Value"] = pd.to_numeric(df["Optimal Value"], errors="coerce").fillna(0.0)

        if positive_only:
            df = df[df["Optimal Value"] > 0]
       # else:
           # df = df[df["Optimal Value"] != 0]
           
        
        if not keep_zero:
            df = df[df["Optimal Value"] != 0]


        return df

    def _cost_unit_and_factor(self, values_usd):
        vals = [float(v) for v in values_usd if pd.notna(v)]
        if not vals:
            return "US$", 1.0
        mx = max(abs(v) for v in vals)
        if mx >= 1_000_000_000:
            return "US$B", 1e-9
        elif mx >= 1_000_000:
            return "US$M", 1e-6
        else:
            return "US$", 1.0

    # ----------------------- Legend helper for overlay -----------------------
    def _add_outage_legend_item(self, fig, row: int, col: int, axis_index: int,
                                label: str, line_color: str, line_width: int, line_dash: str):
        """
        Add an invisible scatter line so the overlay gets a legend entry.
        Shapes (rectangles) don't appear in the legend, so we add a dummy trace with showlegend=True.
        """
        xaxis = f"x{axis_index}" if axis_index > 1 else "x"
        yaxis = f"y{axis_index}" if axis_index > 1 else "y"

        fig.add_trace(
            go.Scatter(
                x=[0, 0], y=[0, 0],
                mode="lines",
                name=label,
                showlegend=True,
                line=dict(color=line_color, width=line_width, dash=line_dash),
                opacity=1.0,        # invisible on plot; just for legend
                hoverinfo="skip",
            ),
            row=row, col=col
        )
        # Bind the dummy trace to the target axes (keeps legend aligned with the panel)
        fig.update_traces(xaxis=xaxis, yaxis=yaxis, selector=dict(name=label))

    # -------------------------------------------------------------------------
    # 2×2 Dashboard with transparent Phase1 outage overlay bars (a/c)
    # -------------------------------------------------------------------------
    def create_use_case_capacity_duration_dashboard(
        self,
        title: str = "",
        filename: str = "use_case_capacity_duration_dashboard.png",
        x_axis_font_size: int = 22, y_axis_font_size: int = 22,
        legend_font_size: int = 20,
        height: int = 1200, width: int = 1800,
        uniform_text_size: int = 16,
        use_cases: Optional[Dict[str, List[str]]] = None,
        sort_scenarios: str = "numeric",
        bar_half_height: float = 0.4,
        outage_outline_color: str = "black",
        outage_outline_width: int = 2,
        outage_dash: str = "dash",
        outage_legend_label: str = "Storage dedicated to outage",
    ):
        # Data (regular only)
        df_cap = self._filter_data_by_metric("Discharge power capacity", keep_zero=True)

        df_diesel = self.df_all[
            (self.df_all["Metric"].str.strip().str.lower() == "capacity") &
            (self.df_all["Technology"].str.strip().str.lower() == "diesel") &
            (self.df_all["__is_phase1__"] == False)
        ].copy()
        
        df_diesel["Optimal Value"] = pd.to_numeric(df_diesel["Optimal Value"], errors="coerce").fillna(0.0)
        df_diesel["Scenario"] = df_diesel["File_Scenario"].astype(str)
        
        # Keep only Diesel columns needed for capacity plotting
        df_diesel = df_diesel[["Scenario", "Technology", "Optimal Value"]]
        
        # Append Diesel to df_cap (storage discharge capacities)
        df_cap = pd.concat([df_cap, df_diesel], ignore_index=True)


        df_dur = self._filter_data_by_metric("Discharge duration")
        if df_cap.empty:
            print("[Dashboard] No 'Discharge power capacity' data (regular).")
            return None
        if df_dur.empty:
            print("[Dashboard] No 'Discharge duration' data (regular).")
            return None

        tech_alias = {"LiIon": "Li-Ion", "VRB": "Vanadium"}
        for df_ in (df_cap, df_dur):
            df_["Technology"] = df_["Technology"].replace(tech_alias)

        # Use cases
        uc_map = use_cases if use_cases is not None else self.use_cases
        if not isinstance(uc_map, dict) or len(uc_map) != 2:
            raise ValueError("Provide exactly two use cases: {'Use Case 1': [...], 'Use Case 2': [...]}")

        (uc1_name, uc1_scenarios), (uc2_name, uc2_scenarios) = list(uc_map.items())
        uc1_scenarios = list(map(str, uc1_scenarios))
        uc2_scenarios = list(map(str, uc2_scenarios))

        # Keep scenarios present in both regular metrics
        reg_caps = set(df_cap["Scenario"].unique())
        reg_durs = set(df_dur["Scenario"].unique())
        uc1_scenarios = [s for s in uc1_scenarios if s in reg_caps and s in reg_durs]
        uc2_scenarios = [s for s in uc2_scenarios if s in reg_caps and s in reg_durs]
        if sort_scenarios == "numeric":
            uc1_scenarios = sorted(uc1_scenarios, key=lambda s: int(s))
            uc2_scenarios = sorted(uc2_scenarios, key=lambda s: int(s))

        # Numeric Y positions (enables dashed rectangle outlines)
        uc1_positions = list(range(len(uc1_scenarios)))
        uc2_positions = list(range(len(uc2_scenarios)))
        
        max_rows = max(len(uc1_positions), len(uc2_positions))
        uniform_y_range = [-0.5, max_rows - 0.5]
        
        uc1_labels = [self.scenario_titles.get(s, s) for s in uc1_scenarios]
        uc2_labels = [self.scenario_titles.get(s, s) for s in uc2_scenarios]

        # Technologies order for capacity stacks
        technologies = sorted(
            df_cap["Technology"].unique(),
            key=lambda t: df_cap[df_cap["Technology"] == t]["Optimal Value"].max(),
            reverse=True,
        )
        
        
        if "Diesel" in technologies:
            technologies = ["Diesel"] + [t for t in technologies if t != "Diesel"]


        # Units (shared across capacity panels)
        all_cap_values = df_cap["Optimal Value"].tolist()
        _, cap_unit_label = self._convert_units_and_get_label(all_cap_values, "MW")
        scale_map = {"MW": 1.0, "GW": 1 / 1_000, "TW": 1 / 1_000_000}
        cap_conversion = scale_map.get(cap_unit_label, 1.0)

        # Subplots
        fig = make_subplots(
            rows=2, cols=2, shared_xaxes=False, shared_yaxes=False,
            vertical_spacing=0.12, horizontal_spacing=0.08,
            specs=[[{"type": "xy"}, {"type": "xy"}], [{"type": "xy"}, {"type": "xy"}]],
            subplot_titles=(
                f"a. {uc1_name} — Power Capacity",
                f"b. {uc1_name} — Duration",
                f"c. {uc2_name} — Power Capacity",
                f"d. {uc2_name} — Duration",
            ),
        )

        # Build Phase1 overlay map: (tag, tech) → outage minimum value
        df_phase1 = self.df_all[
            (self.df_all["__is_phase1__"] == True) &
            (self.df_all["Metric"].astype(str).str.strip().str.lower() == self.outage_req_metric.lower()) &
            (self.df_all["__source_file__"].astype(str).str.contains(self.outage_source_keyword, case=False, na=False))
        ].copy()
        df_phase1["Technology"] = df_phase1["Technology"].astype(str)
        df_phase1["Optimal Value"] = pd.to_numeric(df_phase1["Optimal Value"], errors="coerce").fillna(0.0)
        df_phase1["Technology"] = df_phase1["Technology"].replace({"LiIon": "Li-Ion", "VRB": "Vanadium"})
        # Tag per Phase1 row
        df_phase1["__tag__"] = df_phase1["__source_file__"].apply(infer_tag_from_filename)

        # (tag, tech) → value (if multiple rows, last occurrence wins)
        phase1_overlay: Dict[Tuple[str, str], float] = {}
        for _, r in df_phase1.iterrows():
            tag = r["__tag__"]
            tech = str(r["Technology"])
            val = float(r["Optimal Value"])
            if tag is None or tech not in self.outage_requirement_techs:
                continue
            phase1_overlay[(tag, tech)] = val

        # Rectangle overlay helper — return flag if any rectangles were added
        def _add_phase1_outage_rects(axis_index: int, scenarios: List[str], positions: List[int]) -> bool:
            xref = f"x{axis_index}" if axis_index > 1 else "x"
            yref = f"y{axis_index}" if axis_index > 1 else "y"
            any_rect = False
            for s, y in zip(scenarios, positions):
                tag = self.scenario_to_tag.get(s)
                if not tag:
                    continue
                for tech in self.outage_requirement_techs:
                    v = phase1_overlay.get((tag, tech), 0.0) * cap_conversion
                    if v <= 0:
                        continue
                    fig.add_shape(
                        type="rect",
                        xref=xref, yref=yref,
                        x0=0.0, x1=v,
                        y0=y - bar_half_height, y1=y + bar_half_height,
                        line=dict(color=outage_outline_color, width=outage_outline_width, dash=outage_dash),
                        fillcolor="rgba(0,0,0,0)",  # transparent
                        layer="above",
                    )
                    any_rect = True
            return any_rect

        # Capacity panels (a/c): Phase1 rectangles + regular stacks
        def _add_capacity_panel(scenarios: List[str], positions: List[int], labels: List[str],
                                row: int, col: int, show_legend: bool, axis_index: int):
            # Transparent Phase1 outage bars (paired by tag)
            any_rect = _add_phase1_outage_rects(axis_index, scenarios, positions)

            # Add a single legend entry (only in the first capacity panel where show_legend=True)
            if any_rect and show_legend:
                self._add_outage_legend_item(
                    fig=fig, row=row, col=col, axis_index=axis_index,
                    label=outage_legend_label, line_color=outage_outline_color,
                    line_width=outage_outline_width, line_dash=outage_dash
                )

            # Regular capacity stacks
            for tech in technologies:
                vals = []
                for s in scenarios:
                    row_df = df_cap[(df_cap["Scenario"] == s) & (df_cap["Technology"] == tech)]
                    val = float(row_df["Optimal Value"].iloc[0]) * cap_conversion if not row_df.empty else 0.0
                    vals.append(val)
                text_vals = [f"{v:.1f}" if v > 0 else "" for v in vals]
                fig.add_trace(
                    go.Bar(
                        x=vals, y=positions, name=tech, orientation="h",
                        marker_color=self.color_map.get(tech, "#808080"),
                        text=text_vals, texttemplate="%{text}", textposition="inside",
                        textfont=dict(color="black", size=uniform_text_size, family="Arial"),
                        insidetextanchor="middle", constraintext="none",
                        hoverinfo="skip", legendgroup=f"cap_{tech}", showlegend=show_legend,
                    ),
                    row=row, col=col
                )

            # Y tick labels (capacity panels show scenario labels)
            fig.update_yaxes(tickmode="array", tickvals=positions, ticktext=labels, row=row, col=col)

        # (a) UC1 capacity → axis_index 1
        _add_capacity_panel(uc1_scenarios, uc1_positions, uc1_labels, row=1, col=1, show_legend=True, axis_index=1)
        # (c) UC2 capacity → axis_index 3
        _add_capacity_panel(uc2_scenarios, uc2_positions, uc2_labels, row=2, col=1, show_legend=False, axis_index=3)

        # Duration panels (b/d) — NO y-axis labels/ticks
        def _add_duration_panel(scenarios: List[str], positions: List[int], labels: List[str], row: int, col: int):
            scen_pos = {s: p for s, p in zip(scenarios, positions)}
            
            dur_techs_sorted = sorted(df_dur["Technology"].unique())
            
            # Compute the spread of durations (min–max) for this scenario group
            scenario_durations = []
            for tech in dur_techs_sorted:
                vals = df_dur[df_dur["Technology"] == tech]["Optimal Value"].tolist()
                scenario_durations.extend(vals)
            if scenario_durations:
                dur_range = max(scenario_durations) - min(scenario_durations)
            else:
                dur_range = 0
            
            # Base jitter scales dynamically: more jitter if durations cluster
            base_jitter = 0.5 if dur_range > 2 else 0.35 if dur_range > 0.5 else 0.55
            
            marker_offsets = np.linspace(-base_jitter, base_jitter, len(dur_techs_sorted))
            tech_to_offset = dict(zip(dur_techs_sorted, marker_offsets))

            for tech in dur_techs_sorted:
                tdf = df_dur[df_dur["Technology"] == tech]
                xs, ys, texts = [], [], []
                for s in scenarios:
                    r = tdf[tdf["Scenario"] == s]
                    if not r.empty:
                        val = float(r["Optimal Value"].iloc[0])
                        xs.append(val)
                        ys.append(scen_pos[s] + tech_to_offset[tech])
                        texts.append(f"{val:.1f}")
                if xs:
                    fig.add_trace(
                        go.Scatter(
                            x=xs, y=ys, mode="markers+text",
                            text=texts, textposition="middle right",
                            textfont=dict(size=18, color="black", family="Arial"),   # ← NEW
                            name=tech, showlegend=False,
                            marker=dict(
                                color=self.color_map.get(tech, "#808080"),
                                size=16,
                                symbol=self.marker_symbols.get(tech, "circle"),
                                line=dict(width=1, color="black"),
                            ),
                            hovertemplate="<b>%{text} h</b>",
                            ),
                        row=row, col=col
                    )
            # Intentionally no y tick labels on duration panels

        # (b) UC1 duration
        _add_duration_panel(uc1_scenarios, uc1_positions, uc1_labels, row=1, col=2)
        # (d) UC2 duration
        _add_duration_panel(uc2_scenarios, uc2_positions, uc2_labels, row=2, col=2)

        # Ranges & layout
        def _cap_total(scenarios: List[str]) -> float:
            return max((df_cap[df_cap["Scenario"] == s]["Optimal Value"].sum() * cap_conversion for s in scenarios), default=0.0)


        cap_x_max_uc1 = _cap_total(uc1_scenarios)
        cap_x_max_uc2 = _cap_total(uc2_scenarios)
        
        cap_x_pad_uc1 = 0.15 * cap_x_max_uc1 if cap_x_max_uc1 > 0 else 1.0
        cap_x_pad_uc2 = 0.15 * cap_x_max_uc2 if cap_x_max_uc2 > 0 else 1.0


        # Capacity x/y (keep y title for capacity panels)
        for r, c, positions in [(1, 1, uc1_positions), (2, 1, uc2_positions)]:

            fig.update_xaxes(
                title=f"Discharge Storage Power Capacity ({cap_unit_label})",
                range=[0, cap_x_max_uc1 + cap_x_pad_uc1],
                showgrid=True,
                gridcolor="rgba(128,128,128,0.25)",
                tickfont=dict(size=x_axis_font_size, color="black"),
                title_font=dict(color="black", size=x_axis_font_size + 6),
                row=1, col=1
            )
            
            # --- Subfigure c: UC2 capacity (row 2, col 1) ---
            fig.update_xaxes(
                title=f"Discharge Storage Power Capacity ({cap_unit_label})",
                range=[0, cap_x_max_uc2 + cap_x_pad_uc2],
                showgrid=True,
                gridcolor="rgba(128,128,128,0.25)",
                tickfont=dict(size=x_axis_font_size, color="black"),
                title_font=dict(color="black", size=x_axis_font_size + 6),
                row=2, col=1
            )

            # fig.update_yaxes(title="", showgrid=False,
            #                  range=[-0.5, (positions[-1] if positions else 0) + 0.5],
            #                  tickfont=dict(size=y_axis_font_size, color="black"),
            #                  title_font=dict(color="black", size=y_axis_font_size + 6),
            #                  row=r, col=c)
            
            fig.update_yaxes(
                                title="",
                                showgrid=False,
                                range=uniform_y_range,              # ← use uniform range
                                tickfont=dict(size=y_axis_font_size, color="black"),
                                row=r, col=c
                            )

        # Duration x/y — NO y-axis title or tick labels on b/d
        dur_x_max = float(df_dur["Optimal Value"].max()) if not df_dur.empty else 10.0
        dur_x_range = [-2, max(dur_x_max * 1.25, 10.0)]
        for r, c, positions in [(1, 2, uc1_positions), (2, 2, uc2_positions)]:
            fig.update_xaxes(title="", range=dur_x_range,
                             showgrid=True, gridcolor="rgba(0,0,0,0.08)",
                             zeroline=False, tickfont=dict(size=x_axis_font_size, color="black"),
                             title_font=dict(color="black", size=x_axis_font_size + 6),
                             row=r, col=c)
            fig.update_yaxes(
                title="",
                showgrid=False,
                range=uniform_y_range,              # ← use uniform range
                tickfont=dict(size=y_axis_font_size, color="black"),
                row=r, col=c
            )

        layout_settings = self._get_standard_layout()
        layout_settings.update({
            "title": {"text": title, "x": 0.5, "y": 0.98, "font": dict(size=28, color="black")},
            "height": height, "width": width,
            "barmode": "stack",
            # Legend at TOP; plenty of margin so it fits
            "legend": {
                "orientation": "h",
                "x": 0.5, "xanchor": "center",
                "y": 1.08, "yanchor": "bottom",
                "font": dict(color="black", size=legend_font_size),
                "itemsizing": "constant",
                "itemwidth": 60,
                "traceorder": "normal",
                "bgcolor": "rgba(255,255,255,0)"
            },
            # more top margin so legend doesn't clip
            "margin": dict(t=140, b=80, l=180, r=60),
            "paper_bgcolor": "white", "plot_bgcolor": "white",
            "uniformtext": {"minsize": uniform_text_size, "mode": "show"},
        })
        fig.update_layout(**layout_settings)

        try:
            fig.write_image(filename, width=width, height=height)
            print(f"[Dashboard] Saved {filename}")
        except Exception as e:
            html_fallback = Path(filename).with_suffix(".html")
            fig.write_html(str(html_fallback), include_plotlyjs="cdn")
            print(f"[Dashboard] PNG export failed ({e}). Fallback HTML saved: {html_fallback}")

        return fig

    # -------------------------------------------------------------------------
    # Annualized System Cost split by use case (side-by-side, regular only)
    # -------------------------------------------------------------------------
    def create_system_cost_stacked_bar_by_use_case(
        self,
        title: str = "",
        filename: str = "cost_components_by_use_case.png",
        height: int = 900, width: int = 1800,
        legend_font_size: int = 18, axis_title_size: int = 22,
        tick_font_size: int = 14, title_font_size: int = 26,
        sort_scenarios: str = "numeric",
        include_components: Optional[List[str]] = None,
        component_colors: Optional[Dict[str, str]] = None,
    ):
        df = self.df_all[self.df_all["__is_phase1__"] == False].copy()
        if df.empty:
            print("[Cost] No regular summary data loaded.")
            return None

        df["Optimal Value"] = pd.to_numeric(df["Optimal Value"], errors="coerce").fillna(0.0)
        df["Scenario"] = df["File_Scenario"].astype(str)
        tech_alias = {"LiIon": "Li-Ion", "VRB": "Vanadium"}
        df["Technology"] = df["Technology"].replace(tech_alias)
        df["Technology"] = df["Technology"].astype(str)

        uc_map = self.use_cases
        if not isinstance(uc_map, dict) or len(uc_map) != 2:
            raise ValueError("Provide exactly two use cases: {'Use Case 1': [...], 'Use Case 2': [...]}")

        (uc1_name, uc1_scenarios), (uc2_name, uc2_scenarios) = list(uc_map.items())
        uc1_scenarios = list(map(str, uc1_scenarios))
        uc2_scenarios = list(map(str, uc2_scenarios))

        storage_set = set(self.storage_technologies) | {"Li-Ion"}

        def _not_agg(ser):
            return ~ser.astype(str).str.strip().str.lower().str.startswith("all")

        gen_capex = df[(df["Metric"] == "CAPEX") & (~df["Technology"].isin(storage_set)) & _not_agg(df["Technology"])].groupby("Scenario")["Optimal Value"].sum()
        sto_capex = df[(df["Metric"] == "Total Capex") & (df["Technology"].isin(storage_set)) & _not_agg(df["Technology"])].groupby("Scenario")["Optimal Value"].sum()

        # FOM / VOM aggregation: prefer 'all technologies'; otherwise sum non-aggregated rows
        tech_lower = df["Technology"].str.lower()
        fom_all = df[(df["Metric"] == "FOM") & (tech_lower == "all technologies")].set_index("Scenario")["Optimal Value"]
        if fom_all.empty:
            fom_all = df[(df["Metric"] == "FOM") & _not_agg(df["Technology"])].groupby("Scenario")["Optimal Value"].sum()

        # --- Split VOM components ---
        vom_grid_imports = (
            df[(df["Metric"]=="VOM") & (df["Technology"]=="Grid Imports")]
            .set_index("Scenario")["Optimal Value"]
        )
        
        vom_grid_exports = (
            df[(df["Metric"]=="VOM") & (df["Technology"]=="Grid Exports")]
            .set_index("Scenario")["Optimal Value"]
        )
        
        # All VOM rows except Grid Imports/Exports
        vom_other = df[
            (df["Metric"]=="VOM") &
            (~df["Technology"].isin(["Grid Imports", "Grid Exports"])) &
            _not_agg(df["Technology"])
        ].groupby("Scenario")["Optimal Value"].sum()
        
        # If any scenario is missing a component, fill with zero
        def _align(series):
            return series.reindex(df["Scenario"].unique().astype(str), fill_value=0.0)
        
        vom_grid_imports = _align(vom_grid_imports)
        vom_grid_exports = _align(vom_grid_exports)
        vom_other         = _align(vom_other)


        components_default = ["Generation CAPEX", "Storage CAPEX", "FOM", "VOM", "Grid"]
        components = include_components if include_components else components_default

        def _tidy(case_scenarios: List[str]) -> pd.DataFrame:
            scens = [s for s in case_scenarios if s in df["Scenario"].unique()]
            if sort_scenarios == "numeric":
                scens = sorted(scens, key=lambda s: int(s))
            return pd.DataFrame({
                "Scenario": scens,
                "Label": [self.scenario_titles.get(s, s) for s in scens],
                "Generation CAPEX": [float(gen_capex.get(s, 0.0)) for s in scens],
                "Storage CAPEX":    [float(sto_capex.get(s, 0.0)) for s in scens],
                "FOM":              [float(fom_all.get(s, 0.0))   for s in scens],
                "VOM":              [float(vom_other.get(s, 0.0))   for s in scens],
                "Grid":             [float(vom_grid_imports.get(s, 0.0))   for s in scens],
            })

        tidy_uc1 = _tidy(uc1_scenarios)
        tidy_uc2 = _tidy(uc2_scenarios)

        # Collect all values across components for unit scaling
        all_vals = []
        if not tidy_uc1.empty:
            all_vals += tidy_uc1[components].to_numpy().ravel().tolist()
        if not tidy_uc2.empty:
            all_vals += tidy_uc2[components].to_numpy().ravel().tolist()

        unit_label, scale = self._cost_unit_and_factor(all_vals)

        comp_colors = {
            "Generation CAPEX": "deepskyblue",
            "Storage CAPEX":    "darkorange",
            "FOM":              "lightseagreen",
            "VOM":              "gold",
            "Grid":             "navy"
        }
        if component_colors:
            comp_colors.update(component_colors)

        fig = make_subplots(
            rows=1, cols=2, shared_yaxes=False, horizontal_spacing=0.10,
            subplot_titles=(f"a. {uc1_name}", f"b. {uc2_name}"),
        )

        def _add_cost_column(tidy_df: pd.DataFrame, col_index: int, show_legend: bool):
            if tidy_df.empty:
                fig.add_annotation(
                    text="No scenarios for this use case",
                    x=0.5, y=0.5, xref="x domain", yref="y domain",
                    showarrow=False, font=dict(size=14, color="grey"),
                    row=1, col=col_index
                )
                return
            totals_scaled = (tidy_df[components].sum(axis=1) * scale).tolist()
            y_max = max(totals_scaled) if totals_scaled else 0.0
            y_pad = 0.12 * y_max

            fig.update_yaxes(
                title=dict(text=f"Annualized Cost ({unit_label})", font=dict(size=axis_title_size, color="black")),
                range=[0, y_max + y_pad],
                showgrid=True, gridcolor="rgba(0,0,0,0.1)",
                zeroline=False, tickfont=dict(size=tick_font_size, color="black"),
                row=1, col=col_index
            )
            fig.update_xaxes(
                title=dict(text="", font=dict(size=axis_title_size, color="black")),
                showgrid=False, zeroline=False, tickfont=dict(size=tick_font_size, color="black"),
                row=1, col=col_index
            )

            labels = tidy_df["Label"].tolist()
            for comp in components:
                y_vals = (tidy_df[comp] * scale).tolist()
                text_vals = [f"{v:,.1f}" if v > 0 else "" for v in y_vals]
                fig.add_trace(
                    go.Bar(
                        x=labels, y=y_vals, name=comp,
                        marker=dict(color=comp_colors.get(comp, "#808080"),
                                    line=dict(color="rgba(0,0,0,0.18)", width=1)),
                        text=text_vals, texttemplate="%{text}", textposition="inside", insidetextanchor="middle",
                        textfont=dict(color="black", size=12),
                        hovertemplate="<b>%{x}</b><br>" + comp + ": %{y:,.1f} " + unit_label + "<extra></extra>",
                        showlegend=show_legend, cliponaxis=False,
                    ),
                    row=1, col=col_index
                )

        _add_cost_column(tidy_uc1, col_index=1, show_legend=True)
        _add_cost_column(tidy_uc2, col_index=2, show_legend=False)

        fig.update_layout(
            title=dict(text=title, x=0.5, y=0.98, font=dict(size=title_font_size, color="black")),
            barmode="stack", height=height, width=width,
            # Legend at TOP to fit cleanly
            legend=dict(
                orientation="h",
                x=0.5, xanchor="center",
                y=1.08, yanchor="bottom",
                font=dict(size=legend_font_size, color="black"),
                itemsizing="constant",
                itemwidth=60,
                traceorder="normal"
            ),
            margin=dict(t=130, r=60, b=110, l=80),
            paper_bgcolor="white", plot_bgcolor="white",
            uniformtext=dict(minsize=10, mode="show"),
        )

        try:
            fig.write_image(filename, width=width, height=height)
            print(f"[Cost] Saved {filename}")
        except Exception as e:
            html_fallback = Path(filename).with_suffix(".html")
            fig.write_html(str(html_fallback), include_plotlyjs="cdn")
            print(f"[Cost] PNG export failed ({e}). Fallback HTML saved: {html_fallback}")
        return fig

    # Convenience bundle
    def create_all_plots(self):
        print("=" * 60)
        print("CREATING DASHBOARD + COST BY USE CASE")
        print("=" * 60)
        self.create_use_case_capacity_duration_dashboard()
        self.create_system_cost_stacked_bar_by_use_case()
        print("=" * 60)
        print("DONE")
        print("=" * 60)


# =============================================================================
# MAIN — automatic path discovery (NO wildcards; exact filename list)
# =============================================================================
def main():
    # 0) Optional explicit overrides via env var (semicolon-separated absolute files)
    summary_override = os.environ.get("SDOM_SUMMARY_FILES", "").strip()
    if summary_override:
        summary_paths = [Path(p).expanduser().resolve() for p in summary_override.split(";") if p.strip()]
        storage_paths: List[Path] = []
    else:
        # 1) Exact filenames (NO WILDCARDS). Order matters.
        #    — Regular scenarios (PGnE → 1, MEA → 2)
        #    — Phase1 overlays (PGnE, MEA) for transparent dashed outage rectangles
        exact_filenames_summary = [
            # Regular PGnE / MEA variants
            "2030_OutputSummary_SDOM_PGnE_Target_0.00_Resilience_1.00_Outage_24.00hrs_Recovery_0.00hrs_diesel_3MW.csv",
            "2030_OutputSummary_SDOM_PGnE_Target_0.00_Resilience_1.00_Outage_24.00hrs_Recovery_24.00hrs_3MW.csv",
            "2030_OutputSummary_SDOM_PGnE_Target_0.00_Resilience_1.00_Outage_48.00hrs_Recovery_0.00hrs_diesel_3MW.csv",
            "2030_OutputSummary_SDOM_PGnE_Target_0.00_Resilience_1.00_Outage_48.00hrs_Recovery_48.00hrs_3MW.csv",
            "2030_OutputSummary_SDOM_PGnE_Target_0.00_Resilience_1.00_Outage_72.00hrs_Recovery_0.00hrs_diesel_3MW.csv",
            "2030_OutputSummary_SDOM_PGnE_Target_0.00_Resilience_1.00_Outage_72.00hrs_Recovery_72.00hrs_3MW.csv",
            
            "2030_OutputSummary_SDOM_PGnE_Target_0.00_Resilience_1.00_Outage_24.00hrs_Recovery_0.00hrs_diesel_actual.csv",
            "2030_OutputSummary_SDOM_PGnE_Target_0.00_Resilience_1.00_Outage_24.00hrs_Recovery_24.00hrs_actual.csv",
            "2030_OutputSummary_SDOM_PGnE_Target_0.00_Resilience_1.00_Outage_48.00hrs_Recovery_0.00hrs_diesel_actual.csv",
            "2030_OutputSummary_SDOM_PGnE_Target_0.00_Resilience_1.00_Outage_48.00hrs_Recovery_48.00hrs_actual.csv",
            "2030_OutputSummary_SDOM_PGnE_Target_0.00_Resilience_1.00_Outage_72.00hrs_Recovery_0.00hrs_diesel_actual.csv",
            "2030_OutputSummary_SDOM_PGnE_Target_0.00_Resilience_1.00_Outage_72.00hrs_Recovery_72.00hrs_actual.csv",
            
            "2030_OutputSummary_SDOM_MEA_Target_0.00_Resilience_1.00_Outage_24.00hrs_Recovery_0.00hrs_diesel_land_constr.csv",
            "2030_OutputSummary_SDOM_MEA_Target_0.00_Resilience_1.00_Outage_24.00hrs_Recovery_24.00hrs_land_constr.csv",
            "2030_OutputSummary_SDOM_MEA_Target_0.00_Resilience_1.00_Outage_48.00hrs_Recovery_0.00hrs_diesel_land_constr.csv",
            "2030_OutputSummary_SDOM_MEA_Target_0.00_Resilience_1.00_Outage_48.00hrs_Recovery_48.00hrs_land_constr.csv",
            
            "2030_OutputSummary_SDOM_MEA_Target_0.00_Resilience_1.00_Outage_24.00hrs_Recovery_0.00hrs_diesel_noland_constr.csv",
            "2030_OutputSummary_SDOM_MEA_Target_0.00_Resilience_1.00_Outage_24.00hrs_Recovery_24.00hrs_noland_constr.csv",
            "2030_OutputSummary_SDOM_MEA_Target_0.00_Resilience_1.00_Outage_48.00hrs_Recovery_0.00hrs_diesel_noland_constr.csv",
            "2030_OutputSummary_SDOM_MEA_Target_0.00_Resilience_1.00_Outage_48.00hrs_Recovery_48.00hrs_noland_constr.csv",


            # Supplementary Phase1 overlays
            "2030_OutputSummary_Phase1_SDOM_PGnE_Target_0.00_Resilience_1.00_Outage_24.00hrs_Recovery_0.00hrs_diesel_3MW.csv",
            "2030_OutputSummary_Phase1_SDOM_PGnE_Target_0.00_Resilience_1.00_Outage_24.00hrs_Recovery_24.00hrs_3MW.csv",
            "2030_OutputSummary_Phase1_SDOM_PGnE_Target_0.00_Resilience_1.00_Outage_48.00hrs_Recovery_0.00hrs_diesel_3MW.csv",
            "2030_OutputSummary_Phase1_SDOM_PGnE_Target_0.00_Resilience_1.00_Outage_48.00hrs_Recovery_48.00hrs_3MW.csv",
            "2030_OutputSummary_Phase1_SDOM_PGnE_Target_0.00_Resilience_1.00_Outage_72.00hrs_Recovery_0.00hrs_diesel_3MW.csv",
            "2030_OutputSummary_Phase1_SDOM_PGnE_Target_0.00_Resilience_1.00_Outage_72.00hrs_Recovery_72.00hrs_3MW.csv",
            
            "2030_OutputSummary_Phase1_SDOM_PGnE_Target_0.00_Resilience_1.00_Outage_24.00hrs_Recovery_0.00hrs_diesel_actual.csv",
            "2030_OutputSummary_Phase1_SDOM_PGnE_Target_0.00_Resilience_1.00_Outage_24.00hrs_Recovery_24.00hrs_actual.csv",
            "2030_OutputSummary_Phase1_SDOM_PGnE_Target_0.00_Resilience_1.00_Outage_48.00hrs_Recovery_0.00hrs_diesel_actual.csv",
            "2030_OutputSummary_Phase1_SDOM_PGnE_Target_0.00_Resilience_1.00_Outage_48.00hrs_Recovery_48.00hrs_actual.csv",
            "2030_OutputSummary_Phase1_SDOM_PGnE_Target_0.00_Resilience_1.00_Outage_72.00hrs_Recovery_0.00hrs_diesel_actual.csv",
            "2030_OutputSummary_Phase1_SDOM_PGnE_Target_0.00_Resilience_1.00_Outage_72.00hrs_Recovery_72.00hrs_actual.csv",

            "2030_OutputSummary_Phase1_SDOM_MEA_Target_0.00_Resilience_1.00_Outage_24.00hrs_Recovery_0.00hrs_diesel_land_constr.csv",
            "2030_OutputSummary_Phase1_SDOM_MEA_Target_0.00_Resilience_1.00_Outage_24.00hrs_Recovery_24.00hrs_land_constr.csv",
            "2030_OutputSummary_Phase1_SDOM_MEA_Target_0.00_Resilience_1.00_Outage_48.00hrs_Recovery_0.00hrs_diesel_land_constr.csv",
            "2030_OutputSummary_Phase1_SDOM_MEA_Target_0.00_Resilience_1.00_Outage_48.00hrs_Recovery_48.00hrs_land_constr.csv",
            
            "2030_OutputSummary_Phase1_SDOM_MEA_Target_0.00_Resilience_1.00_Outage_24.00hrs_Recovery_0.00hrs_diesel_noland_constr.csv",
            "2030_OutputSummary_Phase1_SDOM_MEA_Target_0.00_Resilience_1.00_Outage_24.00hrs_Recovery_24.00hrs_noland_constr.csv",
            "2030_OutputSummary_Phase1_SDOM_MEA_Target_0.00_Resilience_1.00_Outage_48.00hrs_Recovery_0.00hrs_diesel_noland_constr.csv",
            "2030_OutputSummary_Phase1_SDOM_MEA_Target_0.00_Resilience_1.00_Outage_48.00hrs_Recovery_48.00hrs_noland_constr.csv"


        ]
        exact_filenames_storage: List[str] = []  # add exact storage filenames here if needed

        # 2) Discover files by exact basename match (no wildcards)
        roots = candidate_roots()
        summary_paths, unmatched_summary = discover_exact_filenames(exact_filenames_summary, roots)
        storage_paths, unmatched_storage = discover_exact_filenames(exact_filenames_storage, roots)

        # Diagnostics
        print("[Discovery] Summary matches (in load order):")
        if summary_paths:
            for p in summary_paths:
                tag = infer_tag_from_filename(str(p)) or "?"
                is_p1 = "Phase1" if is_phase1_file(str(p)) else "Regular"
                print(f"  → [{is_p1} | {tag:4}] {p.name} | {p}")
        else:
            print("  (none)")

        if unmatched_summary:
            print("[Discovery] Summary filenames not found (first plausible hint path):")
            for u in unmatched_summary:
                print("  -", u)

        if unmatched_storage:
            print("[Discovery] Storage filenames not found (first plausible hint path):")
            for u in unmatched_storage:
                print("  -", u)

    # Helpful warnings
    if not any(not is_phase1_file(str(p)) for p in summary_paths):
        print("[WARNING] No regular summary files were found. Plots require at least one regular file.")
    if not any(is_phase1_file(str(p)) for p in summary_paths):
        print("[INFO] No Phase1 overlay files found. Capacity panels will render without dashed outage bars.")

    # 3) Build use cases automatically (first regular match → Scenario 1; second → Scenario 2)
    use_cases = {"Off-grid": ["1",'2','3','4','5','6','7','8','9','10','11','12'], "Grid": ["13",'14','15','16','17','18','19','20']}

    # 4) Optional nicer scenario labels (human-friendly names)
    scenario_labels_map = {
        "1": "3 MW (flat) diesel backup, 24 h outage",
        "2": "3 MW (flat) storage backup, 24 h outage",
        "3": "3 MW (flat) diesel backup, 48 h outage",
        "4": "3 MW (flat) storage backup, 48 h outage",
        "5": "3 MW (flat) diesel backup, 72 h outage",
        "6": "3 MW (flat) storage backup, 72 h outage",
        "7": "Actual load diesel backup, 24 h outage",
        "8": "Actual load storage backup, 24 h outage",
        "9": "Actual load diesel backup, 48 h outage",
        "10": "Actual load storage backup, 48 h outage",
        "11": "Actual load diesel backup, 72 h outage",
        "12": "Actual load storage backup, 72 h outage",
        "13": "Land constrained diesel backup, 24 h outage",
        "14": "Land constrained storage backup, 24 h outage",
        "15": "Land constrained diesel backup, 48 h outage",
        "16": "Land constrained storage backup, 48 h outage",
        "17": "No land constrained diesel backup, 24 h outage",
        "18": "No land constrained storage backup, 24 h outage",
        "19": "No land constrained diesel backup, 48 h outage",
        "20": "No land constrained storage backup, 48 h outage",


    }

    # 5) Overlay technologies (transparent dashed bars)
    outage_techs = ["H2","Li-Ion",'Vanadium"']  # add more like ["H2", "Vanadium"] if needed

    # 6) Create plots
    plots = SDOMPlots(
        csv_summary_paths=summary_paths,
        csv_storage_paths=storage_paths,
        renderer="browser",
        use_cases=use_cases,
        outage_requirement_metric_name="Discharge power capacity",
        outage_requirement_techs=outage_techs,
        outage_source_keyword="Phase1",
        scenario_labels_map=scenario_labels_map,
    )

    plots.create_use_case_capacity_duration_dashboard(
        title="",
        filename="use_case_capacity_duration_dashboard.png",
        outage_legend_label="Storage dedicated to outage",
    )

    plots.create_system_cost_stacked_bar_by_use_case(
        title="",
        filename="cost_components_by_use_case.png",
    )

    # Or: plots.create_all_plots()


if __name__ == "__main__":
    main()
