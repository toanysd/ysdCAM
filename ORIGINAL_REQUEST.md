# Original User Request

## Initial Request — 2026-06-01T09:55:11Z

# Teamwork Project Prompt

> Status: Launched
> Goal: Craft prompt → get user approval → delegate to teamwork_preview

Xử lý lỗi đọc file 3D STEP và thuật toán tính toán lỗ khoan (ysdCAM). Mục tiêu là đọc file STEP, trích xuất đường biên 2D một cách liền mạch, không bị băm nhỏ, sau đó dùng đường biên này để tính toán tọa độ lỗ chuẩn xác. Đồng thời, nghiên cứu các mã nguồn mở (repo) liên quan để học hỏi cách xử lý tối ưu.

Working directory: g:\AntiGravity\apps\ysdCAM
Integrity mode: development

## Requirements

### R1. Research & Repo Analysis
Research existing open-source repositories and Python libraries (e.g. OpenCASCADE, CadQuery, python-occ) related to boundary extraction and hole/pocket recognition from STEP files. Provide a brief summary of techniques that can prevent edge fragmentation.

### R2. STEP File Boundary Extraction
Develop a Python script/module that takes a 3D STEP file as input, reads the top-down 2D projection or pocket bottom faces, and extracts seamless continuous boundaries (Polygons) without fragmentation or noise. 

### R3. Hole Coordinate Calculation
Using the extracted continuous boundaries, implement a robust algorithm to calculate drill hole coordinates (e.g. for corners and arcs) following standard CAM rules (e.g., maintaining 2mm clearance from walls).

## Acceptance Criteria

### Research
- [ ] A markdown report is generated containing at least 2 relevant open-source repos or libraries, with a summary of their approach to edge smoothing/extraction.

### Extraction & Calculation
- [ ] A standalone Python script is created that accepts a STEP file path and outputs a clean set of coordinates for drill holes.
- [ ] The script must successfully run and parse a test STEP file (or generate a mock one if unavailable) without crashing.
- [ ] The extracted boundary data structure must consist of merged, continuous geometric entities rather than fragmented line segments.
