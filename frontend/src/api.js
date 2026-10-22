/**
 * AI Agent Review and Performance Improvement System - Centralized API Client
 */

const API_BASE = ""; // Relative path to support both dev proxy and production static hosting

async function request(endpoint, options = {}) {
  const url = `${API_BASE}${endpoint}`;
  const config = {
    headers: {
      "Content-Type": "application/json",
      ...options.headers,
    },
    ...options,
  };

  try {
    const res = await fetch(url, config);
    if (!res.ok) {
      let detail = `HTTP ${res.status}`;
      try {
        const errJson = await res.json();
        detail = errJson.detail || JSON.stringify(errJson);
      } catch (e) {
        detail = await res.text();
      }
      throw new Error(detail);
    }
    const contentType = res.headers.get("content-type");
    if (contentType && contentType.includes("application/json")) {
      return await res.json();
    }
    return await res.text();
  } catch (error) {
    console.error(`API Error on ${endpoint}:`, error);
    throw error;
  }
}

export const api = {
  // System Health
  getHealth: () => request("/api/health"),

  // Phase 1: External Agent Integration & Validation
  validateEndpoint: (data) =>
    request("/api/agents/validate-endpoint", {
      method: "POST",
      body: JSON.stringify(data),
    }),

  registerAgent: (data) =>
    request("/api/agents/register", {
      method: "POST",
      body: JSON.stringify(data),
    }),

  listAgents: () => request("/api/agents/list"),

  deleteAgent: (agentId) =>
    request(`/api/agents/${encodeURIComponent(agentId)}`, {
      method: "DELETE",
    }),

  // Sandbox Targets
  testFaqChatbot: (data, fault = "none") =>
    request(`/api/external-targets/faq-chatbot?inject_fault=${encodeURIComponent(fault)}`, {
      method: "POST",
      body: JSON.stringify(data),
    }),

  testResumeParser: (data) =>
    request("/api/external-targets/resume-parser", {
      method: "POST",
      body: JSON.stringify(data),
    }),

  testSentimentClassifier: (data) =>
    request("/api/external-targets/sentiment-classifier", {
      method: "POST",
      body: JSON.stringify(data),
    }),

  // Phase 2: Live Testing & Failure Detection
  connectAndTest: (data) =>
    request("/api/agents/connect-and-test", {
      method: "POST",
      body: JSON.stringify(data),
    }),

  runFailureSuite: (agentId) =>
    request(`/api/agents/${encodeURIComponent(agentId)}/run-failure-suite`, {
      method: "POST",
    }),

  executeSuite: (data) =>
    request("/api/tests/execute-suite", {
      method: "POST",
      body: JSON.stringify(data),
    }),

  getFailures: () => request("/api/failures/list"),

  // Phase 3: Root-Cause Diagnosis
  runDiagnosis: (data) =>
    request("/api/diagnosis/investigate", {
      method: "POST",
      body: JSON.stringify(data),
    }),

  getDiagnoses: () => request("/api/diagnosis/list"),

  // Phase 4: Fault Interaction Analysis (2^k factorial)
  runFaultInteractions: (data) =>
    request("/api/fault-interactions/evaluate", {
      method: "POST",
      body: JSON.stringify(data),
    }),

  // Phase 5: Repairs, 8 Hard Gates & Approvals
  generateRepairs: (data) =>
    request("/api/repairs/generate-and-validate", {
      method: "POST",
      body: JSON.stringify(data),
    }),

  getApprovalQueue: () => request("/api/repairs/approval-queue"),

  signOffRepair: (repairId, data) =>
    request(`/api/repairs/${encodeURIComponent(repairId)}/sign-off`, {
      method: "POST",
      body: JSON.stringify(data),
    }),

  // Phase 6: Benchmark & Evaluation
  getBenchmarkSummary: () => request("/api/benchmark/summary"),
  getBenchmarkScenarios: () => request("/api/benchmark/scenarios"),
  runWalkthrough: (sid, residualCheck = false) =>
    request("/api/benchmark/walkthrough", {
      method: "POST",
      body: JSON.stringify({ sid, residual_check: residualCheck }),
    }),

  // Audit Logs
  getAuditLogs: (limit = 100) => request(`/api/audit/logs?limit=${limit}`),

  // Reports
  getAgentReport: (agentId) =>
    request(`/api/reports/agent-report/${encodeURIComponent(agentId)}`),

  getReportPreview: (agentId = "faq-chatbot", targetName = "Target AI Agent") =>
    request(`/api/reports/preview?agent_id=${encodeURIComponent(agentId)}&target_name=${encodeURIComponent(targetName)}`),
};
