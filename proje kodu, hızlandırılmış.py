from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, List, Sequence, Tuple
import math
import pandas as pd
from gurobipy import GRB, Model, quicksum

# ---------------------------------------------------------------------------
# CONFIGURATION
# ---------------------------------------------------------------------------

@dataclass
class Config:
    excel_file: str = "distances matrix.xlsx"
    sheet_name: str = "Sheet1"
    num_trucks: int = 110
    truck_capacity: int = 23000  # kg
    fixed_cost: float = 2700.0   # € per truck
    km_cost: float = 0.32        # € per km
    mipfocus: int = 1            # 0=balanced, 1=feasibility, 2=bound, 3=heur
    symmetry: int = 2            # 0..2 (2 strongest)
    presolve: int = 2            # 0..2
    cuts: int = 2                # 0..3

DEMANDS: Dict[str, int] = {
    "Istanbul": 0,
    "Lille": 6351,
    "Macon": 11580,
    "Colmar": 8767,
    "Kapıkule": 0,
    "Beauvais": 14781,
    "Nantes": 1900,
    "Strasbourg": 0,
    "Rouen": 22483,
    "Versailles": 2139,
    "Goussainville": 8095,
    "Saint Michel Sur Orge": 13218,
    "Orleans": 10885,
    "Melun": 3933,
}

TRANSIT_SEQUENCE = ["Istanbul", "Kapıkule", "Strasbourg"]

# ---------------------------------------------------------------------------
# DATA LOADING
# ---------------------------------------------------------------------------

def read_distance_matrix(cfg: Config, transit_seq: Sequence[str]) -> Tuple[pd.DataFrame, List[str]]:
    df = pd.read_excel(cfg.excel_file, sheet_name=cfg.sheet_name, index_col=0)
    df.index = df.index.astype(str).str.strip()
    df.columns = df.columns.astype(str).str.strip()

    if list(df.index) != list(df.columns):
        raise ValueError(
            f"Rows and columns differ:\nRows: {df.index.tolist()}\nCols: {df.columns.tolist()}"
        )

    lower_names = [n.lower() for n in df.index]
    for name in transit_seq:
        if name.lower() not in lower_names:
            raise ValueError(f"Transit location '{name}' missing in distance matrix")

    return df, df.index.tolist()

def build_demands(location_names: Sequence[str], demand_dict: Dict[str, int]) -> List[int]:
    lookup = {name.lower(): 0 for name in location_names}
    for loc, val in demand_dict.items():
        lookup[loc.lower()] = val
    return [lookup[name.lower()] for name in location_names]

def get_indexes(location_names: Sequence[str], names: Sequence[str]) -> List[int]:
    lower = [n.lower() for n in location_names]
    return [lower.index(name.lower()) for name in names]

# ---------------------------------------------------------------------------
# MODEL BUILDING (speed-optimized)
# ---------------------------------------------------------------------------

def build_allowed_arcs(n: int, origin: int, kapikule: int, strasbourg: int) -> List[Tuple[int,int]]:
    """Generate only arcs consistent with mandatory sequence:
       origin -> kapikule -> strasbourg -> (customers in any order) -> origin"""
    allowed = []
    for i in range(n):
        for j in range(n):
            if i == j:
                continue
            # Enforce mandatory sequence by construction of the arc set:
            # 1) From origin: ONLY to kapikule
            if i == origin:
                if j == kapikule:
                    allowed.append((i, j))
                continue
            # 2) Into kapikule: ONLY from origin
            if j == kapikule:
                continue
            # 3) From kapikule: ONLY to strasbourg
            if i == kapikule:
                if j == strasbourg:
                    allowed.append((i, j))
                continue
            # 4) Into strasbourg: ONLY from kapikule
            if j == strasbourg:
                continue
            # 5) No return to kapikule or strasbourg except as mandated above
            #    (already covered by (j == kapikule)/(j == strasbourg) filters)
            # 6) From strasbourg: to customers or straight to origin (both ok)
            # 7) Customers: to other customers or to origin
            allowed.append((i, j))
    return allowed

def build_inc_out_lists(n: int, allowed: List[Tuple[int,int]]):
    out_arcs = {i: [] for i in range(n)}
    in_arcs  = {j: [] for j in range(n)}
    for (i,j) in allowed:
        out_arcs[i].append(j)
        in_arcs[j].append(i)
    return in_arcs, out_arcs

