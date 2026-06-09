// The 3D viewport: Z-up scene, orbit/pan/zoom, build-plate grid, axes gizmo, the imported
// mesh (display GLB), live helper previews with a transform gizmo, bounding box + mm
// dimensions, display modes, and an optional baked-result preview.

import { Suspense, useEffect, useMemo, useRef } from "react";
import { Canvas, useThree } from "@react-three/fiber";
import type { ThreeEvent } from "@react-three/fiber";
import { GizmoHelper, GizmoViewport, Grid, Html, OrbitControls, useGLTF } from "@react-three/drei";
import * as THREE from "three";

import { useStore } from "../store/projectStore";
import { fileUrl } from "../api/client";
import type { MeshInfo } from "../types/project";
import { BUILD_PLATE_MM, COLORS } from "../geometry/sceneState";
import { degToRadVec } from "../geometry/transformUtils";
import { useStlGeometry } from "../geometry/loaders";
import { picker } from "../geometry/picker";
import HelperMesh from "./HelperMesh";

function SceneSetup() {
  const { camera, gl, controls } = useThree();
  const resetNonce = useStore((s) => s.viewResetNonce);
  useEffect(() => {
    camera.up.set(0, 0, 1); // Z-up world (CAD/mm convention)
    camera.position.set(140, -200, 150);
    camera.lookAt(0, 0, 0);
    gl.setClearColor("#11151c");
    const c = controls as unknown as { target?: THREE.Vector3; update?: () => void } | null;
    if (c?.target) {
      c.target.set(0, 0, 0);
      c.update?.();
    }
  }, [camera, gl, controls, resetNonce]);
  return null;
}

/** Registers the raycast picker so the annotation layer can hit-test the base mesh. */
function PickerBridge({ targetRef }: { targetRef: React.MutableRefObject<THREE.Object3D | null> }) {
  const { camera, scene } = useThree();
  const raycaster = useMemo(() => new THREE.Raycaster(), []);
  useEffect(() => {
    picker.pick = (ndcX, ndcY) => {
      raycaster.setFromCamera(new THREE.Vector2(ndcX, ndcY), camera);
      const target = targetRef.current;
      const objects = target ? [target] : scene.children;
      const hits = raycaster.intersectObjects(objects, true);
      if (!hits.length) return null;
      const p = hits[0].point;
      return [round(p.x), round(p.y), round(p.z)];
    };
    return () => {
      picker.pick = undefined;
    };
  }, [camera, scene, raycaster, targetRef]);
  return null;
}

const round = (v: number) => Math.round(v * 100) / 100;

function BaseMesh({ mesh, targetRef }: { mesh: MeshInfo; targetRef: React.MutableRefObject<THREE.Object3D | null> }) {
  const project = useStore((s) => s.project)!;
  const displayMode = useStore((s) => s.displayMode);
  const showBounds = useStore((s) => s.showBounds);
  const selectedId = useStore((s) => s.selectedId);
  const select = useStore((s) => s.select);

  const url = mesh.displayGlb ? fileUrl(project.id, mesh.displayGlb) : "";
  const gltf = useGLTF(url);

  const scene = useMemo(() => {
    const clone = gltf.scene.clone(true);
    const selected = selectedId === mesh.id;
    clone.traverse((o) => {
      const m = o as THREE.Mesh;
      if (m.isMesh) {
        m.material = new THREE.MeshStandardMaterial({
          color: selected ? COLORS.baseMeshSelected : COLORS.baseMesh,
          metalness: 0.1,
          roughness: 0.8,
          wireframe: displayMode === "wireframe",
          transparent: displayMode === "transparent" || displayMode === "xray",
          opacity: displayMode === "xray" ? 0.35 : displayMode === "transparent" ? 0.6 : 1,
          depthWrite: displayMode !== "xray",
          side: THREE.DoubleSide,
        });
        m.castShadow = false;
      }
    });
    return clone;
  }, [gltf, displayMode, selectedId, mesh.id]);

  const bbox = mesh.analysis?.boundingBox;
  const groupRef = useRef<THREE.Group>(null);
  useEffect(() => {
    targetRef.current = groupRef.current;
  });

  return (
    <group ref={groupRef} position={mesh.positionMm} rotation={degToRadVec(mesh.rotationDeg)}>
      <primitive
        object={scene}
        onClick={(e: ThreeEvent<MouseEvent>) => {
          e.stopPropagation();
          select(mesh.id);
        }}
      />
      {showBounds && bbox && <BoundsBox bbox={bbox} />}
    </group>
  );
}

