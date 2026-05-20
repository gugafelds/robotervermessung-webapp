import ast

def plot(dict):
    traj = dict["traj_similarity"]
    seg = dict["segment_similarity"]

    traj_res = traj["results"]

    traj_coords = []
    for i in ast.literal_eval(traj["target"]):
        coord = [i["x_cmd"], i["y_cmd"], i["z_cmd"]]
        traj_coords.append(coord)

    print("Coordinates of target trajectory setpoints: ", traj_coords)
    print("\nResults for similar trajectories:")
    for res in traj_res:
        print(
            " Id: ", res["seg_id"],
            ",   movement: ", res["features"]["movement_type"],
            ",   rank stage 1: ", res["rank_stage1"],
            ",   dtw distance: ", res["dtw_distance"],
            ",   rank stage 2: ", res["rank_stage2"],
        )

    print("\n\nResults for similar segments:")

    for i in range(len(seg)):
        coords = []
        for j in ast.literal_eval(seg[i]["similar_segments"]["target"]):
            coord = [j["x_cmd"], j["y_cmd"], j["z_cmd"]]
            coords.append(coord) 

        print(f" Segment {i+1}: ({coords[0]} - {coords[1]})")
        for s in seg[i]["similar_segments"]["results"]:
            print(
            "  Id: ", s["seg_id"],
            ",   movement: ", s["features"]["movement_type"],
            ",   rank stage 1: ", s["rank_stage1"],
            ",   dtw distance: ", s["dtw_distance"],
            ",   rank stage 2: ", s["rank_stage2"],
        )
        print("")
