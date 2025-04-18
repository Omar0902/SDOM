import pandas as pd
import os
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from random import randint

def generate_resilience_scenarios(base_dir="."):
    """Generates load scenarios for optimization, ensuring *Hour is retained."""

    # Load base data
    load_data = pd.read_csv(os.path.join(base_dir, "Load_hourly_2050.csv"))
    load_data['date'] = pd.to_datetime(load_data['*Hour'] - 1, origin='2050-01-01', unit='h')

    # Define seasons
    def define_season(date):
        if pd.Timestamp("2050-03-01") <= date < pd.Timestamp("2050-06-01"):
            return "Spring"
        elif pd.Timestamp("2050-06-01") <= date < pd.Timestamp("2050-09-01"):
            return "Summer"
        elif pd.Timestamp("2050-09-01") <= date < pd.Timestamp("2050-12-01"):
            return "Fall"
        else:
            return "Winter"

    load_data['Season'] = load_data['date'].apply(define_season)

    # Merge generation data
    for filename, col_name in [
        ("Nucl_hourly_2019.csv", "Nuclear"),
        ("lahy_hourly_2019.csv", "LargeHydro"),
        ("otre_hourly_2019.csv", "OtherRenewables")
    ]:
        gen_data = pd.read_csv(os.path.join(base_dir, filename))

        load_data = load_data.merge(gen_data, on="*Hour", how="left")

    scenario_dir = os.path.join(base_dir, "resilience_scenarios")
    os.makedirs(scenario_dir, exist_ok=True)

    durations = [6, 12, 24, 72]
    seasons = ["Winter", "Spring", "Summer", "Fall"]
    save_data = {}

    for duration in durations:
        lp = load_data.copy()  # Peak outage scenario
        lr = load_data.copy()  # Random outage scenario

        for season in seasons:
            time_delta = pd.Timedelta(duration / 2, unit="h")
            one_hour = pd.Timedelta(1, unit="h")

            # Peak outage scenario
            peak_hour_id = load_data[load_data.Season == season]["Load"].idxmax()
            peak_hour = load_data.loc[peak_hour_id, "date"]
            lp.loc[(lp.date >= peak_hour - time_delta + one_hour) & 
                   (lp.date <= peak_hour + time_delta), 
                   ["OtherRenewables", "LargeHydro", "Nuclear"]] = 0

            # Random outage scenario
            random_id = randint(
                load_data[load_data.Season == season].index.min(), 
                load_data[load_data.Season == season].index.max()
            )
            random_hour = load_data.loc[random_id, "date"]
            lr.loc[(lr.date >= random_hour - time_delta + one_hour) & 
                   (lr.date <= random_hour + time_delta), 
                   ["OtherRenewables", "LargeHydro", "Nuclear"]] = 0

        save_data[f"seasonpeak_outage_{duration}h"] = lp
        save_data[f"seasonrandom_outage_{duration}h"] = lr

    return save_data
