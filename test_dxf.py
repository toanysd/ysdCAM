import cadquery as cq

wp = cq.Workplane("XY").box(10, 10, 10).faces(">Z").workplane().circle(2).cutThruAll()
cq.exporters.exportDXF(wp, "test_out.dxf")
print("DXF exported to test_out.dxf")
