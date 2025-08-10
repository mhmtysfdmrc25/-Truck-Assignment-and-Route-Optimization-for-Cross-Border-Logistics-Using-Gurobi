import pandas as pd
from gurobipy import Model, GRB, quicksum

# 1) Mesafe Matrisi Oku
excel_file = "distances matrix.xlsx"
sheet_name = "Sheet1"
df = pd.read_excel(excel_file, sheet_name=sheet_name, index_col=0)

df.index = df.index.astype(str).str.strip()
df.columns = df.columns.astype(str).str.strip()
if list(df.index) != list(df.columns):
    raise ValueError(f"Rows and columns differ:\n{df.index.tolist()}\n{df.columns.tolist()}")

location_names = df.index.tolist()
num_locations  = len(location_names)

# 2) Özel Lokasyonların İndekslerini Bul
lower = [n.lower() for n in location_names]
origin_index = lower.index("istanbul")
end_index = lower.index("kapıkule")
start_index = lower.index("strasbourg")  # VRP başlangıç noktası
transit_indexes = [origin_index, end_index, start_index]
delivery_indexes = [i for i in range(num_locations) if i not in transit_indexes]

# 3) Demands'i Direkt Kod İçine Yaz
# Sıralama: location_names listesindeki sıraya göre!
demands = {
    lower.index("istanbul"): 0,
    lower.index("lille"): 6351,
    lower.index("macon"): 11580,
    lower.index("colmar"): 8767,
    lower.index("kapıkule"): 0,
    lower.index("beauvais"): 14781,
    lower.index("nantes"): 1900,
    lower.index("strasbourg"): 0,
    lower.index("rouen"): 22483,
    lower.index("versailles"): 2139,
    lower.index("goussainville"): 8095,
    lower.index("saint michel sur orge"): 13218,
    lower.index("orleans"): 10885,
    lower.index("melun"): 3933,
}

# 4) Parametreler
num_trucks     = 110
truck_capacity = 23000    # kg (gümrük kanunlarına göre çeker+dorse max 40ton alabilir, 23ton ortalama araca eklenebilen mal)
fixed_cost     = 2700     # € / truck (ortalama şoför, hakediş, otoyol masrafları vs.)
km_cost        = 0.32     # € / km (tır başına ortalama benzin masrafı km başına, şirketlere özel indirimle birlikte, 3200km için 1000LT benzin ortalama 1€/lt'den)
distance       = df.values.tolist()

# 5) Model Kurulumu
base_leg_km = (
    distance[origin_index][end_index]
    + distance[end_index][start_index]
    + distance[end_index][origin_index]
)

# 5) Model
model = Model("TruckRoutingVRP")

# Ark kümesi (Strasbourg'dan başlar, Kapıkule'de biter)
arcs = [
    (i, j)
    for i in [start_index] + delivery_indexes
    for j in delivery_indexes + [end_index]
    if i != j
]

# y[t,i,j]: t tırı i -> j arkını kullanır
y = model.addVars(num_trucks, arcs, vtype=GRB.BINARY, name="y")

# z[t]: t tırı kullanıldı mı?
z = model.addVars(num_trucks, vtype=GRB.BINARY, name="z")

# x[t,j]: t tırı teslimat j'yi ziyaret etti mi?
x = model.addVars(num_trucks, delivery_indexes, vtype=GRB.BINARY, name="x")

# u[t,j]: MTZ sıra değişkeni
u = model.addVars(
    num_trucks,
    delivery_indexes,
    lb=0,
    ub=len(delivery_indexes),
    vtype=GRB.CONTINUOUS,
    name="u",
)

# Amaç: sabit + km maliyeti
model.setObjective(
    quicksum(fixed_cost * z[t] for t in range(num_trucks))
    + km_cost
    * (
        quicksum(
            distance[i][j] * y[t, i, j]
            for t in range(num_trucks)
            for i, j in arcs
        )
        + base_leg_km * quicksum(z[t] for t in range(num_trucks))
    ),
    GRB.MINIMIZE,
)
# 6) Kısıtlar
# a) Her teslimat şehri tam 1 kez ziyaret edilir
for j in delivery_indexes:
    model.addConstr(quicksum(x[t, j] for t in range(num_trucks)) == 1, name=f"cover_{j}")
    
