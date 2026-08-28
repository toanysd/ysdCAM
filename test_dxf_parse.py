import ezdxf
import json

dxf_path = "D:/AntiGravity_Workspace/apps/ysdCAM/temp_workspace/model_contour.dxf"
doc = ezdxf.readfile(dxf_path)
msp = doc.modelspace()

edges = []
for entity in msp:
    if entity.dxftype() == 'LINE':
        start = entity.dxf.start
        end = entity.dxf.end
        edges.append({
            'type': 'Line',
            'start': [start.x, start.y],
            'end': [end.x, end.y]
        })
    elif entity.dxftype() == 'CIRCLE':
        center = entity.dxf.center
        radius = entity.dxf.radius
        edges.append({
            'type': 'Circle',
            'center': [center.x, center.y],
            'radius': radius
        })
    elif entity.dxftype() == 'ARC':
        center = entity.dxf.center
        radius = entity.dxf.radius
        start_angle = entity.dxf.start_angle
        end_angle = entity.dxf.end_angle
        edges.append({
            'type': 'Arc',
            'center': [center.x, center.y],
            'radius': radius,
            'start_angle': start_angle,
            'end_angle': end_angle
        })

print(f"Parsed {len(edges)} entities from DXF")
