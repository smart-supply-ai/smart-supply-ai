const BASE_URL = import.meta.env.VITE_API_URL ?? "/api/alerts";

export async function runPrediction() {
  const response = await fetch(`${BASE_URL}/run`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
  });

  if (!response.ok) {
    const body = await response.text();
    throw new Error(`Alert service error (${response.status}): ${body}`);
  }

  const data = await response.json();
  return normalizeAlerts(data.alerts ?? [], data.orders_analyzed ?? 0);
}

export async function checkHealth() {
  try {
    const response = await fetch(`${BASE_URL.replace("/alerts", "")}/health`);
    return response.ok;
  } catch {
    return false;
  }
}

const RISK_STATUS_MAP = { HIGH: "High", MEDIUM: "Medium", LOW: "Low" };

function normalizeAlerts(alerts, ordersAnalyzed) {
  return {
    ordersAnalyzed,

    orders: alerts
      .map((alert) => ({
          id: `ORD-${alert.order_index}`,
          product: alert.product_name ?? "— pending",
          destination: alert.order_city && alert.order_country 
              ? `${alert.order_city}, ${alert.order_country}` 
              : "— pending",
          expectedDelivery: alert.shipping_date 
              ? new Date(alert.shipping_date).toLocaleDateString("en-US", {month: "short", day: "numeric", year: "numeric"})
              : "— pending",
          risk: alert.risk_score,
          status: RISK_STATUS_MAP[alert.risk_level] ?? "Low",
          probability: alert.probability,
      }))
      .sort((a, b) => b.risk - a.risk),
  };
}
