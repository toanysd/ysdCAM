# Research Report: STEP File Boundary Extraction and Hole/Pocket Recognition

## 1. Overview
This report investigates existing open-source Python libraries for processing 3D STEP files, focusing on boundary extraction, hole/pocket recognition, and techniques to prevent edge fragmentation. Extracting seamless, continuous boundaries (Polygons) is a critical prerequisite for accurate CAM algorithms, such as calculating standard clearance coordinates for drill holes.

## 2. Relevant Open-Source Libraries

### 2.1. OpenCASCADE Technology (OCCT) / PythonOCC
**Repository:** [pythonocc-core](https://github.com/tpaviot/pythonocc-core)
**Description:** PythonOCC is a Python wrapper for the powerful C++ OpenCASCADE Technology (OCCT) library, which is the industry standard open-source 3D modeling kernel.

**Approach to Boundary Extraction & Fragmentation Prevention:**
- **Topological Data Structure (B-Rep):** OCCT uses Boundary Representation (B-Rep). A model is hierarchically composed of Solids, Shells, Faces, Wires, Edges, and Vertices. Instead of parsing isolated lines or segments, you can extract `TopoDS_Wire` objects directly from a target `TopoDS_Face` (e.g., the bottom of a pocket).
- **Topology Exploration:** Using `TopExp_Explorer`, developers can filter exclusively for loops (wires) on specific faces. Because the STEP file inherently defines which edges belong to which wire, topological extraction natively guarantees continuous loops rather than scattered line segments.
- **Healing and Unification (Edge Smoothing):** For poorly exported STEP files that suffer from fragmented edges (e.g., a single straight line broken into three collinear segments), OCCT provides `ShapeUpgrade_UnifySameDomain`. This class identifies adjacent edges that share the same underlying geometry (same line or curve) and unifies them into a single continuous `TopoDS_Edge`.
- **Wire Assembly:** The `BRepBuilderAPI_MakeWire` class can take a list of disorganized edges and logically string them together into a continuous loop by matching the tolerances of their vertices.

### 2.2. CadQuery / OCP
**Repository:** [cadquery](https://github.com/CadQuery/cadquery)
**Description:** CadQuery is a high-level, fluent, Pythonic API built on top of OCP (an auto-generated OCCT wrapper). It is designed to make parametric 3D modeling and analysis significantly more accessible than raw PythonOCC.

**Approach to Boundary Extraction & Fragmentation Prevention:**
- **Fluent Face/Edge Selection:** CadQuery allows querying geometric features easily. For example, `model.faces("<Z")` effortlessly selects the bottom face of a pocket. From this face, you can extract the outer boundary using `face.outerWire()`.
- **Built-in Assembly and Tolerances:** Similar to OCCT but more automated, CadQuery's `Wire.assembleEdges()` allows passing a list of potentially disconnected or fragmented edges. It uses a tolerance-based endpoint matching algorithm to chain them together into a continuous, ordered wire sequence.
- **Discretization and Smoothing:** Once a continuous wire is obtained, CadQuery objects can be natively sampled or discretized into 2D polygons (e.g., for offset calculation or standard CAM algorithms). Because the extraction starts from continuous parametric curves (like circles, ellipses, and BSplines), the resulting boundaries avoid the noise and jagged fragmentation seen in mesh-based (STL) processing.

### 2.3. Trimesh (For Comparison)
**Repository:** [trimesh](https://github.com/mikedh/trimesh)
**Description:** While primarily a mesh-based (STL, OBJ) library, it has some STEP import capabilities.
**Note on Fragmentation:** Trimesh converts analytical STEP geometry into discrete meshes. Attempting to extract boundaries from meshes often leads to heavy edge fragmentation (polygonal noise) and requires significant post-processing (Douglas-Peucker simplification, RANSAC). **Conclusion:** For precise CAM boundary extraction, B-Rep libraries like OpenCASCADE/CadQuery are vastly superior to mesh-based libraries.

## 3. Recommended Approach for Implementation
To fulfill the requirements of extracting seamless boundaries and calculating drill hole coordinates with standard wall clearance (e.g., 2mm), we recommend using **CadQuery (or its underlying OCP bindings)**.

1. **Extraction:** Load the STEP file and isolate the target 2D projection or pocket bottom face.
2. **De-fragmentation:** Extract the `Wire` from the face. If multiple edges exist, utilize `ShapeUpgrade_UnifySameDomain` or wire assembly techniques to merge collinear segments and continuous arcs.
3. **Offsetting / Clearance:** Use the `Wire` to generate a 2D offset (inset by 2mm). The resulting offset polygon will represent the safe zones.
4. **Hole Recognition:** Detect `Geom_Circle` or `Geom_CylindricalSurface` entities via the B-Rep hierarchy to identify pre-existing holes and distinguish them from generic boundary corners.

This methodology relies entirely on analytical geometry rather than mesh approximations, completely eliminating arbitrary edge fragmentation.
