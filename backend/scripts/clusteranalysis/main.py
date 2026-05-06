import pandas as pd
import numpy as np
import random
import trimesh
import collections
from helper import calculate_end_point, calculate_clusterdistance, descale

random.seed(42)


def showmesh(points_np, solid, additional):
    additional = np.array(additional) / 50
    additional_mesh = trimesh.points.PointCloud(additional)
    additional_mesh.colors = np.tile([0, 255, 0, 255], (len(additional), 1))

    points_np = points_np / 50

    points = trimesh.points.PointCloud(points_np)
    points.colors = np.tile([255, 255, 255, 255], (len(points_np), 1))

    solid.visual.face_colors = [250, 0, 0, 20]

    scene = trimesh.Scene()
    scene.add_geometry(solid)
    scene.add_geometry(points)
    scene.add_geometry(additional_mesh)

    scene.show(resolution=(800, 600))


def showmesh_trajs(points_np, solid, additional, worst):
    additional = np.array(additional) / 50
    additional_mesh = trimesh.points.PointCloud(additional)
    additional_mesh.colors = np.tile([0, 255, 0, 255], (len(additional), 1))

    points_np = points_np / 50

    points = trimesh.points.PointCloud(points_np)
    points.colors = np.tile([255, 255, 255, 255], (len(points_np), 1))

    solid.visual.face_colors = [250, 0, 0, 20]

    scene = trimesh.Scene()
    scene.add_geometry(solid)
    #scene.add_geometry(points)
    scene.add_geometry(additional_mesh)

    for traj in worst:
        if traj[6]:
            # display straight line for traj
            path = trimesh.path.Path3D(
                entities=[trimesh.path.entities.Line(points=[0, 1])],
                vertices=np.array(
                    [
                        [traj[0] / 50, traj[1] / 50, traj[2] / 50],
                        [traj[3] / 50, traj[4] / 50, traj[5] / 50],
                    ]
                ),
                colors=[[255, 0, 0, 255]],
            )
            scene.add_geometry(geometry=path)

        else:
            # display as curve
            points = circle_points(
                [traj[0] / 50, traj[1] / 50, traj[2] / 50],
                [traj[3] / 50, traj[4] / 50, traj[5] / 50],
            )
            if not solid.contains(points).all():
                n = np.array([0.0, 0.0, 1.0])
                while not solid.contains(points).all():
                    n -= [0, 0, 0.1]
                    if (n < -1).any():
                        points = []
                        break

                    points = circle_points(
                        [traj[0] / 50, traj[1] / 50, traj[2] / 50],
                        [traj[3] / 50, traj[4] / 50, traj[5] / 50],
                        n=n,
                    )

            entities = [
                trimesh.path.entities.Line([i, i + 1]) for i in range(len(points) - 1)
            ]

            if len(points) < 2:
                continue

            path = trimesh.path.Path3D(
                entities=entities,
                vertices=points,
            )
            path.colors = np.tile([0, 0, 255, 255], (len(path.entities), 1))
            scene.add_geometry(geometry=path)

    scene.export(
        "C:/Users/muell/Desktop/Arbeit/Robotervermessung/assets/additional_trajs_only.glb"
    )
    scene.show(resolution=(800, 600))


def circle_points(start, end, num_points=100, n=np.array([0, 0, 1])):
    start = np.array(start, dtype=float)
    end = np.array(end, dtype=float)
    center = (start + end) / 2
    d = end - start

    rad = np.linalg.norm(d) / 2

    if np.allclose(np.cross(d, n), 0):
        n = np.array([0, 1, 0])

    u = start - center
    u /= np.linalg.norm(u)

    v = np.cross(n, u)
    v /= np.linalg.norm(v)

    angles = np.linspace(0, np.pi, num_points)

    points = [center + rad * (np.cos(t) * u + np.sin(t) * v) for t in angles]

    return np.array(points)


setpoints = pd.read_csv(
    "C:/Users/muell/Desktop/Arbeit/Robotervermessung/csvs/setpoints.csv"
)
points_np = setpoints.to_numpy()

worst = pd.read_csv(
    "C:/Users/muell/Desktop/Arbeit/Robotervermessung/csvs/worstpoints.csv"
)
prev_worst = worst[["x", "y", "z"]].to_numpy()

traj_data = pd.read_csv(
    "C:/Users/muell/Desktop/Arbeit/Robotervermessung/csvs/newdata2.csv"
)

prev_trajs = pd.read_csv(
    "C:/Users/muell/Desktop/Arbeit/Robotervermessung/csvs/worsttrajs2.csv"
)
prev_trajs = prev_trajs[
    ["x_start", "y_start", "z_start", "x_end", "y_end", "z_end", "movement"]
].to_numpy()

traj_np = traj_data[
    ["x_start", "y_start", "z_start", "x_end", "y_end", "z_end", "movement"]
].to_numpy()

smallest_distance = 0

for row in traj_np:
    start = [row[0], row[1], row[2]]
    end = [row[3], row[4], row[5]]
    d = np.array(end) - np.array(start)
    dist = np.linalg.norm(d)
    if dist < smallest_distance:
        smallest_distance = dist

for traj in prev_trajs:
    start = [traj[0], traj[1], traj[2]]
    end = [traj[3], traj[4], traj[5]]
    d = np.array(end) - np.array(start)
    dist = np.linalg.norm(d)
    if dist < smallest_distance:
        prev_trajs = prev_trajs[prev_trajs != traj]


mesh = trimesh.load_mesh(
    "C:/Users/muell/Desktop/Arbeit/Robotervermessung/assets/Arbeitsbereich.STL"
)
corners = np.array([[500, -1100, 400], [1900, 1100, 2000]])  # min corner  # max corner

bounds = trimesh.creation.box(bounds=corners)

solid = trimesh.boolean.intersection([mesh, bounds])

"""centers = pd.read_csv(
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
        worst_trajs = list(greatest_distances.values())
        worst_trajs = np.array(worst_trajs)
        greatest_distances[calculate_clusterdistance(i, centers_dict, prev_trajs, worst_trajs)] = i
        count += 1
    else:
        greatest_distances = collections.OrderedDict(sorted(greatest_distances.items()))
        first_key = next(iter(greatest_distances))
        worst_trajs = list(greatest_distances.values())
        worst_trajs = np.array(worst_trajs)
        dist = calculate_clusterdistance(i, centers_dict, prev_trajs, worst_trajs)
        if dist > first_key:
            greatest_distances.pop(first_key)
            greatest_distances[dist] = i
        count += 1

# das weitest entfernte Prozent behalten
worst_trajs = list(greatest_distances.values())
worst_trajs = np.array(worst_trajs)
worst_trajs = np.concatenate((worst_trajs, prev_trajs), axis=0)

df = pd.DataFrame(worst_trajs, columns=['x_start', 'y_start', 'z_start', 'x_end', 'y_end', 'z_end', 'movement'])
df.to_csv('C:/Users/muell/Desktop/Arbeit/Robotervermessung/csvs/worsttrajs2.csv', index=False)

"""
mesh.vertices[:, 0] *= 1.1
mesh.apply_scale(1 / 50)
bounds.apply_scale(1 / 50)

solid = trimesh.boolean.intersection([mesh, bounds])

points = trimesh.points.PointCloud(points_np)
points.colors = np.tile([0, 255, 255, 255], (len(points_np), 1))

solid.visual.face_colors = [250, 0, 0, 60]

showmesh_trajs(points_np, solid, prev_worst, prev_trajs)
