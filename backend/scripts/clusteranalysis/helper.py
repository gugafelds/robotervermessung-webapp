import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from ast import literal_eval
from matplotlib.animation import FuncAnimation
from sklearn.preprocessing import MinMaxScaler
from tslearn.metrics import cdist_dtw
import random
import trimesh

random.seed(42)

def create_gif(values_2d, name):
    fig = plt.figure(figsize=(16, 12))
    ax = fig.add_subplot(111, projection="3d")

    normal = values_2d[values_2d["labels"] != "extra"]
    extra = values_2d[values_2d["labels"] == "extra"]

    scatter = ax.scatter(
        normal["x"],
        normal["y"],
        normal["z"],
        c=normal["labels"],
        cmap="viridis",
        s=1,
        alpha=0.1,
    )

    ax.scatter(extra["x"], extra["y"], extra["z"], color="red", s=20, alpha=0.9)

    fig.colorbar(scatter, ax=ax)
    plt.gca().invert_xaxis()

    # Animation function to rotate the view
    def animate(i):
        ax.view_init(elev=i, azim=25)  # Change the azimuth angle over time
        return (scatter,)

    ani = FuncAnimation(
        fig, animate, frames=np.arange(0, 360, 2), interval=50, blit=False
    )
    ani.save("backend/scripts/clusteranalysis/assets/" + name + ".gif", writer="pillow")

    plt.savefig("backend/scripts/clusteranalysis/assets/" + name + ".png")


def calculate_cluster_density(cluster: pd.DataFrame) -> int:
    min_x = min(min(cluster["x_start"]), min(cluster["x_end"]))
    max_x = max(max(cluster["x_start"]), max(cluster["x_end"]))
    min_y = min(min(cluster["y_start"]), min(cluster["y_end"]))
    max_y = max(max(cluster["y_start"]), max(cluster["y_end"]))
    min_z = min(min(cluster["z_start"]), min(cluster["z_end"]))
    max_z = max(max(cluster["z_start"]), max(cluster["z_end"]))

    x_length = max_x - min_x
    y_length = max_y - min_y
    z_length = max_z - min_z

    volume = x_length * y_length * z_length

    return cluster.size / volume


def cluster_density(X_cluster, centroid):
    return np.mean(np.linalg.norm(X_cluster - centroid, axis=1))


def calculate_clusterdistance_mse(point):
    cluster_centers = [
        [1635.12141307, 465.64264191, 711.22155486],
        [1610.66733913, -291.4255693, 697.2851166],
        [1251.67761453, -37.11189014, 1174.54605526],
        [1593.28908445, -671.19177399, 1166.33797729],
        [1139.49790116, 590.15154448, 1692.0600746],
        [1099.845456, -576.86809494, 1742.92568918],
        [1185.22321016, 420.01943418, 686.74335275],
        [1663.91212853, -66.37438413, 1206.42513959],
        [1172.61544256, -234.61115369, 708.99052981],
        [1015.70813156, -625.07567192, 1218.91459149],
        [1622.59130637, 534.76020715, 1200.09030498],
        [1150.58617804, 504.33929022, 1177.96295236],
    ]
    distance = 0
    # erstmal mit mse versuchen?
    # für alle center aufsummieren: 1/3 * (x-Abweichung^2 + y-Abweichung^2 + z-Abweichung^2), dann 1/7 weil lesen
    for center in cluster_centers:
        distance += abs(center[0] - point[0])
        distance += abs(center[1] - point[1])
        distance += abs(center[2] - point[2])
        distance *= 1 / 3

    return distance / 7

def calculate_clusterdistance(point, cluster_centers, prev_worst):
    distance = 0
    # 7 Metriken für Distanz
    for row in cluster_centers:
        # row is a dict, extract values in consistent order
        current = [row['x_start'], row['y_start'], row['z_start'], 
                   row['x_end'], row['y_end'], row['z_end'], row['movement']]
        # alle Distanzen aufsummieren
        for i in range(7):
            distance += abs(float(point[i]) - float(current[i]))  
    # dann durch 200 teilen weil 200 clustercenter
    distance /= 200    
    
    for row in prev_worst:
        for i in range(7):
            distance += (1/500) * (abs(float(point[i]) - float(row[i]))) 
               
    return distance

def calculate_end_point(mini, maxi, start, max_dist):
    rand = random.randint(0,1)
    if rand:
        temp = start + random.random() * max_dist
    else: 
        temp = start - random.random() * max_dist
    temp = min(temp, maxi)
    temp = max(temp, mini)
    return temp

def scale(mini: float, maxi: float, point: float):
    return (point - mini) / (maxi - mini)

def descale(mini, maxi, point):
    return point * (maxi-mini) + mini

def descale_point(point):
    if point[6]:
        movement = "circular"
    else:
        movement = "linear"
    metrics = [
        descale(400.0, 1993.35, point[0]),
        descale(-1161.82, 1094.0, point[1]),
        descale(326.39, 2005.24, point[2]),
        descale(400.0, 1993.35, point[3]),
        descale(-1161.82, 1094.0, point[4]),
        descale(326.39, 2005.24, point[5]),
        movement,
        descale(12.0, 22.0, point[7]),
    ]
    
    return metrics

def append_worst(worst_points: pd.DataFrame):
    previous = pd.read_csv("backend/scripts/clusteranalysis/worst_points.csv")
    df = pd.DataFrame(worst_points, columns=["x_start", "y_start","z_start", "x_end", "y_end", "z_end", "movement", "weight"])
    df = pd.concat([df, previous])
    df.to_csv('backend/scripts/clusteranalysis/worst_points.csv', index=False)
    
def traj_to_features(traj):
    if isinstance(traj, str):
        traj = literal_eval(traj)

    traj = np.asarray(traj, dtype=float)
    if traj.ndim == 0:
        raise ValueError(f"Expected trajectory sequence, got scalar: {traj!r}")
    if traj.size == 0:
        raise ValueError("Trajectory is empty")

    return np.concatenate([
        traj.mean(axis=0),
        traj.std(axis=0), 
        traj.min(axis=0),
        traj.max(axis=0),
        [len(traj)] 
    ])
    
def movement_to_vector(mov, max_len=10):
    mapping = {"l": 0, "c": 1}

    vec = [mapping.get(x, -1) for x in mov]
    vec = vec[:max_len]

    # Padding
    vec += [-1] * (max_len - len(vec))

    return vec

def compute_medoid(cluster_trajs):
    # DTW distance matrix
    D = cdist_dtw(cluster_trajs)

    # Sum of distances for each trajectory
    dist_sum = D.sum(axis=1)

    # index of minimum
    medoid_idx = np.argmin(dist_sum)

    return cluster_trajs[medoid_idx], medoid_idx
