# Istanbul–France Truck Assignment & Route Optimization (VRP, Gurobi)

**Author:** Yusuf Demirci (Industrial Engineering, Sabancı University)  
**Company:** VIP Lojistik (Hadımköy, Istanbul)  
**Period:** Summer Internship 2025

> This repository demonstrates the cost and fleet impact of **split deliveries (“mixed filo”)** versus **no split** for the Istanbul → Kapıkule → Strasbourg → France corridor. It contains **three program variants** and **three outputs** that you can compare side by side.

---

## ✦ Overview

We solve a **fixed-charge, capacitated multi-vehicle VRP** in **Gurobi** to plan truck activation and routing from Istanbul/Hadımköy through Kapıkule, entering France at Strasbourg, and visiting French customer locations.

**Cost & capacity (operational):**
- **Fixed cost per active truck (round trip):** ~€2,700
- **Fuel cost per km:** ~€0.32/km
- **Capacity:** ~23,000 kg per truck
- **Fleet:** up to ~110 active (of 120 total)

**Core question:** *Can we reduce total cost and truck count by allowing a city’s order to be split across multiple trucks?*

---

## 🗂 Repository Structure (expected)

```
├─ distances matrix.xlsx
├─ project code without mixed filo.py
├─ project code with mixed filo.py
├─ project code with mixed filo extra demand.py
├─ output without mixed filo.PNG
├─ output with mixed filo.png
├─ output with mixed filo extra demand.png
└─ README.md  (this file)
```

> Tip: For linking images in markdown, consider renaming files to avoid spaces or escape them properly.

---

## 🧠 Model Variants (What’s different?)

### 1) `project code without mixed filo.py` — **Baseline (No Split)**
- **Constraint:** each delivery city is visited by **exactly one** truck  
  \(\sum_t x_{t,j}=1, \; x_{t,j}\in\{0,1\}\)
- **Effect:** activates **more trucks** to respect capacity → **fixed charges dominate** total cost.

### 2) `project code with mixed filo.py` — **Mixed Filo (Split Enabled)**
- **Change:** allow **order sharing** across trucks via load variables \(w_{t,j}\ge 0\)  
  Demand balance \(\sum_t w_{t,j}=d_j\), Capacity \(\sum_j w_{t,j}\le Q\)
- **Effect:** **higher load factors → fewer active trucks → lower cost**, even if some route legs shift.

### 3) `project code with mixed filo extra demand.py` — **Mixed Filo, Stress Test**
- **Why:** With the **real company demands**, many cities fit in one truck, so splitting benefit wasn’t obvious.
- **Change:** **Demand increased** intentionally to **force sharing** and make the saving **clearly visible**.

---

## 🖼 Outputs (Qualitative comparison)

| Variant | Split Deliveries | Trucks Activated | Total Cost (indicative) | What the screenshot shows |
|---|---|---:|---:|---|
| **Without mixed filo** | ❌ No | Higher | ~**24.5k** (observed in your run) | More trucks; fixed charge drives cost |
| **With mixed filo** | ✅ Yes | Fewer | **Lower than baseline** | Sharing across trucks, better utilization |
| **With mixed filo – extra demand** | ✅ Yes | Minimized under heavy load | **Lowest under stress** | Strongest benefit of splitting is visible |

> See PNGs in the repo: `output without mixed filo.PNG`, `output with mixed filo.png`, `output with mixed filo extra demand.png`.

---

## ⚙️ Problem Formulation (compact)

- **Variables:**  
  \(z_t\) (truck activation), \(y_{t,ij}\) (arc usage), optional visit indicators (\(x_{t,j}\) / \(v_{t,j}\)), and **split** variants include loads \(w_{t,j}\) (kg of city *j* on truck *t*).

- **Objective:**  
  \[
  \min \sum_t F\,z_t \; + \; \alpha\Big(\sum_{t,i,j} c_{ij} y_{t,ij} \; + \; B\sum_t z_t\Big)
  \]
  where **F** = fixed cost per truck, **\(\alpha\)** = €/km, **B** = corridor base-leg km per active truck.

- **Key constraints:** coverage (no-split: “exactly once”; split: **demand balance**), capacity, flow conservation, corridor start/end (Strasbourg/Kapıkule), linking, and **MTZ** subtour elimination.

---

## 🚀 Quickstart

1. Install Python + Gurobi (licensed):
   ```bash
   pip install gurobipy pandas
   ```
2. Place `distances matrix.xlsx` next to the code files (sheet/labels consistent).
3. Run any variant:
   ```bash
   python "project code without mixed filo.py"
   python "project code with mixed filo.py"
   python "project code with mixed filo extra demand.py"
   ```
4. Compare console outputs and the three PNG screenshots.

---

## 📌 Why Mixed Filo Reduces Cost (intuition)

- **Fixed-charge leverage:** each avoided truck saves ≈ **€2,700**.  
- **Load factor ↑:** sharing packs trucks closer to **23 t**, cutting truck count.  
- **Corner cases:** near-capacity single-city demands no longer force an entire extra truck.  
- **Scales under stress:** as total demand rises or skews, **split** prevents explosive truck activations.

---

## 🧪 “Extra Demand” Variant — What it proves

- Real monthly demands may **not require** splitting → benefit seems small.  
- By **raising demands**, you **force** sharing and **show** clear savings vs. baseline.

---

## 🧪 Reproducibility Notes

- Ensure the **distance matrix is square** with identical row/column labels.  
- Transit nodes (Istanbul, Kapıkule, Strasbourg) must have **zero demand**.  
- Parameters (fixed cost, €/km, capacity, trucks) are configured **in code**.

---

## ⚠️ Known Limitations

- No explicit **time windows** or **driver-hour** constraints in base variants.  
- Tolls not modeled **per arc** (averaged into fixed cost).  
- Homogeneous trucks; single-period planning; no multi-compartment constraints.

---

## 🛠 Roadmap

- Add **time windows** & **driver-hour** constraints.  
- Introduce **heterogeneous fleet**, arc-level tolls/emissions.  
- Consider **backhauls**, multi-depot, and dashboards.  
- Weekly **data pipeline** for demands + fuel index to auto-refresh parameters.

---

## 🙏 Acknowledgments

Thanks to **VIP Lojistik Fleet Operations** for real demands, capacity assumptions, and cost inputs used to calibrate the corridor model.

---

### License

For academic internship use. Coordinate with the company before public/commercial reuse of data and parameter values.
