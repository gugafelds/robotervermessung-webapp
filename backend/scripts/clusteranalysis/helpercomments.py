"""
range_clusters = [3,9]


clusterer_2 = KMeans(n_clusters=2, random_state=42)
raw_2 = clusterer_2.fit_predict(values_2d)
clusterer_3 = KMeans(n_clusters=3, random_state=42)
raw_3 = clusterer_3.fit_predict(values_2d)
clusterer_9 = KMeans(n_clusters=9, random_state=42)
raw_9 = clusterer_9.fit_predict(values_2d)

w_2 = clusterer_2.fit_predict(values_2d_with_w)
w_3 = clusterer_3.fit_predict(values_2d_with_w)

create_gif(values_2d, raw_2, "cluster_raw_2")
create_gif(values_2d, raw_3, "cluster_raw_3")
create_gif(values_2d, raw_9, "cluster_raw_9")
create_gif(values_2d_with_w, w_2, "cluster_w_2")
create_gif(values_2d_with_w, w_3, "cluster_w_3")
create_gif(values_2d_with_w, w_12, "cluster_w_12")


clusterer = KMeans(n_clusters=2, random_state=42)
cluster_labels = clusterer.fit_predict(values_2d)
silhouette_avg = silhouette_score(values_2d, cluster_labels)
print(silhouette_avg)

for cluster_number in range_clusters:
    clusterer = KMeans(n_clusters=cluster_number, random_state=42)
        cluster_labels = clusterer.fit_predict(values_2d)
        silhouette_avg = silhouette_score(values_2d, cluster_labels)
        print(
            "For n_clusters =",
            cluster_number,
            "The average silhouette_score is :",
            silhouette_avg,
        )
    
clusterer_12 = KMeans(n_clusters=12, random_state=42)
w_12 = clusterer_12.fit_predict(values_2d_with_w)
df = pd.DataFrame({'cluster': w_12})
df.to_csv('backend/scripts/clusteranalysis/w_12.csv', index=False)

densities = []
for i in clusters:
    density = calculate_cluster_density(clusters[i])
    dens = Decimal(str(round(density, 6)))
    densities.append(dens)
    print(i + ": " + str(dens))
    
densities.sort()
print(densities)


# finding and plotting furthest points

values_2d = pd.read_csv("backend/scripts/clusteranalysis/setpoints2.csv")
values_2d_with_w = values_2d
values_2d_with_w["w"] = values_2d.apply(lambda row: np.linalg.norm([0,0,0] - row[['x', 'y', 'z']]), axis = 1)
x_min, x_max = values_2d["x"].min(), values_2d["x"].max()
y_min, y_max = values_2d["y"].min(), values_2d["y"].max()
z_min, z_max = values_2d["z"].min(), values_2d["z"].max()

df = pd.read_csv('backend/scripts/clusteranalysis/w_12.csv')
labels = df['cluster'].values

dataset = values_2d_with_w
dataset["labels"] = labels
clusters = {
"cluster_0" : dataset[dataset["labels"] == 0],
"cluster_1" : dataset[dataset["labels"] == 1],
"cluster_2" : dataset[dataset["labels"] == 2],
"cluster_3" : dataset[dataset["labels"] == 3],
"cluster_4" : dataset[dataset["labels"] == 4],
"cluster_5" : dataset[dataset["labels"] == 5],
"cluster_6" : dataset[dataset["labels"] == 6],
"cluster_7" : dataset[dataset["labels"] == 7],
"cluster_8" : dataset[dataset["labels"] == 8],
"cluster_9" : dataset[dataset["labels"] == 9],
"cluster_10" : dataset[dataset["labels"] == 10],
"cluster_11" : dataset[dataset["labels"] == 11]}

# seed setzen für Reproduzierbarkeit
random.seed(42)

# zufällige Punkte erzeugen
random_values = []
for _ in range(10000):
    point = [random.uniform(400.0, 1993.35), random.uniform(-1161.82, 1094.0), random.uniform(326.39, 2005.24)]
    random_values.append(point)

# ranken, welche davon die "schlechtesten" sind bzw am weitesten insgesamt von den clusterzentren weg -> wie genau? -> erstmal mit richtig hässlichen Vergleichen maybe, später dann effizienter
greatest_distances = {}
count = 0
for i in random_values:
    if count < 100:
        greatest_distances[calculate_clusterdistance(i)] = i
        count += 1
    else:
        greatest_distances = collections.OrderedDict(sorted(greatest_distances.items()))
        first_key = next(iter(greatest_distances))
        if calculate_clusterdistance(i) > first_key:
            greatest_distances.pop(first_key)
            greatest_distances[calculate_clusterdistance(i)] = i
        count += 1

# das weitest entfernte Prozent behalten
worst_points = list(greatest_distances.values())

# erstmal in df umwandeln, damit überhaupt mit anderen geplottet werden kann
worst_df = pd.DataFrame(worst_points, columns=["x", "y", "z"])
worst_df["w"] = worst_df.apply(lambda row: np.linalg.norm([0,0,0] - row[['x', 'y', 'z']]), axis = 1)
worst_df["labels"] = "extra"

# an dataset anfügen -> nur ein Array zum plotten übergeben
dataset = pd.concat([dataset, worst_df], ignore_index=True)

# gemeinsam mit den Clustern plotten (möglichst GIF und png) zur Visualisierung, Farbe maybe rot und vllt bisschen größer und undurchsichtiger
create_gif(dataset, "with_outliers")


# analyse der densities mit verschieden vielen clustern:
densities = []
    sum = 0
    for i in range (k):
        data = values[values["label"] == i]
        dens = calculate_cluster_density(data)
        sum += dens
        densities.append(dens)
        
    all_densities[k] = densities
    avg_density = sum / k
    min_density = min(densities)
    max_density = max(densities)
    std_dev = np.std(densities)
    
    print("For k=" + str(k) + " clusters: average density: " + str(avg_density) + ", min density: " + str(min_density) + ", max density: " + str(max_density))
    print("Standard deviation: " + str(std_dev))

# clustering scaled data in 200 clusters
values = pd.read_csv("backend/scripts/clusteranalysis/newdata.csv")
# print(values.head())
values.replace(to_replace={"linear": 0, "circular": 1}, inplace=True)
scaler = MinMaxScaler()
ranges = {
    "x_start": [values["x_start"].min(), values["x_start"].max()],
    "y_start": [values["y_start"].min(), values["y_start"].max()],
    "z_start": [values["z_start"].min(), values["z_start"].max()],
    "x_end": [values["x_end"].min(), values["x_end"].max()],
    "y_end": [values["y_end"].min(), values["y_end"].max()],
    "z_end": [values["z_end"].min(), values["z_end"].max()],
    "weight": [values["weight"]. min(), values["weight"].max()]
}
scalable_columns = ["x_start", "y_start", "z_start", "x_end", "y_end", "z_end", "weight"]

for column in scalable_columns:
    data = pd.DataFrame(values[column])
    scaler.fit(data)
    transformed_data = scaler.transform(data)
    values[column] = transformed_data
      
# print(values.head())
# print(ranges)
clusterer = KMeans(n_clusters=200, random_state=42)
cluster_labels = clusterer.fit_predict(values)
values["label"] = cluster_labels
centers = clusterer.cluster_centers_



labeled_data = pd.read_csv("backend/scripts/clusteranalysis/newdata_with_labels.csv")
centers = pd.read_csv("backend/scripts/clusteranalysis/centers_newdata.csv")
unscaled_data = pd.read_csv("backend/scripts/clusteranalysis/newdata.csv")

min_x = min(min(unscaled_data["x_start"]), min(unscaled_data["x_end"]))
max_x = max(max(unscaled_data["x_start"]), max(unscaled_data["x_end"]))
min_y = min(min(unscaled_data["y_start"]), min(unscaled_data["y_end"]))
max_y = max(max(unscaled_data["y_start"]), max(unscaled_data["y_end"]))
min_z = min(min(unscaled_data["z_start"]), min(unscaled_data["z_end"]))
max_z = max(max(unscaled_data["z_start"]), max(unscaled_data["z_end"]))

weights_temp = set((unscaled_data["weight"]))
weights = list(weights_temp)

# zufällige Bahnen erzeugen, wichtig bei akutellen Daten: minmax scaling beachten, aufpassen, dass Distanzen nicht zu groß werden
random_trajs = []

x_distances = []
y_distances = []
z_distances = []

for i in unscaled_data.head().itertuples(index=False):
    x_distances.append(abs(i.x_start - i.x_end))
    y_distances.append(abs(i.y_start - i.y_end))
    z_distances.append(abs(i.z_start - i.z_end))

max_x_dist = max(x_distances)
max_y_dist = max(y_distances)
max_z_dist = max(z_distances)


for i in range(10000):
    x_start = random.uniform(400.0, 1993.35)
    y_start = random.uniform(-1161.82, 1094.0)
    z_start = random.uniform(326.39, 2005.24)

    x_end = scale(
        400.0, 1993.35, calculate_end_point(400.0, 1993.35, x_start, max_x_dist)
    )
    y_end = scale(
        -1161.82, 1094.0, calculate_end_point(-1161.82, 1094.0, y_start, max_y_dist)
    )
    z_end = scale(
        326.39, 2005.24, calculate_end_point(326.39, 2005.24, z_start, max_z_dist)
    )

    x_start = scale(400.0, 1993.35, x_start)
    y_start = scale(-1161.82, 1094.0, y_start)
    z_start = scale(326.39, 2005.24, z_start)

    movement = random.randint(0, 1)
    weight = scale(12.0, 22.0, weights[random.randint(0, len(weights) - 1)])
    point = [x_start, y_start, z_start, x_end, y_end, z_end, movement, weight]
    random_trajs.append(point)

greatest_distances = {}
count = 0
for i in random_trajs:
    if count < 100:
        greatest_distances[calculate_clusterdistance(i, centers)] = i
        count += 1
    else:
        greatest_distances = collections.OrderedDict(sorted(greatest_distances.items()))
        first_key = next(iter(greatest_distances))
        if calculate_clusterdistance(i, centers) > first_key:
            greatest_distances.pop(first_key)
            greatest_distances[calculate_clusterdistance(i, centers)] = i
        count += 1

# das weitest entfernte Prozent behalten
worst_points = list(greatest_distances.values())

worst_points_readable = []

for point in worst_points:
    worst_points_readable.append(descale_point(point))


print(worst_points_readable)


append_worst(worst_points)



whole_trajs["coordinates"] = whole_trajs["coordinates"].apply(literal_eval)

min_x, max_x, min_y, max_y, min_z, max_z = (
    400.0,
    1993.35,
    -1161.82,
    1094.0,
    326.39,
    2005.24,
)

for coordinate in whole_trajs["coordinates"]:
    for point in coordinate:
        point[0] = scale(min_x, max_x, point[0])
        point[1] = scale(min_y, max_y, point[1])
        point[2] = scale(min_z, max_z, point[2])

X = np.vstack(whole_trajs["coordinates"].apply(traj_to_features).values)

mov_features = whole_trajs["traj_movement"].apply(movement_to_vector)
mov_features = np.vstack(mov_features.values)
X = np.hstack([X, mov_features])


clusterer = MiniBatchKMeans(
    n_clusters=5, random_state=42, batch_size=2048, n_init="auto"
)

cluster_labels = clusterer.fit_predict(X)
whole_trajs["label"] = cluster_labels
whole_trajs.to_csv('backend/scripts/clusteranalysis/wholetraj_labeled.csv', index=False)

random.seed(42)

centroids = pd.read_csv("backend/scripts/clusteranalysis/wholetraj_centroids.csv")
centroids.drop("cluster_id", axis=1, inplace=True)
centroids = centroids.to_numpy()

random_trajs = pd.DataFrame(columns=["coordinates", "traj_movement"])
for _ in range(10000):
    amount = random.randint(2, 5)
    coordinates = [
        [
            random.uniform(400.0, 1993.35),
            random.uniform(-1161.82, 1094.0),
            random.uniform(326.39, 2005.24),
        ]
    ]
    movements = ""
    for i in range(amount):
        movement = random.randint(0, 1)
        if movement:
            movements += "c"
        else:
            movements += "l"

        if i > 0:
            coordinate = [
                calculate_end_point(400.0, 1993.35, coordinates[i-1][0], 449),
                calculate_end_point(-1161.82, 1094.0, coordinates[i-1][1], 675),
                calculate_end_point(326.39, 2005.24, coordinates[i-1][2], 553),
            ]
            coordinates.append(coordinate)

    random_trajs.loc[len(random_trajs)] = [coordinates, movements]
    
    
    trajs_labeled.drop("traj_id", axis=1, inplace=True)

for coordinate in trajs_labeled["coordinates"]:
    for point in coordinate:
        point[0] = scale(400.0, 1993.35, point[0])
        point[1] = scale(-1161.82, 1094.0, point[1])
        point[2] = scale(326.39, 2005.24, point[2])

mapping = {"l": 0, "c": 1}

trajs_labeled["traj_movement"] = trajs_labeled["traj_movement"].apply(
    lambda mov: [mapping.get(x, -1) for x in mov][:10]
)

cluster_0 = trajs_labeled[trajs_labeled["label"] == 0].copy()
cluster_1 = trajs_labeled[trajs_labeled["label"] == 1].copy()
cluster_2 = trajs_labeled[trajs_labeled["label"] == 2].copy()
cluster_3 = trajs_labeled[trajs_labeled["label"] == 3].copy()
cluster_4 = trajs_labeled[trajs_labeled["label"] == 4].copy()

cluster_0.drop("label", axis=1, inplace=True)
cluster_1.drop("label", axis=1, inplace=True)
cluster_2.drop("label", axis=1, inplace=True)
cluster_3.drop("label", axis=1, inplace=True)
cluster_4.drop("label", axis=1, inplace=True)

medoid_data = []

med_0, idx_0 = compute_medoid(cluster_0["coordinates"].tolist())
print(med_0, idx_0)
medoid_data.append(
    {
        "cluster_id": 0,
        "coordinates": med_0,
    }
)

med_1, idx_1 = compute_medoid(cluster_1["coordinates"].tolist())
print(med_1, idx_1)
medoid_data.append(
    {
        "cluster_id": 1,
        "coordinates": med_1,
    }
)

med_2, idx_2 = compute_medoid(cluster_2["coordinates"].tolist())
print(med_2, idx_2)
medoid_data.append(
    {
        "cluster_id": 2,
        "coordinates": med_2,
    }
)

med_3, idx_3 = compute_medoid(cluster_3["coordinates"].tolist())
print(med_3, idx_3)
medoid_data.append(
    {
        "cluster_id": 3,
        "coordinates": med_3,
    }
)

med_4, idx_4 = compute_medoid(cluster_4["coordinates"].tolist())
print(med_4, idx_4)
medoid_data.append(
    {
        "cluster_id": 4,
        "coordinates": med_4,
    }
)

df = pd.DataFrame(medoid_data)

df.to_csv("backend/scripts/clusteranalysis/medoids.csv", index=False)

medoids = medoids["coordinates"].apply(literal_eval)

random_trajs = pd.read_csv("backend/scripts/clusteranalysis/randomtrajs.csv")
random_trajs["coordinates"] = random_trajs["coordinates"].apply(literal_eval)

medoids_np = [np.array(m, dtype=np.double) for m in medoids]
dists = []

for coordinate in random_trajs["coordinates"]:
    coord_np = np.array(coordinate, dtype=np.double)
    dist = 0
    for med_np in medoids_np:
        dist += dtw_ndim.distance_fast(coord_np, med_np, inner_dist="euclidean")

    dists.append(dist/5)

random_trajs["dtw_distance"] = dists

top_100 = random_trajs.nlargest(100, "dtw_distance")
top_100["traj_movement"] = top_100["traj_movement"].apply(literal_eval)

for coordinate in top_100["coordinates"]:
    for point in coordinate:
        point[0] = descale(400.0, 1993.35, point[0])
        point[1] = descale(-1161.82, 1094.0, point[1])
        point[2] = descale(326.39, 2005.24, point[2])

mapping = {0: "l", 1: "c"}

top_100["traj_movement"] = top_100["traj_movement"].apply(
    lambda mov: [mapping.get(x, -1) for x in mov][:10]
)

top_100.to_csv("backend/scripts/clusteranalysis/wholetraj_worst.csv", index=False)


centers = pd.read_csv(
    "C:/Users/muell/Desktop/Arbeit/Robotervermessung/csvs/centers_newdata.csv"
)
centers.drop("weight", axis=1, inplace=True)

# Convert to dict for mutation
centers_dict = centers.to_dict("records")

for row in centers_dict:
    row["x_start"] = descale(400.0, 1993.35, row["x_start"])
    row["x_end"] = descale(400.0, 1993.35, row["x_end"])
    row["y_start"] = descale(-1161.82, 1094.0, row["y_start"])
    row["y_end"] = descale(-1161.82, 1094.0, row["y_end"])
    row["z_start"] = descale(326.39, 2005.24, row["z_start"])
    row["z_end"] = descale(326.39, 2005.24, row["z_end"])

random_trajs = []

x_distances = []
y_distances = []
z_distances = []

for i in traj_data.head().itertuples(index=False):
    x_distances.append(abs(i.x_start - i.x_end))
    y_distances.append(abs(i.y_start - i.y_end))
    z_distances.append(abs(i.z_start - i.z_end))

max_x_dist = max(x_distances)
max_y_dist = max(y_distances)
max_z_dist = max(z_distances)

x_min, x_max = 500, 1900
y_min, y_max = -1100, 1100
z_min, z_max = 400, 2000

for i in range(100000):
    x_start = random.uniform(x_min, x_max)
    y_start = random.uniform(y_min, y_max)
    z_start = random.uniform(z_min, z_max)

    x_end = calculate_end_point(x_min, x_max, x_start, max_x_dist)
    y_end = calculate_end_point(y_min, y_max, y_start, max_y_dist)
    z_end = calculate_end_point(z_min, z_max, z_start, max_z_dist)

    movement = random.randint(0, 1)  # 0: circular, 1: linear

    point = [x_start, y_start, z_start, x_end, y_end, z_end, movement]
    if solid.contains([[point[0],point[1],point[2]]]) and solid.contains([[point[3],point[4],point[5]]]):
        random_trajs.append(point)



greatest_distances = {}
count = 0
for i in random_trajs:
    if count < 100:
        greatest_distances[calculate_clusterdistance(i, centers_dict, prev_trajs)] = i
        count += 1
    else:
        greatest_distances = collections.OrderedDict(sorted(greatest_distances.items()))
        first_key = next(iter(greatest_distances))
        if calculate_clusterdistance(i, centers_dict, prev_trajs) > first_key:
            greatest_distances.pop(first_key)
            greatest_distances[calculate_clusterdistance(i, centers_dict, prev_trajs)] = i
        count += 1

# das weitest entfernte Prozent behalten
worst_trajs = list(greatest_distances.values())
worst_trajs = np.array(worst_trajs)
worst_trajs = np.concatenate((worst_trajs, prev_trajs), axis=0)

df = pd.DataFrame(worst_trajs, columns=['x_start', 'y_start', 'z_start', 'x_end', 'y_end', 'z_end', 'movement'])
df.to_csv('C:/Users/muell/Desktop/Arbeit/Robotervermessung/csvs/worsttrajs.csv', index=False)
"""
