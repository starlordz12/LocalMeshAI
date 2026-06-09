// Project, mesh, and API response types mirroring the backend models.

import type { Annotation, Operation, Vec3 } from "./operations";

export interface BoundingBox {
  min: Vec3;
  max: Vec3;
  size: Vec3;
}

export interface MeshAnalysis {
  triangleCount: number;
  vertexCount: number;
  boundingBox: BoundingBox;
  surfaceAreaMm2: number;
  volumeMm3?: number | null;
  isWatertight: boolean;
  isWindingConsistent: boolean;
  hasInvertedNormals: boolean;
  warnings: string[];
}

export interface MeshInfo {
  id: string;
  name: string;
  sourceFile: string;
  displayGlb?: string | null;
  format: string;
  analysis?: MeshAnalysis | null;
  positionMm: Vec3;
  rotationDeg: Vec3;
}

export interface ProjectSettings {
  units: string;
  minWallMm: number;
  pilotHoleMm: number;
  m3ClearanceMm: number;
  defaultFilletMm: number;
  defaultHelperThicknessMm: number;
}

export interface Project {
  id: string;
  name: string;
  createdAt: string;
  updatedAt: string;
  schemaVersion: number;
  meshes: MeshInfo[];
  operations: Operation[];
  annotations: Annotation[];
  settings: ProjectSettings;
}

export interface ValidationReport {
  isWatertight: boolean;
  isWindingConsistent: boolean;
  volumeMm3?: number | null;
  triangleCount: number;
  boundingBox: BoundingBox;
  warnings: string[];
}

export interface BooleanResponse {
  success: boolean;
  engine: string;
  message: string;
  log: string[];
  before?: ValidationReport | null;
  after?: ValidationReport | null;
  outputFile?: string | null;
}

export interface ExportResponse {
  success: boolean;
  file?: string | null;
  message: string;
  validation?: ValidationReport | null;
  log: string[];
}

export interface RepairResponse {
  meshId: string;
  before: MeshAnalysis;
  after: MeshAnalysis;
  actions: string[];
  success: boolean;
  message: string;
}

export interface EngineStatus {
  booleanEngine: string;
  blenderAvailable: boolean;
  manifoldAvailable: boolean;
  blenderPath?: string | null;
}

export interface HealthResponse {
  status: string;
  version: string;
  engine: EngineStatus;
}
