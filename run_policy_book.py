import pandas as pd
import numpy as np
from pymort import MortXML
from Acsci_proj_final import (load_policy_book, randomize_lapse_dynamic, calibrate_book_premiums, run_full_book_simulation_lifetime, build_extended_lapse_table, export_results_to_excel)

np.random.seed(42)

start_rate = 0.045
long_run_mean = 0.045
speed = 0.3
annual_vol = 0.01
shock_std_mort  = 0.05
shock_std_lapse = 0.005
n_sims = 200 #Set for the purpose of demonstration not accruacy

base_lapse = [0.1620, 0.1185, 0.0962, 0.0817, 0.0698, 0.0613, 0.0554, 0.0506, 0.0471, 0.0442, 0.0415, 0.0398, 0.0376, 0.0361, 0.0347, 0.0335, 0.0324, 0.0316, 0.0307, 0.0299, 0.0290, 0.0285, 0.0278, 0.0272, 0.0267, 0.0261, 0.0257, 0.0253, 0.0248, 0.0244]

xml = MortXML.from_id(3282)
mortality_rates = xml.Tables[1].Values['vals'].tolist()

extended_lapse = build_extended_lapse_table(base_lapse, total_years = 120, ultimate_rate = 0.02,  decay_speed = 0.01)

policy_book = load_policy_book("data/sample_policy_book.xlsx")
print(f"Loaded {len(policy_book)} policies.")

policy_book = calibrate_book_premiums(policy_book, mortality_rates, extended_lapse, start_rate)
print("Premiums calibrated via equivalence principle")

result = run_full_book_simulation_lifetime(n_sims, start_rate, long_run_mean, speed, annual_vol, policy_book, mortality_rates, extended_lapse, shock_std_mort, shock_std_lapse)

print(f"Mean book reserve: {result.mean():,.2f}")
print(f"95% VaR: {np.percentile(result, 95):,.2f}")

assumptions = {
        "start_rate": start_rate,
    "long_run_mean": long_run_mean,
    "speed": speed,
    "annual_vol": annual_vol,
    "n_sims": n_sims,
    "shock_std_mort": shock_std_mort,
    "shock_std_lapse": shock_std_lapse,
    "mortality_source": "SOA 2017 CSO (Table ID 3282)",
    "lapse_source": "Base + decay-to-ultimate extension (2%)",
}

output_path = export_results_to_excel("output/final_lifetime_results.xlsx", policy_book, result, assumptions)
print(f"Results exported to {output_path}")