function BoundsBox({ bbox }: { bbox: { min: [number, number, number]; max: [number, number, number]; size: [number, number, number] } }) {
  const center: [number, number, number] = [
    (bbox.min[0] + bbox.max[0]) / 2,
    (bbox.min[1] + bbox.max[1]) / 2,
    (bbox.min[2] + bbox.max[2]) / 2,
  ];
  const geo = useMemo(() => {
    const box = new THREE.BoxGeometry(bbox.size[0], bbox.size[1], bbox.size[2]);
    return new THREE.EdgesGeometry(box);
  }, [bbox.size[0], bbox.size[1], bbox.size[2]]);

  const label = (text: string, pos: [number, number, number]) => (
    <Html position={pos} center style={{ pointerEvents: "none" }}>
      <div className="dim-label">{text}</div>
    </Html>
  );

  return (
    <group position={center}>
      <lineSegments geometry={geo}>
        <lineBasicMaterial color="#6cc6ff" />
      </lineSegments>
      {label(`${bbox.size[0].toFixed(1)} mm`, [0, -bbox.size[1] / 2 - 2, bbox.size[2] / 2])}
      {label(`${bbox.size[1].toFixed(1)} mm`, [bbox.size[0] / 2 + 2, 0, bbox.size[2] / 2])}
      {label(`${bbox.size[2].toFixed(1)} mm`, [bbox.size[0] / 2 + 2, -bbox.size[1] / 2 - 2, 0])}
    </group>
  );
}

function ResultPreview() {
  const project = useStore((s) => s.project);
  const url = useStore((s) => s.resultPreviewUrl);
  const show = useStore((s) => s.showResult);
  const geometry = useStlGeometry(show && url ? url : null);
  if (!project || !geometry) return null;
  return (
    <mesh geometry={geometry}>
      <meshStandardMaterial color={COLORS.resultPreview} metalness={0.1} roughness={0.6} transparent opacity={0.85} />
    </mesh>
  );
}

function Helpers() {
  const project = useStore((s) => s.project);
  const selectedId = useStore((s) => s.selectedId);
  const hiddenIds = useStore((s) => s.hiddenIds);
  const gizmoMode = useStore((s) => s.gizmoMode);
  const displayMode = useStore((s) => s.displayMode);
  const select = useStore((s) => s.select);
  const updateOperation = useStore((s) => s.updateOperation);
  if (!project) return null;
  return (
    <>
      {project.operations
        .filter((op) => op.type === "helper_feature" && !hiddenIds.includes(op.id))
        .map((op) => (
          <HelperMesh
            key={op.id}
            op={op}
            selected={selectedId === op.id}
            gizmoMode={gizmoMode}
            displayMode={displayMode}
            onSelect={select}
            onCommit={updateOperation}
          />
        ))}
    </>
  );
}

export default function Viewer3D() {
  const project = useStore((s) => s.project);
  const select = useStore((s) => s.select);
  const targetRef = useRef<THREE.Object3D | null>(null);
  const mesh = project?.meshes[0] ?? null;

  return (
    <Canvas
      dpr={[1, 2]}
      gl={{ antialias: true }}
      camera={{ fov: 45, near: 0.1, far: 8000, position: [140, -200, 150] }}
      onPointerMissed={() => select(null)}
    >
      <SceneSetup />
      <PickerBridge targetRef={targetRef} />
      <ambientLight intensity={0.6} />
      <directionalLight position={[200, -150, 300]} intensity={1.1} />
      <directionalLight position={[-200, 200, 150]} intensity={0.4} />

      {/* Build plate on the XY plane at Z=0 */}
      <Grid
        rotation={[Math.PI / 2, 0, 0]}
        args={[BUILD_PLATE_MM, BUILD_PLATE_MM]}
        cellSize={8}
        cellThickness={0.6}
        cellColor={COLORS.buildPlate}
        sectionSize={40}
        sectionThickness={1.2}
        sectionColor={COLORS.buildPlateAxis}
        infiniteGrid
        fadeDistance={1200}
        fadeStrength={1.5}
      />
      {/* Origin marker */}
      <mesh position={[0, 0, 0]}>
        <sphereGeometry args={[1.2, 16, 16]} />
        <meshBasicMaterial color="#ffd54f" />
      </mesh>

      <Suspense fallback={null}>
        {mesh && mesh.displayGlb && <BaseMesh mesh={mesh} targetRef={targetRef} />}
        <ResultPreview />
      </Suspense>

      <Helpers />

      <OrbitControls makeDefault enableDamping dampingFactor={0.1} />
      <GizmoHelper alignment="bottom-right" margin={[72, 72]}>
        <GizmoViewport axisColors={["#e0533d", "#4caf50", "#3d8be0"]} labelColor="white" />
      </GizmoHelper>
    </Canvas>
  );
}
