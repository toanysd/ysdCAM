import cadquery as cq

# generate a mock STEP file
mock_step = "mock.step"
box = cq.Workplane("XY").box(10, 10, 10).faces(">Z").workplane().hole(2)
cq.exporters.export(box, mock_step)

print("Mock STEP created.")

# read mock STEP
model = cq.importers.importStep(mock_step)
print("Model loaded.")

# get bottom faces (or top face)
# Here we want to extract the boundary
top_face = model.faces(">Z").val()
print("Top face:", top_face)

wires = top_face.Wires()
print("Wires:", wires)

# Calculate offset
for w in wires:
    # We want an offset
    try:
        offset_wires = w.offset2D(2.0, "arc")
        print("Offset wires:", offset_wires)
    except AttributeError:
        print("offset2D not on Wire, let's try something else.")