def build_model(
    dist: List[List[float]],
    demands: List[int],
    cfg: Config,
    origin: int,
    kapikule: int,
    strasbourg: int,
    transit_idx: List[int],
    delivery_idx: List[int],
):
    m = Model("TruckRouting_fast")
    n = len(dist)
    T = range(cfg.num_trucks)

    # Only create variables for allowed arcs (huge reduction)
    allowed = build_allowed_arcs(n, origin, kapikule, strasbourg)
    in_arcs, out_arcs = build_inc_out_lists(n, allowed)

    # y[t,i,j] for (i,j) in allowed
    y = m.addVars(cfg.num_trucks, allowed, vtype=GRB.BINARY, name="arc")
    # z[t] = truck used
    z = m.addVars(cfg.num_trucks, vtype=GRB.BINARY, name="use_truck")

    # Objective: fixed + distance cost
    m.setObjective(
        quicksum(cfg.fixed_cost * z[t] for t in T)
        + cfg.km_cost * quicksum(dist[i][j] * y[t, i, j] for t in T for (i,j) in allowed),
        GRB.MINIMIZE,
    )

    # Degree / flow balance
    for t in T:
        # Start at origin exactly once if used; due to allowed arcs it's origin->kapikule
        m.addConstr(quicksum(y[t, origin, j] for j in out_arcs[origin]) == z[t], name=f"start_{t}")
        # End at origin exactly once if used
        m.addConstr(quicksum(y[t, i, origin] for i in in_arcs[origin]) == z[t], name=f"end_{t}")

        # Kapikule and Strasbourg arc counts implicitly enforced by arc set + balance
        # But to tighten:
        m.addConstr(quicksum(y[t, i, kapikule] for i in in_arcs[kapikule]) == z[t], name=f"in_kap_{t}")
        m.addConstr(quicksum(y[t, kapikule, j] for j in out_arcs[kapikule]) == z[t], name=f"out_kap_{t}")
        m.addConstr(quicksum(y[t, i, strasbourg] for i in in_arcs[strasbourg]) == z[t], name=f"in_str_{t}")
        # Out of Strasbourg equals in due to balance below.

        # Flow balance for all nodes except origin (origin handled by start/end)
        for v in range(n):
            if v == origin:
                continue
            m.addConstr(
                quicksum(y[t, v, j] for j in out_arcs[v]) ==
                quicksum(y[t, i, v] for i in in_arcs[v]),
                name=f"balance_t{t}_v{v}"
            )

        # Link: if truck not used, forbid any arc activity (kills isolated cycles)
        bigM = 2*n  # safe upper bound on number of arcs a used truck can have
        m.addConstr(quicksum(y[t, i, j] for (i,j) in allowed) <= bigM * z[t], name=f"link_z_y_{t}")

    # Each delivery node visited exactly once (across all trucks)
    for j in delivery_idx:
        m.addConstr(
            quicksum(y[t, i, j] for t in T for i in in_arcs[j]) == 1,
            name=f"visit_once_{j}"
        )

    # Capacity per truck (sum of demands of customers that t enters)
    for t in T:
        m.addConstr(
            quicksum(demands[j] * quicksum(y[t, i, j] for i in in_arcs[j]) for j in delivery_idx)
            <= cfg.truck_capacity,
            name=f"cap_{t}"
        )

    # MTZ subtour elimination ONLY on customer nodes (faster & sufficient)
    C = delivery_idx
    if len(C) >= 2:
        u = m.addVars(cfg.num_trucks, C, lb=1, ub=len(C), vtype=GRB.CONTINUOUS, name="u")
        for t in T:
            for i in C:
                for j in C:
                    if i == j:
                        continue
                    if (i, j) in set(build_allowed_arcs(n, origin, kapikule, strasbourg)):
                        # u_i - u_j + |C| * y_ij <= |C| - 1
                        m.addConstr(u[t, i] - u[t, j] + len(C) * y[t, i, j] <= len(C) - 1,
                                    name=f"mtz_t{t}_{i}_{j}")

    # Symmetry breaking on trucks: z[0] >= z[1] >= ...
    for t in range(cfg.num_trucks - 1):
        m.addConstr(z[t] >= z[t + 1], name=f"symm_{t}")

    # Gurobi parameters (speed)
    m.Params.MIPFocus = cfg.mipfocus
    m.Params.Symmetry = cfg.symmetry
    m.Params.Presolve = cfg.presolve
    m.Params.Cuts = cfg.cuts
    # m.Params.TimeLimit = 600  # uncomment if you want a hard cap

    return m, y, z, allowed, in_arcs, out_arcs

