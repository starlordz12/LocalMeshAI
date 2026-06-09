"""API smoke tests covering the acceptance-test workflow end to end."""
import io

import trimesh
from fastapi.testclient import TestClient

import main
from services import geometry_engine

client = TestClient(main.app)


def _cube_stl_bytes(size=20.0) -> bytes:
    mesh = trimesh.creation.box(extents=(size, size, size))
    return mesh.export(file_type="stl")


def _new_project() -> dict:
    r = client.post("/api/project/new", json={"name": "Test"})
    assert r.status_code == 200
    return r.json()["project"]


def _import_cube(project_id: str) -> dict:
    files = {"file": ("cube.stl", io.BytesIO(_cube_stl_bytes()), "model/stl")}
    r = client.post("/api/import", data={"projectId": project_id}, files=files)
    assert r.status_code == 200, r.text
    return r.json()


def test_health_reports_engine():
    r = client.get("/api/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert "booleanEngine" in body["engine"]


def test_feature_catalog():
    r = client.get("/api/features")
    assert r.status_code == 200
    cat = r.json()["catalog"]
    assert "additive" in cat and "subtractive" in cat


def test_import_and_analyze_cube():
    project = _new_project()
    imported = _import_cube(project["id"])
    mesh = imported["mesh"]
    assert mesh["analysis"]["isWatertight"] is True
    assert mesh["analysis"]["triangleCount"] == 12
    assert mesh["displayGlb"].endswith(".glb")

    # The display GLB is fetchable.
    r = client.get(f"/api/project/{project['id']}/file/{mesh['displayGlb']}")
    assert r.status_code == 200
    assert len(r.content) > 0


def test_add_helper_and_export_helper_stl():
    project = _new_project()
    imported = _import_cube(project["id"])
    project = imported["project"]
    mesh_id = imported["mesh"]["id"]

    op = {
        "id": "op_pad",
        "type": "helper_feature",
        "name": "Mounting Pad",
        "mode": "glue_on",
        "feature": "mounting_pad",
        "targetMeshId": mesh_id,
        "positionMm": [0, 0, 12],
        "rotationDeg": [0, 0, 0],
        "scaleMm": [28, 14, 3],
        "parameters": {"holeCount": 2, "holeDiameterMm": 2.2, "holeSpacingMm": 20.0},
    }
    r = client.post("/api/operation/add-helper", json={"project": project, "operation": op})
    assert r.status_code == 200, r.text
    project = r.json()["project"]
    assert len(project["operations"]) == 1

    r = client.post("/api/export/helper-stl",
                    json={"project": project, "operationId": "op_pad", "format": "stl"})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["success"] is True
    assert body["file"].endswith(".stl")
    assert body["validation"]["isWatertight"] is True


def test_boolean_union_and_final_export():
    project = _new_project()
    imported = _import_cube(project["id"])
    project = imported["project"]
    mesh_id = imported["mesh"]["id"]

    # A block overlapping the top face (union) and a through hole (difference).
    project["operations"] = [
        {
            "id": "op_block", "type": "helper_feature", "name": "Block", "mode": "additive",
            "feature": "box", "targetMeshId": mesh_id,
            "positionMm": [0, 0, 12], "rotationDeg": [0, 0, 0], "scaleMm": [8, 8, 8],
            "parameters": {},
        },
        {
            "id": "op_hole", "type": "helper_feature", "name": "Hole", "mode": "subtractive",
            "feature": "cylinder_hole", "targetMeshId": mesh_id,
            "positionMm": [0, 0, 0], "rotationDeg": [0, 0, 0], "scaleMm": [4, 4, 40],
            "parameters": {"diameterMm": 4},
        },
    ]

    r = client.post("/api/operation/apply-boolean",
                    json={"project": project, "meshId": mesh_id})
    assert r.status_code == 200, r.text
    body = r.json()
    if not geometry_engine.boolean_supported():
        assert body["success"] is False
        return
    assert body["success"] is True, body["message"]
    assert body["after"]["triangleCount"] > 0

    r = client.post("/api/export/final-stl",
                    json={"project": project, "meshId": mesh_id, "format": "stl"})
    assert r.status_code == 200, r.text
    assert r.json()["success"] is True


def test_ai_plan_rule_based():
    r = client.post("/api/ai/plan", json={
        "prompt": "add a 25x15x3 mm camera mounting pad with two 2.2 mm pilot holes spaced 20 mm apart",
        "planner": "rule_based",
    })
    assert r.status_code == 200, r.text
    body = r.json()
    assert len(body["features"]) == 1
    feat = body["features"][0]
    assert feat["feature"] in ("mounting_pad", "mounting_deck")
    assert feat["scaleMm"] == [25, 15, 3]
    assert feat["parameters"]["holeCount"] == 2
    assert feat["parameters"]["holeSpacingMm"] == 20.0


def test_ai_plan_cut_hole_and_glue_on():
    r = client.post("/api/ai/plan", json={"prompt": "drill a 6 mm hole", "planner": "rule_based"})
    assert r.json()["features"][0]["feature"] == "cylinder_hole"

    r = client.post("/api/ai/plan", json={"prompt": "add a mounting tab as a glue-on piece"})
    feat = r.json()["features"][0]
    assert feat["feature"] == "mounting_tab"
    assert feat["mode"] == "glue_on"
