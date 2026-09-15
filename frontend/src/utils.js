export function escapeHtml(text) {
  if (!text) return '';
  const map = { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#039;' };
  return String(text).replace(/[&<>"']/g, m => map[m]);
}

export function capitalize(str) {
  if (!str) return '';
  return str.charAt(0).toUpperCase() + str.slice(1);
}

export function healthLabel(v) { return v > 0.8 ? 'Excellent' : v > 0.5 ? 'Good' : 'Low'; }
export function budgetLabel(v) { return v > 0.7 ? 'Great Value' : v > 0.4 ? 'Fair' : 'Pricey'; }
export function tasteLabel(v) { return v > 0.8 ? 'Perfect Match' : v > 0.5 ? 'Good Match' : 'Mild Match'; }

export function getErrorMessage(err) {
  if (err.name === 'ApiError') {
    if (err.status === 429) return "You're doing that too fast! Please wait a moment.";
    if (err.status === 400) return typeof err.details?.detail === 'string' ? err.details.detail : "Invalid request. Please submit a query first.";
    if (err.status === 501) return "Try this in the local demo — see the video linked below";
    if (err.status >= 500) return "Our servers are currently overwhelmed. Please try again later.";
    return typeof err.details?.detail === 'string' ? err.details.detail : `Server error (${err.status})`;
  }
  return "Network error. Please check your connection.";
}

export function extractWinnerReasons(dishName, traces) {
  let agentReasons = [];
  if (!traces || !dishName) return agentReasons;
  const startIdx = traces.findIndex(t => t.includes(`${dishName} Candidate Breakdown:`));
  if (startIdx !== -1) {
    for (let i = startIdx + 1; i < traces.length; i++) {
      if (traces[i].includes('=> Final U_total') || traces[i].includes('Candidate Breakdown:')) {
        break;
      }
      const match = traces[i].match(/-\s+([^:]+):\s+(.*?)\s+\(raw:/);
      if (match) {
        agentReasons.push({ agent: match[1].trim(), reason: match[2].trim() });
      }
    }
  }
  return agentReasons;
}

export function parseReasons(traces, winnerName) {
  let reasons = { health: '', budget: '', taste: '' };
  if (!traces || !winnerName) return reasons;
  const idx = traces.findIndex(t => t.includes(winnerName) && t.includes('Candidate Breakdown'));
  if (idx !== -1) {
    const lines = traces.slice(idx + 1, idx + 4);
    lines.forEach(l => {
      const match = l.match(/- (\w+) Agent: (.*?)(?: \(raw:|$)/);
      if (match) {
        if (match[1] === 'Health') reasons.health = match[2].trim();
        if (match[1] === 'Budget') reasons.budget = match[2].trim();
        if (match[1] === 'Taste') reasons.taste = match[2].trim();
      }
    });
  }
  return reasons;
}