# b) Tüm transit noktalar (istanbul, kapıkule, strasbourg) her kullanılan tır için güzergahda olmalı
for t in range(num_trucks):
    model.addConstr(
        quicksum(y[t, start_index, j] for j in delivery_indexes + [end_index]) == z[t],
        name=f"start_{t}",
    )
    model.addConstr(
        quicksum(y[t, i, end_index] for i in [start_index] + delivery_indexes) == z[t],
        name=f"end_{t}",
    )

    for j in delivery_indexes:
        model.addConstr(
            quicksum(y[t, i, j] for i in [start_index] + delivery_indexes if i != j) == x[t, j],
            name=f"in_{t}_{j}",
        )
        model.addConstr(
            quicksum(y[t, j, k] for k in delivery_indexes + [end_index] if k != j) == x[t, j],
            name=f"out_{t}_{j}",
        )
        model.addConstr(x[t, j] <= z[t], name=f"use_if_visit_{t}_{j}")

    for i, j in arcs:
        model.addConstr(y[t, i, j] <= z[t], name=f"arc_use_{t}_{i}_{j}")

    # Kapasite
    model.addConstr(
        quicksum(demands[j] * x[t, j] for j in delivery_indexes) <= truck_capacity,
        name=f"cap_{t}",
    )

    # MTZ alt-tur kırıcı
    for j in delivery_indexes:
        model.addConstr(u[t, j] >= x[t, j], name=f"mtz_lb_{t}_{j}")
        model.addConstr(
            u[t, j] <= len(delivery_indexes) * x[t, j],
            name=f"mtz_ub_{t}_{j}",
        )
    for i in delivery_indexes:
        for j in delivery_indexes:
            if i != j:
                model.addConstr(
                    u[t, i] - u[t, j] + len(delivery_indexes) * y[t, i, j]
                    <= len(delivery_indexes) - 1,
                    name=f"mtz_{t}_{i}_{j}",
                )
model.Params.MIPFocus = 1
#model.Params.TimeLimit = 3660
model.Params.MIPGap = 0.01

# 7) Modeli Çöz
model.optimize()

# 8) Sonuçları Yazdır
if model.status == GRB.OPTIMAL or model.status == GRB.TIME_LIMIT:
    used = [t for t in range(num_trucks) if z[t].X > 0.5]
    total_fixed = fixed_cost * len(used)
    total_km_cost = model.objVal - total_fixed
    
    print(f"\n{len(used)} trucks have been used for this order set.")
    print(f"Total fixed cost: {total_fixed:.2f} €\n")
    model.write("TruckRoutingVRP.lp")
    model.write("TruckRoutingVRP.sol")
    for idx, t in enumerate(used, start=1):
        route = [start_index]
        current = start_index
        while current != end_index:
            next_nodes = [j for (i, j) in arcs if i == current and y[t, i, j].X > 0.5]
            if not next_nodes:
                break
            current = next_nodes[0]
            route.append(current)

        inside_km = sum(distance[route[i]][route[i + 1]] for i in range(len(route) - 1))
        base_km = base_leg_km
        total_km = inside_km + base_km
        km_cost_val = km_cost * total_km

        full_route = [origin_index, end_index, start_index] + route[1:] + [origin_index]
        route_names = " -> ".join(location_names[r] for r in full_route)

        print(f"\nTruck {idx}")
        print(f"Route: {route_names}")
        print(f"Inside-VRP km: {inside_km:.2f}")
        print(f"Base legs km: {base_km:.2f}")
        print(f"Total km: {total_km:.2f}")
        print(f"Cost breakdown: {fixed_cost:.2f} + {km_cost_val:.2f}")

    print(f"\nTotal fixed cost: {total_fixed:.2f} €")
    print(f"Total km cost: {total_km_cost:.2f} €")
    print(f"Total cost: {model.objVal:.2f} €")
else:
    print("Model couldn't find optimum solution.")
    
    
    
    
    
    
    
    
    