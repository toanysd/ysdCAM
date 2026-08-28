from src.plugins.ysd_flow.generate_cam_use_case import GenerateMoldCAMUseCase
import math
from collections import Counter

uc = GenerateMoldCAMUseCase('data-sample/IRI-002D/IRI-002D(Q)_3D.step')
res = uc.execute()
back = [h for h in res['holes'] if 'back' in h.get('hole_type','')]
active = [h for h in back if h.get('is_active', True)]

# Kiểm tra lỗ chồng: tìm cặp gần < 5mm
violations = 0
for i, a in enumerate(active):
    for b in active[i+1:]:
        d = math.hypot(a['x']-b['x'], a['y']-b['y'])
        if d < 5.0 and abs(a['z']-b['z']) < 0.5:
            violations += 1
            if violations <= 5:
                print(f'CHONG: ({a["x"]:.1f},{a["y"]:.1f},z={a["z"]:.1f}) vs ({b["x"]:.1f},{b["y"]:.1f},z={b["z"]:.1f}) dist={d:.2f}mm')

print(f'active: {len(active)} | vi pham clearance: {violations}')
print('by z:', Counter(round(h['z'],1) for h in active))
print('by type:', Counter(h['hole_type'] for h in active))
