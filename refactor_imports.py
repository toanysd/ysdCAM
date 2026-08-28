import os

replacements = {
    "src.infrastructure.cad_reader": "src.core_geometry.cad_reader",
    "src.infrastructure.dxf_reader": "src.core_geometry.dxf_reader",
    "src.infrastructure.dxf_writer": "src.post_processor.dxf_writer",
    "src.infrastructure.gcode_writer": "src.post_processor.gcode_writer",
    "src.domain.polygon_hole_strategy": "src.plugins.ysd_flow.polygon_hole_strategy",
    "src.domain.medial_axis_strategy": "src.plugins.ysd_flow.medial_axis_strategy",
    "src.domain.edge_traversal": "src.core_geometry.edge_traversal",
    "src.domain.geometric_heuristics": "src.core_geometry.geometric_heuristics",
    "src.domain.kinematic_clearance": "src.cam_engine.kinematic_clearance",
    "src.domain.tool_selection": "src.cam_engine.tool_selection",
    "src.domain.hole_feature_extractor": "src.plugins.ysd_flow.hole_feature_extractor",
    "src.application.generate_cam_use_case": "src.plugins.ysd_flow.generate_cam_use_case",
    "src.application.generate_drill_cam_use_case": "src.plugins.ysd_flow.generate_drill_cam_use_case",
    "src.application.hole_clustering": "src.plugins.ysd_flow.hole_clustering",
}

for root, dirs, files in os.walk('src'):
    for file in files:
        if file.endswith('.py'):
            filepath = os.path.join(root, file)
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
            original = content
            for old, new in replacements.items():
                content = content.replace(old, new)
            if content != original:
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(content)
                print(f"Updated {filepath}")
