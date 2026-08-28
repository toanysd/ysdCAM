import cadquery as cq
import ezdxf
import os

def execute_mock(step_path):
    wp = cq.importers.importStep(step_path)
    
    # 1. Export 2D DXF
    dxf_path = step_path + ".contour.dxf"
    cq.exporters.exportDXF(wp, dxf_path)
    
    # 2. Extract Edges from DXF
    doc = ezdxf.readfile(dxf_path)
    msp = doc.modelspace()
    edges_data = []
    
    display_edges = []
    for entity in msp:
        if entity.dxftype() == 'LINE':
            start = entity.dxf.start
            end = entity.dxf.end
            display_edges.append({
                'type': 'Line',
                'start': [round(start.x, 3), round(start.y, 3)],
                'end': [round(end.x, 3), round(end.y, 3)],
            })
        elif entity.dxftype() == 'CIRCLE':
            center = entity.dxf.center
            radius = entity.dxf.radius
            display_edges.append({
                'type': 'Circle',
                'center': [round(center.x, 3), round(center.y, 3)],
                'radius': round(radius, 3)
            })
        elif entity.dxftype() == 'ARC':
            center = entity.dxf.center
            radius = entity.dxf.radius
            display_edges.append({
                'type': 'Arc',
                'center': [round(center.x, 3), round(center.y, 3)],
                'radius': round(radius, 3),
                'start_angle': round(entity.dxf.start_angle, 2),
                'end_angle': round(entity.dxf.end_angle, 2)
            })
            
    if display_edges:
        edges_data.append({
            "depth": 0,
            "actual_z": 0,
            "wires": display_edges
        })

    # 3. Extract Holes natively
    holes_data = []
    cyls = wp.faces("%Cylinder").vals()
    
    for cyl in cyls:
        center = cyl.Center()
        bbox = cyl.BoundingBox()
        depth = bbox.zlen
        
        radius = 0
        for e in cyl.Edges():
            if e.geomType() == "CIRCLE":
                radius = e.BoundingBox().xlen / 2.0
                break
                
        holes_data.append({
            "x": round(center.x, 3),
            "y": round(center.y, 3),
            "depth": round(depth, 3),
            "actual_z": round(center.z + depth/2.0, 3), # Top of the hole
            "diameter": round(radius * 2.0, 3)
        })
        
    print(f"Extracted {len(holes_data)} holes and {len(display_edges)} 2D edges.")
    return holes_data, edges_data

if __name__ == "__main__":
    holes, edges = execute_mock("D:/AntiGravity_Workspace/apps/ysdCAM/temp_workspace/IRI-002D(Q)_3D.step")
    print(holes[:2])
