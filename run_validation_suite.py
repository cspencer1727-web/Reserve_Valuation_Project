import numpy as np
import pandas as pd
from pymort import MortXML
from Acsci_proj_final import (get_qx_for_policy, build_extended_lapse_table, randomize_mortality, randomize_lapse, randomize_lapse_dynamic, simulate_rate_path_vasicek,calibrate_book_premiums, simulate_n_paths, simulate_one_reserve, reserve_for_one_path, simulate_one_book_reserve, run_full_book_simulation, benefit_only_pv)

np.random.seed(42)

xml = MortXML.from_id(3282)
mortality_rates = xml.Tables[1].Values['vals'].tolist()
qx_30 = mortality_rates[:30]

base_lapse = [0.1620, 0.1185, 0.0962, 0.0817, 0.0698, 0.0613, 0.0554, 0.0506, 0.0471, 0.0442, 0.0415, 0.0398, 0.0376, 0.0361, 0.0347, 0.0335, 0.0324, 0.0316, 0.0307, 0.0299, 0.0290, 0.0285, 0.0278, 0.0272, 0.0267, 0.0261, 0.0257, 0.0253, 0.0248, 0.0244]

start_rate, long_run_mean, speed, annual_vol = 0.045, 0.045, 0.05, 0.01
shock_std_mort, shock_std_lapse = 0.05, 0.005
policy_face, annual_premium = 100000, 1450
n_years = 30
total_years = 120


sample_book = pd.DataFrame({
    'policy_id': [f'POL{i}' for i in range(10)],
    'issue_age': [25, 30, 35, 40, 45, 50, 55, 60, 65, 70],
    'face_amount': [150000, 200000, 250000, 180000, 220000, 300000, 175000, 240000, 190000, 210000],
    'annual_premium': [2200, 3100, 4000, 2700, 3600, 5200, 2900, 4300, 3400, 4100],
})

print("--- Test 1: Life Table Identity Check (lx - dx = lx+1) ---")

radix = 100000
px = [1 - qx for qx in qx_30]
survival_prob = np.cumprod(px)
lx_start = [radix] + [radix * s for s in survival_prob[:-1]]
dx = [l * qx for l, qx in zip(lx_start, qx_30)]
check_col = [lx - d for lx, d in zip(lx_start, dx)]
identity_holds = all(abs(check_col[i] - lx_start[i+1]) < 0.01 for i in range(len(lx_start)-1))
print(f"lx - dx = lx+1 holds for all rows: {identity_holds}\n")

print("--- Test 2: Monte Carlo Convergence (N = 200 to 10,000) ---")

def run_single_policy_sim(n_sims):
    paths = simulate_n_paths(n_sims, start_rate, long_run_mean, speed, annual_vol, n_years)
    discount_paths = np.array([np.cumprod(1/(1+i)) for i in paths])
    reserves = []
    for path, d in zip(paths, discount_paths):
        current_rate = float(np.mean(path))
        r = simulate_one_reserve(qx_30, base_lapse, shock_std_mort, shock_std_lapse, policy_face, annual_premium, d, current_rate, long_run_mean)
        reserves.append(r)
    return np.array(reserves)

for n in [200, 500, 1000, 5000, 10000]:
    reserves_n = run_single_policy_sim(n)
    VaR = np.percentile(reserves_n, 95)
    print(f"n={n:>6}: mean={reserves_n.mean():>10.2f}  std={reserves_n.std():>9.2f}  95% VaR={VaR:>10.2f}")
print()

print("--- Test 3: Deterministic Benchmark (shock_std = 0) ---")

deterministic_discounts = [1/(1+start_rate)**t for t in range(n_years)]

np.random.seed(1)
det_reserve_1 = simulate_one_reserve(qx_30, base_lapse, 0.0, 0.0, policy_face, annual_premium, deterministic_discounts, start_rate, long_run_mean)
np.random.seed(1)
det_reserve_2 = simulate_one_reserve(qx_30, base_lapse, 0.0, 0.0, policy_face, annual_premium, deterministic_discounts, start_rate, long_run_mean)

