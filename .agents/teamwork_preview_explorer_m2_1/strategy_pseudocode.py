import cadquery as cq
from shapely.geometry import Polygon

def process_step_file(filepath: str, clearance: float = 2.0):
    # 1. Load the STEP file
    model = cq.importers.importStep(filepath)
    
    # 2. Identify target faces (e.g., pocket bottoms facing up)
    # This gets all planar faces with normal vector pointing in +Z
    faces = model.faces(">Z").vals()
    
    drill_coordinates = []
    
    for face in faces:
        # 3. Extract continuous boundaries
        outer_wire = face.outerWire()
        
        # Extract ordered vertices from the continuous wire
        # We can extract vertices to build a polygon
        vertices = []
        for edge in outer_wire.Edges():
            # edge.startPoint() returns a Vector
            pt = edge.startPoint()
            vertices.append((pt.x, pt.y))
            
        if not vertices:
            continue
            
        # 4. Calculate Clearance (using Shapely for robust 2D offset)
        poly = Polygon(vertices)
        
        # Inward offset by clearance (e.g., 2mm)
        # join_style=2 (mitre) or 1 (round) depending on CAM toolpath needs
        inset_poly = poly.buffer(-clearance, join_style=1)
        
        if inset_poly.is_empty:
            continue
            
        # Extract the drill hole coordinates from the inset boundary corners
        # If the tool is a drill, corners of the inset polygon are valid safe positions
        if inset_poly.geom_type == 'Polygon':
            safe_coords = list(inset_poly.exterior.coords)
            drill_coordinates.extend(safe_coords)
        elif inset_poly.geom_type == 'MultiPolygon':
            for p in inset_poly.geoms:
                drill_coordinates.extend(list(p.exterior.coords))
                
    return drill_coordinates
