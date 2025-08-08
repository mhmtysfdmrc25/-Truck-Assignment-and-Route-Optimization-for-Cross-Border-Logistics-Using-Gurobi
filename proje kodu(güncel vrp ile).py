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
origin_index    = lower.index("istanbul")
customs_index   = lower.index("kapıkule")
customs_index_2 = lower.index("strasbourg") #fransaya giriş şehri genellikle karayolu için buradan giriş sağlanıyormuş
customs_index_3 = lower.index("melun")      #vip lojistik firmasının burada acentesi olduğundan, tırlar ilk buraya gidip evrak işlerini halledip fransadaki diğer şehirlere dağılıyor.
transit_locs    = ["istanbul", "kapıkule", "strasbourg"]
transit_indexes = [lower.index(name) for name in transit_locs]
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
    lower.index("melun"): 3933
}

# 4) Parametreler
num_trucks     = 110
truck_capacity = 23000    # kg (gümrük kanunlarına göre çeker+dorse max 40ton alabilir, 23ton ortalama araca eklenebilen mal)
fixed_cost     = 2700     # € / truck (ortalama şoför, hakediş, otoyol masrafları vs.)
km_cost        = 0.32     # € / km (tır başına ortalama benzin masrafı km başına, şirketlere özel indirimle birlikte, 3200km için 1000LT benzin ortalama 1€/lt'den)
distance       = df.values.tolist()

# 5) Model Kurulumu (routing ile)
model = Model("TruckRouting")
x = model.addVars(num_trucks, num_locations, vtype=GRB.BINARY, name="visit")
z = model.addVars(num_trucks, vtype=GRB.BINARY, name="use_truck")
y = model.addVars(num_trucks, num_locations, num_locations, vtype=GRB.BINARY, name="arc")
u = model.addVars(num_trucks, num_locations, lb=0, ub=num_locations, vtype=GRB.CONTINUOUS, name="u")

# Amaç fonksiyonu: sabit maliyet + km maliyeti
model.setObjective(
    quicksum(fixed_cost * z[t] for t in range(num_trucks))
    + km_cost * quicksum(distance[i][j] * y[t, i, j]
        for t in range(num_trucks)
        for i in range(num_locations)
        for j in range(num_locations) if i != j),GRB.MINIMIZE)

# 6) Kısıtlar
# a) Arc’larla x ilişkisi (flow conservation), 
for t in range(num_trucks):
    for i in range(num_locations):
        model.addConstr(quicksum(y[t, j, i] for j in range(num_locations) if j != i) == x[t, i], 
            name=f"flow_in_{t}_{i}")
        
        model.addConstr(quicksum(y[t, i, j] for j in range(num_locations) if j != i) == x[t, i],
            name=f"flow_out_{t}_{i}")

# b) Her teslimat lokasyonu tam bir kez ziyaret edilmeli
for j in delivery_indexes:
    model.addConstr(quicksum(y[t, i, j]
                 for t in range(num_trucks)
                 for i in range(num_locations) if i != j) == 1,
        name=f"visit_once_{j}")

# c) Transit noktaları her kullanılan tır için güzergahda olmalı
for t in range(num_trucks):
    for idx in transit_indexes:
        model.addConstr(x[t, idx] == z[t], name=f"transit_{idx}_{t}")

# d) Ziyaret ⇒ Tır kullanımı
for t in range(num_trucks):
    for i in range(num_locations):
        model.addConstr(x[t, i] <= z[t], name=f"use_if_visit_{t}_{i}")

# e) Kapasite kısıtı
for t in range(num_trucks):
    model.addConstr(quicksum(demands[j] * x[t, j] for j in delivery_indexes) <= truck_capacity,
        name=f"cap_{t}")

# f) MTZ alt tur önleme
for t in range(num_trucks):
    for i in range(num_locations):
        for j in range(num_locations):
            if i != j and j != origin_index:
                model.addConstr(u[t, i] - u[t, j] + num_locations * y[t, i, j] <= num_locations - 1,
                                name=f"mtz_{t}_{i}_{j}")

# g) Başlangıç ve bitiş origin (istanbul) kontrolü
for t in range(num_trucks):
    model.addConstr(quicksum(y[t, origin_index, j]
                 for j in range(num_locations) if j != origin_index) == z[t],
        name=f"start_{t}")
    
    model.addConstr(quicksum(y[t, j, origin_index]
                 for j in range(num_locations) if j != origin_index) == z[t],
        name=f"end_{t}")

# 7) Modeli Çöz
model.optimize()

# 8) Sonuçları Yazdır
if model.status == GRB.OPTIMAL:
    used = [t for t in range(num_trucks) if z[t].x > 0.5]
    total_fixed = sum(fixed_cost for t in used)
    total_dist = 0.0

    print(f"\n{len(used)} trucks have been used for this order set.")
    print(f"Fixed cost: {total_fixed:.2f} €")

    for idx, t in enumerate(used, start=1):
        route = [origin_index]
        cur = origin_index
        while True:
            nxt = next(
                j for j in range(num_locations)
                if j != cur and y[t, cur, j].x > 0.5
            )
            route.append(nxt)
            if nxt == origin_index:
                break
            cur = nxt

        dist_cost = sum(distance[route[i]][route[i+1]]
            for i in range(len(route)-1)) * km_cost
        total_dist += dist_cost

        print(f"\n▶ Tır {idx} (gas cost: {dist_cost:.2f} €):")
        for node in route:
            print(f"   - {location_names[node]}")

    print(f"\nTotal gas cost: {total_dist:.2f} €")
    print(f"Total cost: {total_fixed + total_dist:.2f} €")
else:
    print("Model couldn't find optimum solution.")
   
# print the LP file
model.write('TruckRouting.lp')
    
# print the sol file
model.write('TruckRouting.sol')