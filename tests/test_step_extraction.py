import os
import sys
import tempfile
import pytest
import cadquery as cq

# Ensure the project root is in the path to import cad_reader
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Attempt to import cad_reader
try:
    import infrastructure.cad_reader as cad_reader
except ImportError:
    src_path = os.path.join(project_root, 'src', 'infrastructure')
    if src_path not in sys.path:
        sys.path.insert(0, src_path)
    import cad_reader

def test_boundary_extraction_and_clearance():
    """
    Test that cad_reader can extract the bottom face boundaries as a closed continuous loop
    and verify that Z-raycast clustering ensures a 2mm clearance from walls.
    """
    # 1. Create a mock 3D model: A 50x50x20 box with a tapered pocket
    # The taper provides the draft angle requested.
    model = (
        cq.Workplane("XY")
        .box(50, 50, 20)
        .faces(">Z")
        .workplane()
        .rect(30, 30)
        .extrude(-10, taper=10, combine='cut')
    )
    
    with tempfile.NamedTemporaryFile(suffix=".step", delete=False) as tmp:
        temp_step_path = tmp.name

    try:
        # Export the model to a temporary STEP file
        cq.exporters.export(model, temp_step_path)
        
        # --- 2. Test Boundary Extraction ---
        # Using a TDD hypothetical API for cad_reader.
        boundaries = cad_reader.extract_bottom_boundaries(temp_step_path)
        
        # Verify we get at least one boundary
        assert boundaries is not None, "Boundary extraction returned None"
        assert len(boundaries) > 0, "No boundaries extracted"
        
        # Verify the extracted boundary forms a single closed, continuous loop 
        # (1 wire/polygon per feature) instead of fragmented edges.
        assert len(boundaries) == 1, f"Expected 1 continuous closed loop, got {len(boundaries)} fragments."
        
        # Check if the boundary loop is closed
        if hasattr(boundaries[0], 'is_closed'):
            assert boundaries[0].is_closed(), "The boundary loop is not closed."
        elif hasattr(boundaries[0], 'isClosed'):
            assert boundaries[0].isClosed(), "The boundary loop is not closed."
            
        # --- 3. Test Clearance Calculation ---
        # Assuming cad_reader has a function that calculates valid hole locations
        # with a specified clearance (Z-raycast and clustering).
        points = cad_reader.calculate_hole_clearance(temp_step_path, clearance=2.0)
        
        # Verify that points are returned
        assert points is not None, "Clearance calculation returned None"
        assert len(points) > 0, "No clearance points were generated."
        
        # Verify the distance of these points to the nearest wall is >= 2.0mm
        if hasattr(cad_reader, 'distance_to_nearest_wall'):
            for pt in points:
                dist = cad_reader.distance_to_nearest_wall(temp_step_path, pt)
                assert dist >= 2.0, f"Point {pt} is too close to a wall (distance: {dist}mm, expected >= 2.0mm)"

    finally:
        # Cleanup the temporary STEP file
        if os.path.exists(temp_step_path):
            os.remove(temp_step_path)

if __name__ == "__main__":
    pytest.main([__file__])
