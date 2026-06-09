---
name: Geometry operation failure
about: A boolean / helper / export operation failed or produced bad geometry
title: "[Geometry] "
labels: geometry, bug
assignees: ''
---

## Operation that failed

- Type: [boolean union | boolean difference | helper generation | repair | export]
- Helper feature (if any): [box | cylinder | mounting_tab | cable_channel | ...]
- Mode: [additive | subtractive | glue_on]
- Engine: [Blender | trimesh/manifold3d]

## What happened

The error message from the status console, plus the backend log if you have it.

```
paste log here
```

## Inputs

- Target mesh format / triangle count:
- Watertight? [yes/no/unknown]
- Helper parameters (mm):
- Position / rotation (mm / deg):

## Expected result

What the geometry should have looked like.

## Reproducibility

- [ ] Happens every time
- [ ] Happens intermittently
- [ ] Only with this specific mesh (attached)

## Attachments

Attach the source STL and, if possible, the exported `project.json` so the operation tree
can be replayed.
