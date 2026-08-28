import math
from src.plugins.ysd_flow.generate_cam_use_case import GenerateMoldCAMUseCase
from collections import Counter

uc = GenerateMoldCAMUseCase('data-sample/IRI-002D/IRI-002D(Q)_3D.step')
res = uc.execute()
back = [h for h in res['holes'] if 'back' in h.get('hole_type','')]
active = [h for h in back if h.get('is_active')]
violations = sum(
    1 for i, a in enumerate(active)
    for b in active[i+1:]
    if math.hypot(a['x']-b['x'], a['y']-b['y']) < 5.0 and abs(a['z']-b['z']) < 0.5
)

print(f'Total back: {len(back)} | Active: {len(active)} | Vi pham: {violations}')
print('Active by z:', Counter(round(h['z'],1) for h in active))
print('Active by type:', Counter(h['hole_type'].split('_')[-1] for h in active))
