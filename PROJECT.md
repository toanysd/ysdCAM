# Project: ysdCAM

## Architecture
- **Research Module**: A markdown report documenting approaches to STEP boundary extraction and hole coordinate calculation.
- **Implementation Module**: A Python script/module that takes a STEP file, extracts 2D seamless boundaries (Polygons) without fragmentation, and calculates drill hole coordinates (e.g. for corners and arcs) maintaining 2mm clearance from walls.

## Milestones
| # | Name | Scope | Dependencies | Status |
|---|------|-------|-------------|--------|
| 1 | Research | Research existing open-source repos (OpenCASCADE, CadQuery, python-occ) related to boundary extraction and hole/pocket recognition. Generate a markdown report. | none | DONE |
| 2 | Implementation | Develop Python script to parse STEP files, extract seamless boundaries, calculate drill hole coordinates, and run against a mock STEP file. | none | IN_PROGRESS |

## Interface Contracts
### Research ↔ Implementation
- Research report will inform the best library and technique to use for the Implementation script.

## Code Layout
- `docs/research_report.md` - Generated markdown report.
- `src/step_processor.py` - Main implementation script.
- `tests/mock_data/` - Mock STEP files for testing.
