import pandas as pd
from gurobipy import Model, GRB, quicksum

# -----------------------
# Data
# -----------------------
excel_file = "distances matrix.xlsx"
df = pd.read_excel(excel_file, sheet_name="Sheet1", index_col=0)

# keep location names as strings
df.index = df.index.astype(str).str.strip()
df.columns = df.columns.astype(str).str.strip()
assert list(df.index) == list(df.columns)

locs = df.index.tolist()
lower = [n.lower() for n in locs]
n = len(locs)

# indices for origin / end / starting point
origin = lower.index("istanbul")
end    = lower.index("kapıkule")
start  = lower.index("strasbourg")
transit = [origin, end, start]
deliveries = [i for i in range(n) if i not in transit]

# demand per location (kg)
demand = {
    lower.index("istanbul"): 0,
    lower.index("lille"): 16351,
    lower.index("macon"): 21580,
    lower.index("colmar"): 18767,
    lower.index("kapıkule"): 0,
    lower.index("beauvais"): 24781,
    lower.index("nantes"): 11900,
    lower.index("strasbourg"): 0,
    lower.index("rouen"): 32483,
    lower.index("versailles"): 12139,
    lower.index("goussainville"): 18095,
    lower.index("saint michel sur orge"): 13218,
    lower.index("orleans"): 10885,
    lower.index("melun"): 3933,
}

# -----------------------
# Parameters
# -----------------------
num_trucks  = 110
capacity    = 23000    # kg (gümrük kanunlarına göre çeker+dorse max 40ton alabilir, 23ton ortalama araca eklenebilen mal)
fixed_cost  = 2700     # € / truck (ortalama şoför, hakediş, otoyol masrafları vs.)
km_cost     = 0.32     # € / km (tır başına ortalama benzin masrafı km başına, şirketlere özel indirimle birlikte, 3200km için 1000LT benzin ortalama 1€/lt'den)
dist        = df.values.tolist()

base_leg_km = dist[origin][end] + dist[end][start] + dist[end][origin]

# -----------------------
# Model
# -----------------------
m = Model("MixedOrderVRP")

arcs = [(i, j) for i in [start] + deliveries
        for j in deliveries + [end] if i != j]

y = m.addVars(num_trucks, arcs, vtype=GRB.BINARY, name="y")           # route
x = m.addVars(num_trucks, deliveries, vtype=GRB.BINARY, name="x")     # visit
q = m.addVars(num_trucks, deliveries, lb=0.0, name="q")               # delivered load
z = m.addVars(num_trucks, vtype=GRB.BINARY, name="z")                 # truck used
u = m.addVars(num_trucks, deliveries, lb=0.0,
              ub=len(deliveries), name="u")                           # MTZ

# Objective: fixed cost + travel cost
m.setObjective(
    quicksum(fixed_cost * z[t] for t in range(num_trucks))
    + km_cost * (
        quicksum(dist[i][j] * y[t, i, j] for t in range(num_trucks) for i, j in arcs)
        + base_leg_km * quicksum(z[t] for t in range(num_trucks))
    ),
    GRB.MINIMIZE
)

# --- Demand is fully delivered (can be split)
for j in deliveries:
    m.addConstr(quicksum(q[t, j] for t in range(num_trucks)) == demand[j],
                name=f"demand_{j}")

# --- Capacity & linking
for t in range(num_trucks):
    # truck capacity
    m.addConstr(quicksum(q[t, j] for j in deliveries) <= capacity * z[t],
                name=f"cap_{t}")

    # q positive => visit
    for j in deliveries:
        m.addConstr(q[t, j] <= demand[j] * x[t, j], name=f"link_{t}_{j}")

    # start/end must be used if truck is active
    m.addConstr(quicksum(y[t, start, j] for j in deliveries + [end]) == z[t],
                name=f"start_{t}")
    m.addConstr(quicksum(y[t, i, end]   for i in [start] + deliveries) == z[t],
                name=f"end_{t}")

    # flow conservation for visited nodes
    for j in deliveries:
        m.addConstr(quicksum(y[t, i, j] for i in [start] + deliveries if i != j)
                    == x[t, j], name=f"in_{t}_{j}")
        m.addConstr(quicksum(y[t, j, k] for k in deliveries + [end] if k != j)
                    == x[t, j], name=f"out_{t}_{j}")

    # if truck unused, no arcs
    for i, j in arcs:
        m.addConstr(y[t, i, j] <= z[t], name=f"use_{t}_{i}_{j}")

    # MTZ subtour elimination
    for j in deliveries:
        m.addConstr(u[t, j] >= x[t, j],                      name=f"mtz_lb_{t}_{j}")
        m.addConstr(u[t, j] <= len(deliveries) * x[t, j],    name=f"mtz_ub_{t}_{j}")
    for i in deliveries:
        for j in deliveries:
            if i != j:
                m.addConstr(u[t, i] - u[t, j]
                            + len(deliveries) * y[t, i, j] <= len(deliveries) - 1,
                            name=f"mtz_{t}_{i}_{j}")
m.Params.MIPFocus = 1
m.Params.TimeLimit = 120
m.Params.MIPGap = 0.01
m.optimize()

# -----------------------
# Reporting
# -----------------------
if m.status in (GRB.OPTIMAL, GRB.TIME_LIMIT):
    active = [t for t in range(num_trucks) if z[t].X > 0.5]
    print(f"\n{len(active)} trucks used.")
    print(f"Total cost: {m.objVal:.2f} €")

    for idx, t in enumerate(active, 1):
        route = [start]
        curr = start
        while curr != end:
            nxt = [j for (i, j) in arcs if i == curr and y[t, i, j].X > 0.5]
            if not nxt:
                break
            curr = nxt[0]
            route.append(curr)

        inside_km = sum(dist[route[i]][route[i+1]] for i in range(len(route)-1))
        tot_km = inside_km + base_leg_km

        print(f"\nTruck {idx}")
        print("Route:", " -> ".join(locs[i] for i in [origin, end, start] + route[1:] + [origin]))
        print(f"Delivered kg: {sum(q[t, j].X for j in deliveries):.0f}")
        print(f"Travel km: {tot_km:.2f}")
else:
    print("No feasible/optimal solution found.")
