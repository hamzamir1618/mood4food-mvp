export class ApiError extends Error {
  constructor(message, status, details) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.details = details;
  }
}

const API_BASE = '';

async function handleResponse(resp) {
  if (!resp.ok) {
    let details = {};
    try {
      details = await resp.json();
    } catch (e) {}
    throw new ApiError(details.detail || `Server responded ${resp.status}`, resp.status, details);
  }
  return resp.json();
}

export async function submitQuery(input) {
  const resp = await fetch(`${API_BASE}/submit`, { method: 'POST', body: input });
  return handleResponse(resp);
}

export async function recalculate(weights) {
  const resp = await fetch(`${API_BASE}/recalculate`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(weights),
  });
  return handleResponse(resp);
}

export async function getFulfillment() {
  const resp = await fetch(`${API_BASE}/decision_blueprint`);
  return handleResponse(resp);
}

export async function getAlternate(rejectedIds) {
  const resp = await fetch(`${API_BASE}/alternate`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ already_rejected: rejectedIds })
  });
  return handleResponse(resp);
}
