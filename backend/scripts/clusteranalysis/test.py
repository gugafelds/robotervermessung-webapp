import pandas as pd
import numpy as np
import trimesh

setpoints = pd.read_csv(
    "C:/Users/muell/Desktop/Arbeit/Robotervermessung/csvs/setpoints.csv"
)

print("x_min: ", min(setpoints["x"]), ", x_max: ", max(setpoints["x"]), ", y_min: ", min(setpoints["y"]), ", y_max: ", max(setpoints["y"]), ", z_min: ", min(setpoints["z"]), "z_max: ", max(setpoints["z"]))
points_np = setpoints.to_numpy()

mesh = trimesh.load_mesh(
    "C:/Users/muell/Desktop/Arbeit/Robotervermessung/assets/Arbeitsbereich.STL"
)
corners = np.array([[500, -1100, 400], [1900, 1100, 2000]])  # min corner  # max corner
bounds = trimesh.creation.box(bounds=corners)

mesh.vertices[:, 0] *= 1.1
mesh.apply_scale(1 / 50)
bounds.apply_scale(1 / 50)

solid = trimesh.boolean.intersection([mesh, bounds])
points_np = points_np / 50

points = trimesh.points.PointCloud(points_np)
points.colors = np.tile([0, 255, 255, 255], (len(points_np), 1))

solid.visual.face_colors = [250, 0, 0, 60]

scene = trimesh.Scene()
scene.add_geometry(solid)
scene.add_geometry(points)

print(solid.bounds*50)
scene.show(resolution=(800, 600))