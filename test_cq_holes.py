import cadquery as cq
import sys
import os

filename = "D:/AntiGravity_Workspace/apps/ysdCAM/temp_workspace/IRI-002D(Q)_3D.step"
if not os.path.exists(filename):
    print("File not found")
    sys.exit(0)

wp = cq.importers.importStep(filename)
cyls = wp.faces("%Cylinder").vals()
print(f"Found {len(cyls)} cylinders")
for i, f in enumerate(cyls[:5]):
    bbox = f.BoundingBox()
    print(f"Cyl {i}: Center={f.Center()}, Depth={bbox.zlen}")
    for e in f.Edges():
        if e.geomType() == "CIRCLE":
            print(f"  Circle Edge: radius ~ {e.BoundingBox().xlen / 2}")
