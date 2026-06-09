// Thin typed wrapper around the LocalMeshAI backend. The base URL is read from
// VITE_API_BASE (see .env.example) so the same UI can point at a local or remote backend
// without code changes — this is the seam that keeps a future SaaS move cheap.

import type { Operation } from "../types/operations";
import type {
  BooleanResponse,
  ExportResponse,
  HealthResponse,
  MeshInfo,
  Project,
  RepairResponse,
} from "../types/project";
import type { FeatureCatalog, PlanResponse } from "../types/operations";

export const API_BASE: string =
  (import.meta.env.VITE_API_BASE as string | undefined)?.replace(/\/$/, "") ||
  "http://localhost:8000";

class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
    this.name = "ApiError";
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { "Content-Type": "application/json", ...(init?.headers || {}) },
    ...init,
  });
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      detail = body.detail ?? JSON.stringify(body);
    } catch {
      /* keep statusText */
    }
    throw new ApiError(res.status, detail);
  }
  return (await res.json()) as T;
}

export function fileUrl(projectId: string, relativePath: string): string {
  const clean = relativePath.replace(/^\/+/, "");
  return `${API_BASE}/api/project/${projectId}/file/${clean}`;
}

export const api = {
  async health(): Promise<HealthResponse> {
    return request<HealthResponse>("/api/health");
  },

  async features(): Promise<{ catalog: FeatureCatalog; defaults: Record<string, number | string> }> {
    return request("/api/features");
  },

  async newProject(name: string): Promise<Project> {
    const r = await request<{ project: Project }>("/api/project/new", {
      method: "POST",
      body: JSON.stringify({ name }),
    });
    return r.project;
  },

  async getProject(id: string): Promise<Project> {
    const r = await request<{ project: Project }>(`/api/project/${id}`);
    return r.project;
  },

  async saveProject(project: Project): Promise<Project> {
    const r = await request<{ project: Project }>(`/api/project/${project.id}/save`, {
      method: "POST",
      body: JSON.stringify(project),
    });
    return r.project;
  },

  async importMesh(projectId: string, file: File): Promise<{ project: Project; mesh: MeshInfo }> {
    const form = new FormData();
    form.append("projectId", projectId);
    form.append("file", file);
    const res = await fetch(`${API_BASE}/api/import`, { method: "POST", body: form });
    if (!res.ok) {
      let detail = res.statusText;
      try {
        detail = (await res.json()).detail;
      } catch {
        /* ignore */
      }
      throw new ApiError(res.status, detail);
    }
    return (await res.json()) as { project: Project; mesh: MeshInfo };
  },

  async repair(projectId: string, meshId: string): Promise<RepairResponse> {
    return request<RepairResponse>("/api/mesh/repair", {
      method: "POST",
      body: JSON.stringify({ projectId, meshId }),
    });
  },

  async addHelper(project: Project, operation: Operation): Promise<Project> {
    const r = await request<{ project: Project }>("/api/operation/add-helper", {
      method: "POST",
      body: JSON.stringify({ project, operation }),
    });
    return r.project;
  },

  async updateHelper(project: Project, operation: Operation): Promise<Project> {
    const r = await request<{ project: Project }>("/api/operation/update-helper", {
      method: "POST",
      body: JSON.stringify({ project, operation }),
    });
    return r.project;
  },

  async deleteOperation(project: Project, operationId: string, suppress: boolean): Promise<Project> {
    const r = await request<{ project: Project }>("/api/operation/delete", {
      method: "POST",
      body: JSON.stringify({ project, operationId, suppress }),
    });
    return r.project;
  },

  async applyBoolean(project: Project, meshId: string, operationIds?: string[]): Promise<BooleanResponse> {
    return request<BooleanResponse>("/api/operation/apply-boolean", {
      method: "POST",
      body: JSON.stringify({ project, meshId, operationIds: operationIds ?? null }),
    });
  },

  async exportFinal(project: Project, meshId: string, format = "stl"): Promise<ExportResponse> {
    return request<ExportResponse>("/api/export/final-stl", {
      method: "POST",
      body: JSON.stringify({ project, meshId, format }),
    });
  },

  async exportHelper(project: Project, operationId: string, format = "stl"): Promise<ExportResponse> {
    return request<ExportResponse>("/api/export/helper-stl", {
      method: "POST",
      body: JSON.stringify({ project, operationId, format }),
    });
  },

  async plan(
    prompt: string,
    opts: { projectId?: string; meshId?: string; annotationId?: string; planner?: string } = {}
  ): Promise<PlanResponse> {
    return request<PlanResponse>("/api/ai/plan", {
      method: "POST",
      body: JSON.stringify({
        prompt,
        projectId: opts.projectId ?? null,
        meshId: opts.meshId ?? null,
        annotationId: opts.annotationId ?? null,
        planner: opts.planner ?? "rule_based",
      }),
    });
  },
};

export { ApiError };
