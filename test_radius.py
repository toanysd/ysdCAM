import cadquery as cq
filename = "D:/AntiGravity_Workspace/apps/ysdCAM/temp_workspace/IRI-002D(Q)_3D.step"
wp = cq.importers.importStep(filename)
f = wp.faces("%Cylinder").vals()[0]
surf = f._geomAdaptor()
print(surf.Cylinder().Radius())
