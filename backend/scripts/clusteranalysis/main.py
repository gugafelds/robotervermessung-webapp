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
    scene.add_geometry(points)
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
        "C:/Users/muell/Desktop/Arbeit/Robotervermessung/assets/additional_trajs.glb"
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
    "C:/Users/muell/Desktop/Arbeit/Robotervermessung/csvs/worsttrajs.csv"
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

mesh.vertices[:, 0] *= 1.1
mesh.apply_scale(1 / 50)
bounds.apply_scale(1 / 50)

solid = trimesh.boolean.intersection([mesh, bounds])

points = trimesh.points.PointCloud(points_np)
points.colors = np.tile([0, 255, 255, 255], (len(points_np), 1))

solid.visual.face_colors = [250, 0, 0, 60]

showmesh_trajs(points_np, solid, prev_worst, prev_trajs)
