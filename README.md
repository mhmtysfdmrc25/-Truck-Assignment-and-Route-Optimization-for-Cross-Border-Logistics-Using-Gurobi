## Overview
This project is a decision-support tool for **assigning trucks and optimizing road routes** from **Istanbul/Hadımköy** to multiple delivery locations in **France**. The model reflects the company’s real operating corridor—**Istanbul → Kapıkule (TR–BG) → Strasbourg (FR entry)** via **Bulgaria → Slovenia → Austria → Germany → France**—and computes a **minimum-cost plan** that covers all demands while respecting fleet size and truck capacity.

The optimization is formulated as a **fixed-charge, capacitated multi-vehicle VRP** and solved with **Gurobi**. Costs include a fixed cost per active truck and a per-kilometer fuel cost; distances are taken from a square Excel **distance matrix** assembled from Google Maps.

---

## Business Problem
- Given monthly orders (weights in kg) for French destinations, **how many trucks** should be used and **which deliveries** should each truck serve?
- Objective: **Minimize total cost** = fixed truck cost + fuel cost × total kilometers (corridor + inside-France legs).

---

## Data & Inputs
- **Distance matrix**: `distances matrix.xlsx` (`Sheet1`), square with identical row/column location names.
- **Nodes**:
  - **Origin**: Istanbul (Hadımköy)
  - **Transit**: Kapıkule (border), Strasbourg (FR entry)
  - **Delivery nodes (France)**: Lille, Macon, Colmar, Beauvais, Nantes, Rouen, Versailles, Goussainville, Saint‑Michel‑sur‑Orge, Orléans, Melun
- **Demands (kg)**: Embedded in code as a dictionary for the French nodes (transit nodes have zero demand).
- **Fleet & capacity**:
  - Total fleet: 120, **active planning size: 110**
  - Legal gross (tractor+trailer): **40 t** (TR customs)
  - **Model capacity per truck (avg): 23,000 kg** (operational practice)
- **Costs**:
  - **Fixed cost per truck (round trip)**: **€2,700**  
    (driver wage ~ €920 + driver expenses ~ €630 + averaged one‑way tolls: BG €55, SI €20, AT €220, DE €220)
  - **Fuel cost per km**: **€0.32/km** (≈ 1,000 L / 3,200 km × €1/L with refunds/discounts)
- **Corridor logic**:
  - Each active truck’s kilometers include: **Istanbul→Kapıkule + Kapıkule→Strasbourg + (Strasbourg→deliveries→Kapıkule) + Kapıkule→Istanbul**.

---

## Method (At a Glance)
- **Model**: Capacitated Multi‑Vehicle VRP with **fixed‑charge** activation per truck.
- **Variables**:
  - `z_t` = 1 if truck *t* is used
  - `x_{t,j}` = 1 if truck *t* serves delivery node *j*
  - `y_{t,ij}` = 1 if truck *t* travels arc *(i→j)* inside the France VRP
  - `u_{t,j}` MTZ order variables (subtour elimination)
- **Objective**:  
  \( \min \sum_t F z_t + \alpha[ \sum_t \sum_{(i,j)} c_{ij} y_{t,ij} + B \sum_t z_t ] \)  
  where \(F=2700\) (EUR/truck), \(\alpha=0.32\) (EUR/km), \(B\) is the per‑truck base‑legs distance.
- **Key constraints**:
  - Each delivery node is visited **exactly once**.
  - **Capacity** per truck: total assigned kg ≤ **23,000**.
  - **Flow conservation** and **start/end** structure with Strasbourg (start) and Kapıkule (end) for the France leg.
  - **MTZ** subtour elimination.

---

## What the Script Produces
- **Total cost**, split into fixed and distance components.
- **Number of trucks used**.
- **Per‑truck route** in the corridor format:  
  `Istanbul → Kapıkule → Strasbourg → [deliveries…] → Kapıkule → Istanbul`
- **Kilometer breakdown** (inside‑France vs. base legs) and **per‑truck cost**.

---

## How to Run
1. Install Python and **Gurobi** with a valid license.
2. `pip install pandas gurobipy`
3. Place the Excel file `distances matrix.xlsx` next to the script.
4. Run:  
   ```bash
   python "proje kodu.py"
   ```
   (Rename your script if needed, e.g., `vrp_main.py`.)

**Notes**
- The solver is configured with practical limits (e.g., time/gap). Results are typically near‑optimal and operationally usable.
- Ensure distance matrix row/column names **exactly match**; the script validates this and stops if mismatched.

---

## Assumptions & Limitations
- Toll variability and time‑dependent traffic are not modeled per arc; tolls are averaged into the **fixed cost**.
- **Fuel price** assumed constant in a run (parameterized at €0.32/km).
- No **time windows**, **driver-hour** constraints, or **heterogeneous fleet** in the base model.
- Single‑period planning; every French node is served once (no split deliveries).

---

## Roadmap (Future Work)
- Add **time windows** and **driver-hour** constraints (EU regs).
- Model **heterogeneous fleet** and **arc-level tolls** and emissions.
- Add **backhauls** and multi‑depot variations.
- Build a simple **data pipeline** (CSV templates) + reporting dashboards.

---

## Acknowledgments
Built during the 2025 summer internship at **VIP Lojistik** with input from the **Fleet Operations** team on real demands, capacity assumptions, and cost parameters.
