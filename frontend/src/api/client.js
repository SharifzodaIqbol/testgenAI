const BASE_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

async function request(path, options = {}) {
  const token = localStorage.getItem("access_token");
  const headers = {
    "Content-Type": "application/json",
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
    ...options.headers,
  };

  const resp = await fetch(`${BASE_URL}/api/v1${path}`, {
    ...options,
    headers,
  });

  if (resp.status === 401) {
    localStorage.removeItem("access_token");
    window.location.href = "/login";
    return;
  }

  if (!resp.ok) {
    const err = await resp.json().catch(() => ({ detail: resp.statusText }));
    throw new Error(err.detail || "Ошибка запроса");
  }

  if (resp.status === 204) return null;
  return resp.json();
}

// ── Auth ──────────────────────────────────────────────────────────────────────

export const api = {
  auth: {
    register: (data) => request("/auth/register", { method: "POST", body: JSON.stringify(data) }),
    login: (data) => request("/auth/login", { method: "POST", body: JSON.stringify(data) }),
    me: () => request("/auth/me"),
  },

  projects: {
    list: () => request("/projects/"),
    create: (data) => request("/projects/", { method: "POST", body: JSON.stringify(data) }),
    delete: (id) => request(`/projects/${id}`, { method: "DELETE" }),
  },

  documents: {
    list: (projectId) => request(`/documents/project/${projectId}`),
    upload: (projectId, file) => {
      const token = localStorage.getItem("access_token");
      const form = new FormData();
      form.append("file", file);
      return fetch(`${BASE_URL}/api/v1/documents/upload?project_id=${projectId}`, {
        method: "POST",
        headers: { Authorization: `Bearer ${token}` },
        body: form,
      }).then((r) => r.json());
    },
    delete: (id) => request(`/documents/${id}`, { method: "DELETE" }),
  },

  generation: {
    start: (data) => request("/generation/start", { method: "POST", body: JSON.stringify(data) }),
    status: (taskId) => request(`/generation/${taskId}`),
    wsUrl: (taskId) =>
      `${BASE_URL.replace("http", "ws")}/api/v1/generation/ws/${taskId}`,
  },

  testCases: {
    suites: (projectId) => request(`/test-cases/suites/project/${projectId}`),
    getSuite: (suiteId) => request(`/test-cases/suites/${suiteId}`),
    deleteSuite: (suiteId) => request(`/test-cases/suites/${suiteId}`, { method: "DELETE" }),
    update: (caseId, data) =>
      request(`/test-cases/${caseId}`, { method: "PATCH", body: JSON.stringify(data) }),
    delete: (caseId) => request(`/test-cases/${caseId}`, { method: "DELETE" }),
    
    // Переписываем экспорт на честный fetch внутри вашего клиента
    exportJson: async (suiteId, suiteName = "suite") => {
      const token = localStorage.getItem("access_token");
      const resp = await fetch(`${BASE_URL}/api/v1/test-cases/suites/${suiteId}/export/json`, {
        headers: { "Authorization": `Bearer ${token}` }
      });
      if (!resp.ok) throw new Error("Ошибка скачивания JSON");
      const blob = await resp.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `${suiteName.replace(/\s+/g, '_')}.json`;
      a.click();
      window.URL.revokeObjectURL(url);
    },

    exportExcel: async (suiteId, suiteName = "suite") => {
      const token = localStorage.getItem("access_token");
      const resp = await fetch(`${BASE_URL}/api/v1/test-cases/suites/${suiteId}/export/excel`, {
        headers: { "Authorization": `Bearer ${token}` }
      });
      if (!resp.ok) throw new Error("Ошибка скачивания Excel");
      const blob = await resp.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `${suiteName.replace(/\s+/g, '_')}.xlsx`;
      a.click();
      window.URL.revokeObjectURL(url);
    }
  },
};
