# User Workflow

Three end-to-end workflows LocalMeshAI is built to support. Each maps to acceptance tests
in the README.

## Workflow 1 — Glue-on mounting pad with screw holes

1. Start the app (`./start-dev.ps1`, or run backend + frontend separately).
2. **Import Model** → choose an STL.
3. The model renders in the viewport with mm dimensions and a bounding box.
4. Orbit/rotate to orient the part as you want it.
5. Toolbar → **Add Helper** → choose **Flat Mounting Pad**.
6. The pad appears in the scene and in the object tree. Drag the transform gizmo to place it
   on/near the mesh; fine-tune position/size in the **Inspector** (mm).
7. In the Inspector, set the mode to **glue-on** (or **additive**).
8. Add screw holes (pad parameters → hole diameter/spacing, or add `screw_clearance_hole`
   subtractive helpers).
9. Preview — the pad and holes render live.
10. Export:
    - **Export Selected Helper STL** → the pad as its own glue-on piece, **or**
    - **Run Geometry Operation** (boolean union) then **Export Final STL**.

## Workflow 2 — Annotated cooling vent cutout

1. **Import** an STL.
2. Toolbar → **Edit Pencil** mode. Circle the area that needs a vent.
3. In the annotation popover, set intent = **Cut/remove material** (vent/cutout) and type
   "make a rectangular cooling vent here".
4. The annotation appears in the object tree. Click **Convert to Helper** → it becomes an
   editable `vent_slot`/`box_cutout` helper placed at the stroke location.
5. Adjust dimensions/position in the Inspector.
6. **Run Geometry Operation** → backend boolean difference (Blender or trimesh/manifold3d).
7. **Export Final STL**.

## Workflow 3 — AI-planned camera mounting deck

1. **Import** an STL.
2. Open the **AI panel** (right side / bottom).
3. Prompt: *"Add a small aerodynamic camera mounting deck on the underside, 28 mm long,
   14 mm wide, 3 mm thick, with two 2.2 mm pilot holes 20 mm apart."*
4. Click **Generate Edit Plan**. The rule-based planner returns a structured, **editable**
   plan (no geometry is changed yet).
5. Review the dimensions in the plan preview.
6. Click **Create Helper Features From Plan** → the deck + holes become helper operations.
7. Adjust if needed, then export as a **glue-on piece** or **merge** into the main STL.

## Display & inspection tips

- **Display modes:** solid / wireframe / transparent / x-ray (Inspector or toolbar).
- **Reset View** re-frames the camera on the model.
- **Center on bed / Move to build plate** snap the part to the grid origin / Z=0.
- **Rotate X/Y/Z 90°** are one-click in the Inspector; free-rotation fields below them.
- The status console (bottom) logs every operation and any geometry warnings.

## Saving & reloading

- **Save Project** writes `project.json` (the operation tree) into the project workspace.
- Reopening the project restores the imported mesh and every helper exactly.
- The original source mesh is never modified — only exports bake geometry.
