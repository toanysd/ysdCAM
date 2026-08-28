# Handoff: STEP Boundary Extraction and Hole Coordinate Logic

## Observation
1. **Requirements**: `PROJECT.md` and `ORIGINAL_REQUEST.md` define the goal of developing a Python script to parse a STEP file, extract 2D seamless boundaries (Polygons) without fragmentation, and calculate drill hole coordinates (for corners and arcs) maintaining a 2mm wall clearance.
2. **Library**: `docs/research_report.md` establishes that **CadQuery / OCP** is the recommended tool because it utilizes B-Rep (Boundary Representation), avoiding the severe fragmentation seen in mesh-based approaches (like STL processing).
3. **Healing Fragments**: The research report explicitly highlights `ShapeUpgrade_UnifySameDomain` (available via CadQuery's underlying OCP layer) as the method to merge fragmented collinear edges and co-radial arcs.
4. **API Constraints**: The environment uses CadQuery, which exposes `.offset2D()`, `.outerWire()`, `.Vertices()`, `.Edges()`, and geometric queries like `.geomType() == 'CIRCLE'` and `.arcCenter()`.

## Logic Chain
1. **De-fragmentation Strategy**:
   - Even with B-Rep, poorly exported STEP files can split straight lines into multiple segments. 
   - By running `OCP.ShapeUpgrade.ShapeUpgrade_UnifySameDomain(face.wrapped, True, True, True)` on the target planar face *before* extracting the boundaries, we force the topological engine to merge any adjacent edges that share the same underlying geometry. This guarantees the "seamless boundaries without fragmentation" requirement.
2. **2mm Clearance Geometry**:
   - To maintain a strict 2mm wall clearance, we must find the locus of points exactly 2mm inward from the outer boundary. 
   - In CadQuery, applying `wire.offset2D(-2.0, kind='intersection')` yields a new boundary wire that is geometrically inset by 2mm. 
3. **Corner Hole Coordinate Calculation**:
   - For internal corners, the drill hole center must maintain the 2mm clearance from both intersecting walls. 
   - Mathematically, if we inset a polygon by $R=2\text{mm}$, the distance from an original vertex to the corresponding inset vertex along the angle bisector is exactly $\frac{2.0}{\sin(\theta/2)}$. This inset vertex is the precise geometric center for a 2mm radius drill hole that is tangent to both original walls.
   - Therefore, the coordinates for the corner drill holes can simply be extracted by iterating over the `Vertices()` of the **offset** wire.
4. **Arc Hole Coordinate Calculation**:
   - The original boundary may contain intentional circular features (arcs/holes) that require drilling.
   - To locate these, we iterate through the `Edges()` of the **original** unified wire. If an edge's `.geomType() == 'CIRCLE'`, we call `.arcCenter()` to get the exact coordinate for the drill.

## Caveats
- **Self-Intersections in Offset**: If a pocket or feature is narrower than 4mm (2mm offset from both sides), the 2mm inset offset will collapse or self-intersect, and CadQuery's `.offset2D()` might return an empty list or throw an error. The implementer must catch this and gracefully skip areas where a 2mm clearance drill cannot fit.
- **Dogbone Relief Intent**: Standard "maintaining 2mm clearance" places the edge of the drill perfectly tangent to the walls, leaving a tiny sliver of material in the absolute sharp corner. If the user strictly meant "corner overcut / dogbone" (to allow a mating rectangular part to fit), the drill coordinate would need to be pushed slightly further into the corner. However, based on the wording "maintaining 2mm clearance", placing the center at the offset vertex is mathematically exact.

## Conclusion
The implementation script (`src/step_processor.py`) should follow this execution flow:
1. **Load**: `model = cq.importers.importStep("file.step")`
2. **Select Face**: Isolate the target 2D projection or pocket bottom face (e.g., `model.faces("<Z")`).
3. **Heal**: Apply `OCP.ShapeUpgrade.ShapeUpgrade_UnifySameDomain` to the face.
4. **Extract**: Call `outer_wire = face.outerWire()` and `inner_wires = face.innerWires()`.
5. **Calculate Arcs**: Iterate `outer_wire.Edges()`; if it's a circle, save its `.arcCenter()`.
6. **Calculate Corners**: Call `offset_wire = outer_wire.offset2D(-2.0)[0]`. Iterate through `offset_wire.Vertices()` and save their `(X, Y)` coordinates as the corner drill points.

## Verification Method
1. Create `src/step_processor.py` applying this logic.
2. Create a mock rectangular pocket in CadQuery (e.g., 100x100 mm) with one inner hole.
3. Run the script. If the original corners were at `(0,0)`, `(100,0)`, etc., the extracted corner hole coordinates should strictly be `(2,2)`, `(98,2)`, etc., and the inner hole center should match exactly.