# ---------------------------------------------------------------------------
# SOLUTION EXTRACTION
# ---------------------------------------------------------------------------

def extract_routes(model, y, z, location_names, demands, dist, origin, allowed, out_arcs):
    n = len(location_names)
    routes = []
    allowed_set = set(allowed)
    for t in z.keys():
        if z[t].X <= 0.5:
            continue
        route_idx = [origin]
        cur = origin
        load = 0
        distance = 0.0
        visited_guard = 0
        # Traverse unique successor each step
        while True:
            nxt_candidates = [j for j in out_arcs[cur] if (origin, j) in allowed_set or True]
            nxt_candidates = [j for j in nxt_candidates if (t, cur, j) in y and y[t, cur, j].X > 0.5]
            if not nxt_candidates:
                break
            nxt = nxt_candidates[0]
            route_idx.append(nxt)
            distance += dist[cur][nxt]
            if nxt != origin:
                load += demands[nxt]
            if nxt == origin:
                break
            cur = nxt
            visited_guard += 1
            if visited_guard > 2 * n + 5:
                # Safety break against unexpected loops
                break
        routes.append({
            "truck": t,
            "route": [location_names[i] for i in route_idx],
            "load": load,
            "distance": distance,
        })
    return routes

# ---------------------------------------------------------------------------
# REPORTING
# ---------------------------------------------------------------------------

def print_report(routes: Sequence[Dict[str, object]], cfg: Config) -> None:
    if not routes:
        print("No trucks were used.")
        return
    total_fixed = len(routes) * cfg.fixed_cost
    total_distance = sum(r["distance"] for r in routes)
    total_km_cost = total_distance * cfg.km_cost
    total_cost = total_fixed + total_km_cost
    for idx, r in enumerate(routes, start=1):
        print(f"\nTruck {idx}:")
        print("  Route: " + " -> ".join(r["route"]))
        print(f"  Load: {r['load']} kg")
        print(f"  Distance: {r['distance']:.2f} km")
    print("\nSummary:")
    print(f"  Trucks used: {len(routes)}")
    print(f"  Total distance cost: {total_km_cost:.2f} €")
    print(f"  Total fixed cost: {total_fixed:.2f} €")
    print(f"  Total cost: {total_cost:.2f} €")

# ---------------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------------

def main() -> None:
    cfg = Config()
    try:
        df, location_names = read_distance_matrix(cfg, TRANSIT_SEQUENCE)
    except Exception as exc:
        print(f"Error reading distance matrix: {exc}")
        return

    demands = build_demands(location_names, DEMANDS)
    transit_idx = get_indexes(location_names, TRANSIT_SEQUENCE)
    origin, kapikule, strasbourg = transit_idx
    delivery_idx = [i for i in range(len(location_names)) if i not in transit_idx]

    # Quick sanity: any single customer demand > capacity?
    bads = [location_names[i] for i in delivery_idx if demands[i] > cfg.truck_capacity]
    if bads:
        print("Infeasible: individual demand exceeds truck capacity:", bads)
        return

    total_demand = sum(demands[i] for i in delivery_idx)
    min_trucks_needed = math.ceil(total_demand / cfg.truck_capacity)
    if min_trucks_needed > cfg.num_trucks:
        print(f"Warning: total demand ({total_demand}) exceeds total available capacity "
              f"({cfg.num_trucks * cfg.truck_capacity}).")

    model, y, z, allowed, in_arcs, out_arcs = build_model(
        df.values.tolist(),
        demands,
        cfg,
        origin,
        kapikule,
        strasbourg,
        transit_idx,
        delivery_idx,
    )

    model.optimize()

    if model.status == GRB.OPTIMAL:
        routes = extract_routes(model, y, z, location_names, demands, df.values.tolist(),
                                origin, allowed, out_arcs)
        print_report(routes, cfg)
        model.write("TruckRouting.lp")
        model.write("TruckRouting.sol")
    else:
        print("Model couldn't find an optimal solution.")
        if model.status == GRB.INFEASIBLE:
            print("Model is infeasible. Possible reasons: capacity limits, transit order or demand totals.")
            try:
                model.computeIIS()
                model.write("TruckRouting.ilp")
            except Exception as exc:
                print(f"Failed to compute IIS: {exc}")

if __name__ == "__main__":
    main()