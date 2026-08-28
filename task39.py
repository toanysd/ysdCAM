import math
from collections import Counter
from src.plugins.ysd_flow.generate_cam_use_case import GenerateMoldCAMUseCase

uc = GenerateMoldCAMUseCase('data-sample/IRI-002D/IRI-002D(Q)_3D.step')
res = uc.execute()
vh = res['vacuum_holes']
violations = sum(
    1 for i, a in enumerate(vh)
    for b in vh[i+1:]
    if abs(a['actual_z'] - b['actual_z']) < 0.1 and (a['x'] - b['x'])**2 + (a['y'] - b['y'])**2 < 9
)

print('vacuum count:', len(vh))
print('by z:', Counter(round(h['actual_z'], 1) for h in vh))
print('violations (same-Z, dist<3mm):', violations)