print(f"Reserve, run 1: {det_reserve_1:.2f}")
print(f"Reserve, run 2: {det_reserve_2:.2f}")
print(f"Reproducible with zero shocks and matched seed: {abs(det_reserve_1 - det_reserve_2) < 0.01}\n")

print("--- Test 4: Interest Rate Volatility Sensitivity ---")

np.random.seed(2)
low_vol_reserves = np.array([simulate_one_reserve(qx_30, base_lapse, shock_std_mort, shock_std_lapse, policy_face, annual_premium, np.cumprod(1/(1+np.array(p))), float(np.mean(p)), long_run_mean)for p in simulate_n_paths(500, start_rate, long_run_mean, speed, 0.005, n_years)])
np.random.seed(2)
high_vol_reserves = np.array([simulate_one_reserve(qx_30, base_lapse, shock_std_mort, shock_std_lapse, policy_face, annual_premium, np.cumprod(1/(1+np.array(p))), float(np.mean(p)), long_run_mean)for p in simulate_n_paths(500, start_rate, long_run_mean, speed, 0.03, n_years)])

print(f"Low annual_vol (0.005)  std dev: {low_vol_reserves.std():.2f}")
print(f"High annual_vol (0.03)  std dev: {high_vol_reserves.std():.2f}")
print(f"Higher volatility widened the distribution: {high_vol_reserves.std() > low_vol_reserves.std()}\n")

print("--- Test 5: Mortality Shock Sensitivity (benefit-side isolated) ---")

np.random.seed(3)
low_mort_shock = np.array([benefit_only_pv(qx_30, base_lapse, 0.01, policy_face, deterministic_discounts)for _ in range(500)])
np.random.seed(3)
high_mort_shock = np.array([benefit_only_pv(qx_30, base_lapse, 0.15, policy_face, deterministic_discounts)for _ in range(500)
])

print(f"Low shock_std_mort (0.01)  std dev: {low_mort_shock.std():.2f}")
print(f"High shock_std_mort (0.15) std dev: {high_mort_shock.std():.2f}")
print(f"Higher mortality shock widened the distribution: {high_mort_shock.std() > low_mort_shock.std()}")
print("Note: this isolates the benefit-side APV, holding lapse static for more info look at README")


print("--- Test 6: Dynamic Lapse Rate-Responsiveness ---")

np.random.seed(4)
low_rate_lapse = randomize_lapse_dynamic(base_lapse, 0.0, current_rate=0.02, long_run_mean=0.045, sensitivity=2.0, idiosyncratic_std=0.002)
np.random.seed(4)
high_rate_lapse = randomize_lapse_dynamic(base_lapse, 0.0, current_rate=0.08, long_run_mean=0.045, sensitivity=2.0, idiosyncratic_std=0.002)

print(f"Avg lapse rate, low-rate scenario  (2%): {np.mean(low_rate_lapse):.4f}")
print(f"Avg lapse rate, high-rate scenario (8%): {np.mean(high_rate_lapse):.4f}")
print(f"Higher rates produced higher lapse, as expected: {np.mean(high_rate_lapse) > np.mean(low_rate_lapse)}\n")

print("--- Test 7: Book-Level VaR / CVaR Tail Direction Check ---")

extended_lapse = build_extended_lapse_table(base_lapse, total_years, ultimate_rate = 0.02, decay_speed = 0.01)
policy_book = calibrate_book_premiums(sample_book, mortality_rates, extended_lapse, start_rate)
book_reserves = run_full_book_simulation(500, start_rate, long_run_mean, speed, annual_vol, n_years, policy_book, mortality_rates, extended_lapse, shock_std_mort, shock_std_lapse)


VaR_95 = np.percentile(book_reserves, 95)
tail = book_reserves[book_reserves >= VaR_95]
CVaR_95 = tail.mean()

print(f"All book reserves non-negative (floor working): {(book_reserves >= 0).all()}")
print(f"95% VaR:  {VaR_95:,.2f}")
print(f"95% CVaR: {CVaR_95:,.2f}")
print(f"CVaR is more severe than VaR (CVaR >= VaR): {CVaR_95 >= VaR_95}")

print("\nVALIDATION SUITE COMPLETE")