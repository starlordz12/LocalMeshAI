# Geometry Pipeline

This document describes how meshes and helper features move through LocalMeshAI, the
correctness guarantees, and the known limitations.

## Units

**Everything is in millimeters.** Blender's scene is configured so 1 Blender unit = 1 mm.
trimesh works in the mesh's native units, which we treat as mm. The UI labels all values
in mm.

## Stages

```
import → analyze → (repair?) → place helpers → preview → boolean apply → validate → export
```

### 1. Import

- Accepted: **STL** (required), **OBJ**, **PLY**, **3MF**. STEP is deferred (needs
  Blender/FreeCAD) and does not block import of the above.
- The original file is copied into `projects/<id>/sources/` and never modified.
- trimesh loads it; if the file contains a scene (multiple meshes), it is concatenated into
  a single mesh for analysis and display.
- A **display GLB** is exported to `_derived/` for the viewer.

### 2. Analyze

`mesh_analyzer.analyze()` reports:

| Metric | Source | Notes |
|---|---|---|
| Bounding box (mm) | `mesh.bounds` | min/max and size per axis |
| Volume (mm³) | `mesh.volume` | only meaningful if watertight |
| Surface area (mm²) | `mesh.area` | always available |
| Triangle count | `len(mesh.faces)` | |
| Watertight | `mesh.is_watertight` | manifold proxy |
| Winding consistent | `mesh.is_winding_consistent` | normals sane |
| Volume sign | `mesh.volume > 0` | inverted normals hint |

If the mesh is **not watertight**, the UI shows a warning. Volume is reported as
`null`/unknown rather than a misleading number.

### 3. Repair (explicit, opt-in)

`mesh_analyzer.repair()` performs **conservative** fixes only:

- merge duplicate vertices
- remove degenerate / duplicate faces
- fix winding & normals (`fix_normals`)
- fill small holes where trimesh can

It returns before/after triangle counts and watertight status. It never deletes large
regions. If repair cannot make the mesh watertight, it says so — it does not pretend.

### 4. Helper features (parametric, non-destructive)

Helpers are generated from parameters by `backend/services/helpers.py`. Each returns a
clean, watertight trimesh primitive positioned/rotated per the operation. Supported:

**Additive:** `box`, `cylinder`, `screw_boss` (rounded boss + optional pilot hole),
`mounting_tab` (tab + screw hole), `mounting_pad` (flat rectangular pad), `rib_gusset`,
`cable_guide`, `fairing` (aero wedge), `mounting_deck`, `glue_plate`.

**Subtractive:** `box_cutout`, `cylinder_hole`, `rectangular_slot`, `cable_channel`,
`vent_slot`, `screw_clearance_hole`, `pocket`.

The same builders are used for **preview** (frontend renders an equivalent three.js
geometry) and **authoritative export** (backend builds the real trimesh).

### 5. Boolean apply

`geometry_engine` dispatches to a backend:

1. **Blender** (`blender_engine`) if a Blender executable is found — robust boolean
   modifier with the MANIFOLD solver, the same approach used for thin-wall RC parts.
2. **trimesh + manifold3d** (`trimesh_engine`) otherwise — watertight CSG that works with
   no Blender installed.

Order of operations follows the operation tree (top to bottom, skipping `suppressed`).
Additive helpers union into the target; subtractive helpers difference from it; `glue_on`
helpers are **not** merged — they are kept as separate exportable bodies.

If a boolean fails (e.g. non-manifold inputs, open meshes, coplanar faces), the engine
returns the log and a readable reason. The operation tree is left unchanged.

### 6. Validate

Before any STL is written, a validation pass checks:

- watertight / manifold
- consistent winding
- non-zero volume
- triangle count and bbox delta vs. the input

Results are returned to the UI and printed to the status console.

### 7. Export

- **Final STL** — target mesh with all non-suppressed additive/subtractive helpers baked.
- **Helper STL** — a single helper exported on its own (glue-on pieces).
- **Project JSON** — the operation tree, so the export is fully reproducible.

3MF/OBJ export are optional niceties layered on the same trimesh export path.

## Glue-on contact surfaces

**MVP behavior:** glue-on parts use a **flat contact face**. The part is positioned where
the user places it; the contact is whatever flat face touches the target.

**TODO — conformal glue surfaces:** project the helper's contact face onto the target mesh
surface (raycast a grid, build a conforming skirt) so curved surfaces get a matching mating
face. This is intentionally deferred; it is the single biggest geometry upgrade after the
MVP. Tracked in [ROADMAP.md](ROADMAP.md) under Milestone 3+.

## Printability defaults

| Default | Value |
|---|---|
| Units | mm |
| Min wall thickness warning | 0.8 mm |
| Screw pilot hole | 2.2 mm |
| M3 clearance hole | 3.2 mm |
| Default fillet/chamfer | 0.5–1.0 mm where supported |
| Default helper thickness | 2–3 mm |

The analyzer warns (does not block) when a generated feature is thinner than the minimum
wall thickness.

## Known limitations

- No freehand sculpting. Annotations capture **intent**; geometry comes from parametric
  helpers. This is deliberate — see the README.
- Conformal glue surfaces are flat for now (above).
- Very large meshes (millions of triangles) will boolean slowly in the trimesh fallback;
  Blender handles them better.
- STEP/IGES require Blender or FreeCAD and are deferred.
