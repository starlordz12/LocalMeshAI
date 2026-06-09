// Mesh loading helpers for the viewer.
// - GLB display meshes are loaded with drei's useGLTF in Viewer3D.
// - This module loads STL results (e.g. the baked boolean preview) via three's STLLoader.

import { useEffect, useState } from "react";
import * as THREE from "three";
import { STLLoader } from "three/examples/jsm/loaders/STLLoader.js";

/** Load an STL URL into a BufferGeometry, recomputing normals. Returns null while loading. */
export function useStlGeometry(url: string | null): THREE.BufferGeometry | null {
  const [geometry, setGeometry] = useState<THREE.BufferGeometry | null>(null);

  useEffect(() => {
    if (!url) {
      setGeometry(null);
      return;
    }
    let cancelled = false;
    const loader = new STLLoader();
    loader.load(
      url,
      (geo) => {
        if (cancelled) return;
        geo.computeVertexNormals();
        setGeometry(geo);
      },
      undefined,
      () => !cancelled && setGeometry(null)
    );
    return () => {
      cancelled = true;
    };
  }, [url]);

  return geometry;
}
