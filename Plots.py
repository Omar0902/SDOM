# -*- coding: utf-8 -*-
"""
Created on Wed May 28 14:50:00 2025

@author: mkoleva
"""
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
import numpy as np
import matplotlib.colors as mc # For the legend
from matplotlib.colors import LinearSegmentedColormap

# Another utility for the legend
from matplotlib.cm import ScalarMappable

# Open the csv file
data = pd.read_csv("OutputSummary_SDOM_SDOM_pyomo_cbc_122324_Nuclear_1_Target_1.00_.csv")

# Doughnut chart

gen_capacity = pd.DataFrame(data.loc[data["Metric"] == "Capacity", "Optimal Value"][0:3])
gen_capacity_label = pd.DataFrame(data.loc[data["Metric"] == "Capacity", "Technology"][0:3])
sto_capacity = pd.DataFrame(data.loc[data["Metric"] == "Average power capacity", "Optimal Value"][0:4])
sto_capacity_label = pd.DataFrame(data.loc[data["Metric"] == "Average power capacity", "Technology"][0:4])


capacity = pd.concat([gen_capacity, sto_capacity])
capacity_labels = pd.concat([gen_capacity_label, sto_capacity_label])
total_capacity = round(sum(capacity['Optimal Value'])/1000) #GW
capacity_n_labels = pd.concat([capacity_labels, capacity], axis=1)


capacity_filtered = capacity_n_labels[capacity_n_labels['Optimal Value'] > 0]

color_map = {'GasCC': '#5E1688', 'Solar PV': '#FFC903', 'Wind': '#00B6EF', 'Li-Ion': '#FF4A88', 'CAES': '#FF4741', 'PHS': '#CC0079', 'H2': '#FF7FBB'}  
colors = [color_map[label] for label in capacity_filtered['Technology']]  
    

fig, ax = plt.subplots(figsize=(10, 10))
ax.pie(capacity_filtered['Optimal Value'], 
       #labels=capacity_labels['Technology'], 
       startangle=90, colors = colors, autopct='%1.1f%%', pctdistance=0.8,  textprops={'fontsize': 20, 'fontweight':'bold','color':'black'})

# Draw a circle at the center to create the donut effect
centre_circle = plt.Circle((0, 0), 0.60, fc='white')
fig = plt.gcf()
fig.gca().add_artist(centre_circle)

# Ensure the circle is a circle
ax.axis('equal')

# Display the chart
plt.title('Capacity per technology (MW)', y = 0.95, fontsize = 28)
legend = plt.legend(capacity_filtered['Technology'], bbox_to_anchor=(1.15, 0.9), loc="upper right", frameon=False, fontsize = 20, labelcolor='black')

centre_text = f'{total_capacity}GW'
centre_text_line_2 = f'Total Capacity'
ax.text(0,0.1, centre_text, horizontalalignment='center', 
            verticalalignment='center', 
            fontsize=32, fontweight='bold',
            color='black')
ax.text(0,-0.1, centre_text_line_2, horizontalalignment='center', 
            verticalalignment='center', 
            fontsize=30, fontweight='bold',
            color='black')
plt.tight_layout() # Adjust layout to prevent labels from overlapping
plt.show()
plt.savefig('Capacity_per_tech.png', dpi=1000)

# TODO
# 1. How to remove labels of values which are 0 and technologies which are 0? - done
# 2. Resolution - done
# 3. Change color of total to black - done
# 4. Remove frame for legend; keep vertical - done
# 5. Think of dark gray for % and technologies - done (not working well)

# Heat map

results = pd.read_csv("OutputStorage_SDOM_SDOM_pyomo_cbc_122324_Nuclear_1_Target_1.00_.csv")
results_LiIon = pd.DataFrame(results.loc[results["Technology"] == "Li-Ion", "State of charge (MWh)"])

hours = np.arange(1, 8761)

# Create the DataFrame with the hours
df = pd.DataFrame(data=hours, columns=["Hour of the Year"])

# Create a DatetimeIndex for a year (assuming the data starts at the beginning of the year)
start_date = '2023-01-01 00:00:00' # Or any starting date
datetime_index = pd.date_range(start=start_date, periods=8760, freq='H')

# Assign the DatetimeIndex to the DataFrame
df['timestamp'] = datetime_index

# Extract day of year and hour of day
df['day_of_year'] = df['timestamp'].dt.dayofyear
df['hour_of_day'] = df['timestamp'].dt.hour

# Re-arrange SOC values
SOC = results_LiIon['State of charge (MWh)'].values.reshape(24, len(df['day_of_year'].unique()), order="F")
norm_SOC = SOC*100/np.max(SOC) # Percentage %

# # Compute x and y grids, passed to `ax.pcolormesh()`.

# # The first + 1 increases the length
# # The outer + 1 ensures days start at 1, and not at 0.
xgrid = np.arange(df['day_of_year'].max() + 1) + 1

# # Hours start at 0, length 2
ygrid = np.arange(25)

fig, ax = plt.subplots(figsize=(12,10))

CB_color_cycle = [
                 '#00296b','#003f88', '#00509d',  '#1F449C' , '#ffd500', '#fdc500',  '#F05039'                             
                  ]

custom_cmap = LinearSegmentedColormap.from_list("my_cmap", CB_color_cycle)

heatmap = ax.pcolormesh(xgrid, ygrid, norm_SOC, cmap = custom_cmap)
ax.set_xticklabels(ax.get_xmajorticklabels(), fontsize=16) 
ax.set_yticklabels(ax.get_ymajorticklabels(), fontsize=16)
ax.set_frame_on(False) # remove all spines
current_xticks = plt.xticks()[0]
current_xticklabels = [label.get_text() for label in plt.xticks()[1]]

# Add the last x-value if it's not already a tick
if xgrid[-1] not in current_xticks:
    new_xticks = np.append(current_xticks, xgrid[-1])
    new_xticklabels = np.append(current_xticklabels, str(xgrid[-1]))
    plt.xticks(new_xticks, new_xticklabels)

# Get the current tick locations and labels for y-axis
current_yticks = plt.yticks()[0]
current_yticklabels = [label.get_text() for label in plt.yticks()[1]]

# Add the last y-value if it's not already a tick
if ygrid[-1] not in current_yticks:
    new_yticks = np.append(current_yticks, ygrid[-1])
    new_yticklabels = np.append(current_yticklabels, str(ygrid[-1]))
    plt.yticks(new_yticks, new_yticklabels)
plt.xlim(0, 365)  
plt.ylim(0,24)
plt.colorbar(heatmap)
plt.xlabel("Day of the year", fontsize = 20)
plt.ylabel("Hour of the day", fontsize = 20)
plt.title("Annual Hourly Li-Ion Battery Storage State of Charge (%)", y=1.05, fontsize = 20)
plt.savefig('SOC_Li_ion.png', dpi=1000)
