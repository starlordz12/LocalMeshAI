// Build three.js preview geometry for a helper operation. These approximate the backend's
// authoritative shapes (services/helpers.py) closely enough for live editing; the exported
// STL is always rebuilt by the backend. The whole scene is Z-up (CAD/mm convention), so
// cylinders are aligned to Z here.

import * as THREE from "three";
import type { Operation, Vec3 } from "../types/operations";

const SECTIONS = 48;

function numParam(op: Operation, key: string, fallback: number): number {
  const v = op.parameters?.[key];
  return typeof v === "number" && !Number.isNaN(v) ? v : fallback;
}

function centerGeometry(geo: THREE.BufferGeometry): THREE.BufferGeometry {
  geo.computeBoundingBox();
  const bb = geo.boundingBox!;
  const cx = (bb.min.x + bb.max.x) / 2;
  const cy = (bb.min.y + bb.max.y) / 2;
  const cz = (bb.min.z + bb.max.z) / 2;
  geo.translate(-cx, -cy, -cz);
  return geo;
}

/** Cylinder aligned to the Z axis, centered. */
function zCylinder(radius: number, height: number): THREE.BufferGeometry {
  const geo = new THREE.CylinderGeometry(radius, radius, height, SECTIONS);
  geo.rotateX(Math.PI / 2); // Y-axis -> Z-axis
  return geo;
}

/** Cylinder aligned to the X axis (for channels / guides), centered. */
function xCylinder(radius: number, length: number): THREE.BufferGeometry {
  const geo = new THREE.CylinderGeometry(radius, radius, length, SECTIONS);
  geo.rotateZ(Math.PI / 2); // Y-axis -> X-axis
  return geo;
}

/** Triangular prism via extrude. ramp=true rises front->back (fairing). */
function trianglePrism(length: number, height: number, width: number, ramp: boolean): THREE.BufferGeometry {
  const shape = new THREE.Shape();
  shape.moveTo(0, 0);
  shape.lineTo(length, 0);
  shape.lineTo(ramp ? length : 0, height);
  shape.lineTo(0, 0);
  const geo = new THREE.ExtrudeGeometry(shape, { depth: width, bevelEnabled: false });
  return centerGeometry(geo);
}

export function buildHelperGeometry(op: Operation): THREE.BufferGeometry {
  const [sx, sy, sz] = op.scaleMm;
  const f = op.feature;

  switch (f) {
    case "box":
    case "box_cutout":
    case "rectangular_slot":
    case "vent_slot":
    case "pocket":
      return new THREE.BoxGeometry(sx, sy, sz);

    case "mounting_pad":
    case "mounting_deck":
    case "glue_plate":
      return new THREE.BoxGeometry(sx, sy, sz > 0 ? sz : 2.5);

    case "mounting_tab":
      return new THREE.BoxGeometry(sx > 0 ? sx : 18, sy > 0 ? sy : 10, sz > 0 ? sz : 2.5);

    case "cylinder":
    case "cylinder_hole": {
      const r = numParam(op, "radiusMm", op.parameters.diameterMm ? numParam(op, "diameterMm", sx) / 2 : sx / 2);
      const h = numParam(op, "heightMm", sz);
      return zCylinder(Math.max(r, 0.01), Math.max(h, 0.01));
    }

    case "screw_clearance_hole": {
      const d = numParam(op, "holeDiameterMm", 3.2);
      const h = numParam(op, "heightMm", sz > 0 ? sz : 10);
      return zCylinder(d / 2, h);
    }

    case "screw_boss": {
      const od = numParam(op, "outerDiameterMm", sx > 0 ? sx : 6);
      const h = numParam(op, "heightMm", sz > 0 ? sz : 6);
      return zCylinder(od / 2, h);
    }

    case "cable_channel": {
      const d = numParam(op, "cableDiameterMm", numParam(op, "diameterMm", Math.min(sy, sz) || 4));
      const len = sx > 0 ? sx : 30;
      return xCylinder(d / 2, len);
    }

    case "cable_guide": {
      const od = numParam(op, "outerDiameterMm", Math.max(sy, sz) || 8);
      const len = sx > 0 ? sx : 12;
      return xCylinder(od / 2, len);
    }

    case "rib_gusset":
      return trianglePrism(sx > 0 ? sx : 15, sy > 0 ? sy : 15, sz > 0 ? sz : 3, false);

    case "fairing":
      return trianglePrism(sx > 0 ? sx : 30, sz > 0 ? sz : 8, sy > 0 ? sy : 16, true);

    default:
      return new THREE.BoxGeometry(sx || 20, sy || 10, sz || 3);
  }
}

export interface HoleMarker {
  position: Vec3;
  radius: number;
  depth: number;
}

/** Hole indicators for pads/tabs/bosses, so the preview shows where holes will be cut. */
export function holeMarkers(op: Operation): HoleMarker[] {
  const [sx, , sz] = op.scaleMm;
  const f = op.feature;
  if (f === "mounting_pad" || f === "mounting_deck" || f === "glue_plate") {
    const count = numParam(op, "holeCount", 0);
    if (count <= 0) return [];
    const dia = numParam(op, "holeDiameterMm", 2.2);
    const spacing = numParam(op, "holeSpacingMm", 20);
    const thickness = sz > 0 ? sz : 2.5;
    if (count === 1) return [{ position: [0, 0, 0], radius: dia / 2, depth: thickness }];
    const start = (-spacing * (count - 1)) / 2;
    return Array.from({ length: count }, (_, i) => ({
      position: [start + i * spacing, 0, 0] as Vec3,
      radius: dia / 2,
      depth: thickness,
    }));
  }
  if (f === "mounting_tab") {
    const dia = numParam(op, "holeDiameterMm", 3.2);
    const hx = sx * 0.5 - 5;
    return [{ position: [hx, 0, 0], radius: dia / 2, depth: sz > 0 ? sz : 2.5 }];
  }
  return [];
}
