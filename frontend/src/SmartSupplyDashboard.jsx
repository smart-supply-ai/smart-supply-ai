import { useState } from "react";
import { runPrediction } from "./services/alertService";

// ─────────────────────────────────────────────
// MOCK DATA
// Used as a fallback while the real API isn't connected yet.
// ─────────────────────────────────────────────
const MOCK_ORDERS = [
  {
    id: "ORD-4821",
    product: "Industrial Compressors",
    destination: "Hamburg, DE",
    expectedDelivery: "Mar 14, 2026",
    risk: 91,
    status: "Critical",
  },
  {
    id: "ORD-3377",
    product: "Electronic Components",
    destination: "Chicago, US",
    expectedDelivery: "Mar 11, 2026",
    risk: 74,
    status: "High",
  },
  {
    id: "ORD-5903",
    product: "Automotive Parts",
    destination: "Seoul, KR",
    expectedDelivery: "Mar 18, 2026",
    risk: 68,
    status: "High",
  },
  {
    id: "ORD-2265",
    product: "Medical Supplies",
    destination: "Toronto, CA",
    expectedDelivery: "Mar 12, 2026",
    risk: 55,
    status: "Medium",
  },
  {
    id: "ORD-7741",
    product: "Textile Rolls",
    destination: "Milan, IT",
    expectedDelivery: "Mar 20, 2026",
    risk: 42,
    status: "Medium",
  },
  {
    id: "ORD-6618",
    product: "Chemical Reagents",
    destination: "Mumbai, IN",
    expectedDelivery: "Mar 15, 2026",
    risk: 28,
    status: "Low",
  },
];

const SUMMARY_STATS = [
  { label: "Orders Analyzed", value: "1,284", icon: "📦", delta: "+38 today" },
  {
    label: "At-Risk Orders",
    value: "47",
    icon: "⚠️",
    delta: "+5 since yesterday",
  },
  {
    label: "Avg. Delay (days)",
    value: "3.2",
    icon: "🕐",
    delta: "+0.4 this week",
  },
  {
    label: "On-Time Rate",
    value: "94.6%",
    icon: "✅",
    delta: "-0.3% this week",
  },
];

// ─────────────────────────────────────────────
// COMPONENT: Header
// ─────────────────────────────────────────────
function Header() {
  return (
    <header style={styles.header}>
      <div style={styles.headerLeft}>
        <div style={styles.logoMark}>SS</div>
        <div>
          <h1 style={styles.appTitle}>
            Smart Supply <span style={styles.titleAccent}>AI</span>
          </h1>
          <p style={styles.appSubtitle}>
            Predictive logistics intelligence — identify late deliveries before
            they happen
          </p>
        </div>
      </div>
      <div style={styles.headerRight}>
        <span style={styles.liveBadge}>● LIVE</span>
        <span style={styles.timestamp}>
          Last sync: {new Date().toLocaleTimeString()}
        </span>
      </div>
    </header>
  );
}

// ─────────────────────────────────────────────
// COMPONENT: SummaryCard
// Displays one KPI. Receives label, value, icon, delta as props.
// ─────────────────────────────────────────────
function SummaryCard({ label, value, icon, delta }) {
  return (
    <div style={styles.card}>
      <div style={styles.cardIcon}>{icon}</div>
      <div style={styles.cardValue}>{value}</div>
      <div style={styles.cardLabel}>{label}</div>
      <div style={styles.cardDelta}>{delta}</div>
    </div>
  );
}

// ─────────────────────────────────────────────
// COMPONENT: SummaryBar
// Lays out four SummaryCards in a grid row.
// ─────────────────────────────────────────────
function SummaryBar() {
  return (
    <section style={styles.summaryBar}>
      {SUMMARY_STATS.map((stat) => (
        <SummaryCard key={stat.label} {...stat} />
      ))}
    </section>
  );
}

// ─────────────────────────────────────────────
// COMPONENT: RiskBadge
// Color-coded pill driven by the status string.
// ─────────────────────────────────────────────
function RiskBadge({ status }) {
  const colors = {
    Critical: { bg: "#ff1e1e22", color: "#ff4d4d", border: "#ff4d4d55" },
    High: { bg: "#ff6b0022", color: "#ff8c42", border: "#ff8c4255" },
    Medium: { bg: "#f5c54222", color: "#f5c542", border: "#f5c54255" },
    Low: { bg: "#00e09622", color: "#00e096", border: "#00e09655" },
  };
  const c = colors[status] || colors.Low;
  return (
    <span
      style={{
        ...styles.badge,
        background: c.bg,
        color: c.color,
        border: `1px solid ${c.border}`,
      }}
    >
      {status}
    </span>
  );
}

// ─────────────────────────────────────────────
// COMPONENT: RiskBar
// Thin progress bar; colour shifts green → yellow → orange → red by score.
// ─────────────────────────────────────────────
function RiskBar({ score }) {
  const color =
    score > 80
      ? "#ff4d4d"
      : score > 60
        ? "#ff8c42"
        : score > 40
          ? "#f5c542"
          : "#00e096";
  return (
    <div style={styles.riskBarTrack}>
      <div
        style={{ ...styles.riskBarFill, width: `${score}%`, background: color }}
      />
    </div>
  );
}

// ─────────────────────────────────────────────
// COMPONENT: OrderRow
// One row in the flagged-orders table.
// ─────────────────────────────────────────────
function OrderRow({ order }) {
  return (
    <tr style={styles.tableRow}>
      <td style={{ ...styles.td, ...styles.monoText, color: "#a78bfa" }}>
        {order.id}
      </td>
      <td style={styles.td}>{order.product}</td>
      <td style={{ ...styles.td, color: "#94a3b8" }}>{order.destination}</td>
      <td style={{ ...styles.td, ...styles.monoText }}>
        {order.expectedDelivery}
      </td>
      <td style={styles.td}>
        <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
          <RiskBar score={order.risk} />
          <span
            style={{
              ...styles.monoText,
              fontSize: "12px",
              color: "#cbd5e1",
              minWidth: "30px",
            }}
          >
            {order.risk}
          </span>
        </div>
      </td>
      <td style={styles.td}>
        <RiskBadge status={order.status} />
      </td>
    </tr>
  );
}

// ─────────────────────────────────────────────
// COMPONENT: OrdersTable
// Full results table. Shows empty state before first run.
// ─────────────────────────────────────────────
function OrdersTable({ orders }) {
  if (orders.length === 0) {
    return (
      <p style={styles.emptyState}>
        No results yet. Run a prediction to analyze your orders.
      </p>
    );
  }
  return (
    <div style={styles.tableWrapper}>
      <table style={styles.table}>
        <thead>
          <tr>
            {[
              "Order ID",
              "Product",
              "Destination",
              "Expected Delivery",
              "Risk Score",
              "Status",
            ].map((h) => (
              <th key={h} style={styles.th}>
                {h}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {orders.map((order) => (
            <OrderRow key={order.id} order={order} />
          ))}
        </tbody>
      </table>
    </div>
  );
}

// ────────────────────────────────────────────────────────────────────────────
// COMPONENT: PredictionPanel
// This component owns the async state machine for the prediction flow.
// It delegates the actual API call to alertService.js.
// ────────────────────────────────────────────────────────────────────────────
function PredictionPanel() {
  const [orders, setOrders] = useState([]);
  const [ordersAnalyzed, setOrdersAnalyzed] = useState(0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [hasRun, setHasRun] = useState(false);

  async function handleRunPrediction() {
    setLoading(true);
    setError(null);
    setOrders([]);
    setOrdersAnalyzed(0);

    try {
      const { orders: flagged, ordersAnalyzed: analyzed } =
        await runPrediction();
      setOrders(flagged);
      setOrdersAnalyzed(analyzed);
      setHasRun(true);
    } catch (err) {
      if (import.meta.env.DEV) {
        console.warn("API unavailable — using mock data:", err.message);
        const sorted = [...MOCK_ORDERS].sort((a, b) => b.risk - a.risk);
        setOrders(sorted);
        setOrdersAnalyzed(sorted.length);
        setHasRun(true);
      } else {
        setError(err.message ?? "An unexpected error occurred.");
      }
    } finally {
      setLoading(false);
    }
  }

  return (
    <section style={styles.panel}>
      {/* Panel header row: title + button */}
      <div style={styles.panelHeader}>
        <div>
          <h2 style={styles.panelTitle}>Late Delivery Predictor</h2>
          <p style={styles.panelSubtitle}>
            Scan active orders and surface those most likely to miss their
            delivery window.
          </p>
        </div>
        <button
          onClick={handleRunPrediction}
          disabled={loading}
          style={{
            ...styles.runButton,
            opacity: loading ? 0.6 : 1,
            cursor: loading ? "not-allowed" : "pointer",
          }}
        >
          {loading ? (
            <span style={styles.buttonInner}>
              <span style={styles.spinner} /> Analyzing…
            </span>
          ) : (
            <span style={styles.buttonInner}>▶ Run Prediction</span>
          )}
        </button>
      </div>

      {/* Error banner */}
      {error && (
        <div style={styles.errorBanner}>
          <span style={styles.errorIcon}>⚠</span>
          <span>{error}</span>
        </div>
      )}

      {/* Results count row */}
      {hasRun && !loading && !error && (
        <div style={styles.resultsHeader}>
          <span style={styles.resultsCount}>
            {orders.length} of {ordersAnalyzed} orders flagged — sorted by risk
          </span>
          <span style={styles.resultsMeta}>
            {import.meta.env.DEV
              ? "Mock data · replace with live API"
              : "Live data"}
          </span>
        </div>
      )}

      {/* Loading state */}
      {loading && <p style={styles.loadingText}>Running prediction model…</p>}

      {/* Results table */}
      {!loading && <OrdersTable orders={orders} />}
    </section>
  );
}

// ─────────────────────────────────────────────
// COMPONENT: Dashboard (Root / Page Component)
// ─────────────────────────────────────────────
export default function Dashboard() {
  return (
    <div style={styles.page}>
      <div style={styles.gridOverlay} />
      <div style={styles.container}>
        <Header />
        <SummaryBar />
        <PredictionPanel />
        <footer style={styles.footer}>
          Smart Supply AI · Powered by predictive ML · Mock data only
        </footer>
      </div>
    </div>
  );
}

// ─────────────────────────────────────────────
// STYLES
// ─────────────────────────────────────────────
const styles = {
  page: {
    minHeight: "100vh",
    width: "100%",
    background: "#080c14",
    fontFamily: "'DM Sans', 'Segoe UI', sans-serif",
    color: "#e2e8f0",
    position: "relative",
    overflowX: "hidden",
    boxSizing: "border-box",
  },
  gridOverlay: {
    position: "fixed",
    inset: 0,
    backgroundImage:
      "linear-gradient(rgba(99,102,241,0.04) 1px, transparent 1px), linear-gradient(90deg, rgba(99,102,241,0.04) 1px, transparent 1px)",
    backgroundSize: "40px 40px",
    pointerEvents: "none",
    zIndex: 0,
  },
  container: {
    position: "relative",
    zIndex: 1,
    maxWidth: "1200px",
    margin: "0 auto",
    padding: "32px 24px",
    display: "flex",
    flexDirection: "column",
    gap: "28px",
  },
  header: {
    display: "flex",
    alignItems: "center",
    justifyContent: "space-between",
    borderBottom: "1px solid #1e293b",
    paddingBottom: "24px",
  },
  headerLeft: { display: "flex", alignItems: "center", gap: "16px" },
  logoMark: {
    width: "48px",
    height: "48px",
    borderRadius: "12px",
    background: "linear-gradient(135deg, #6366f1, #8b5cf6)",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    fontWeight: "800",
    fontSize: "16px",
    color: "#fff",
    letterSpacing: "0.05em",
    flexShrink: 0,
  },
  appTitle: {
    margin: 0,
    fontSize: "26px",
    fontWeight: "700",
    letterSpacing: "-0.02em",
    color: "#f1f5f9",
  },
  titleAccent: { color: "#818cf8" },
  appSubtitle: { margin: "2px 0 0", fontSize: "13px", color: "#64748b" },
  headerRight: {
    display: "flex",
    flexDirection: "column",
    alignItems: "flex-end",
    gap: "4px",
  },
  liveBadge: {
    fontSize: "11px",
    fontWeight: "700",
    color: "#00e096",
    letterSpacing: "0.1em",
  },
  timestamp: {
    fontSize: "12px",
    color: "#475569",
    fontFamily: "'Courier New', monospace",
  },
  summaryBar: {
    display: "grid",
    gridTemplateColumns: "repeat(4, 1fr)",
    gap: "16px",
  },
  card: {
    background: "#0f172a",
    border: "1px solid #1e293b",
    borderRadius: "14px",
    padding: "20px",
    display: "flex",
    flexDirection: "column",
    gap: "4px",
  },
  cardIcon: { fontSize: "22px", marginBottom: "4px" },
  cardValue: {
    fontSize: "28px",
    fontWeight: "700",
    color: "#f1f5f9",
    letterSpacing: "-0.03em",
    fontFamily: "'Courier New', monospace",
  },
  cardLabel: { fontSize: "13px", color: "#64748b", fontWeight: "500" },
  cardDelta: { fontSize: "12px", color: "#475569", marginTop: "2px" },
  panel: {
    background: "#0f172a",
    border: "1px solid #1e293b",
    borderRadius: "16px",
    padding: "28px",
    display: "flex",
    flexDirection: "column",
    gap: "20px",
  },
  panelHeader: {
    display: "flex",
    alignItems: "flex-start",
    justifyContent: "space-between",
    gap: "16px",
  },
  panelTitle: {
    margin: 0,
    fontSize: "18px",
    fontWeight: "700",
    color: "#f1f5f9",
  },
  panelSubtitle: {
    margin: "4px 0 0",
    fontSize: "13px",
    color: "#64748b",
    maxWidth: "420px",
  },
  runButton: {
    background: "linear-gradient(135deg, #6366f1, #8b5cf6)",
    color: "#fff",
    border: "none",
    borderRadius: "10px",
    padding: "12px 24px",
    fontSize: "14px",
    fontWeight: "600",
    letterSpacing: "0.01em",
    boxShadow: "0 4px 20px rgba(99,102,241,0.35)",
    flexShrink: 0,
  },
  buttonInner: { display: "flex", alignItems: "center", gap: "8px" },
  spinner: {
    display: "inline-block",
    width: "12px",
    height: "12px",
    border: "2px solid rgba(255,255,255,0.3)",
    borderTopColor: "#fff",
    borderRadius: "50%",
    animation: "spin 0.8s linear infinite",
  },
  errorBanner: {
    display: "flex",
    alignItems: "center",
    gap: "10px",
    background: "#ff1e1e18",
    border: "1px solid #ff4d4d44",
    borderRadius: "10px",
    padding: "12px 16px",
    color: "#ff6b6b",
    fontSize: "13px",
  },
  errorIcon: { fontSize: "16px", flexShrink: 0 },
  resultsHeader: {
    display: "flex",
    justifyContent: "space-between",
    alignItems: "center",
    padding: "8px 0",
    borderTop: "1px solid #1e293b",
  },
  resultsCount: { fontSize: "13px", color: "#94a3b8", fontWeight: "600" },
  resultsMeta: {
    fontSize: "11px",
    color: "#334155",
    fontFamily: "'Courier New', monospace",
  },
  tableWrapper: {
    overflowX: "auto",
    borderRadius: "10px",
    border: "1px solid #1e293b",
  },
  table: { width: "100%", borderCollapse: "collapse", fontSize: "13px" },
  th: {
    background: "#0a0f1e",
    padding: "12px 16px",
    textAlign: "left",
    color: "#475569",
    fontWeight: "600",
    fontSize: "11px",
    letterSpacing: "0.07em",
    textTransform: "uppercase",
    borderBottom: "1px solid #1e293b",
    whiteSpace: "nowrap",
  },
  tableRow: { borderBottom: "1px solid #131c2e" },
  td: { padding: "14px 16px", color: "#cbd5e1", verticalAlign: "middle" },
  monoText: { fontFamily: "'Courier New', monospace", fontSize: "12px" },
  badge: {
    display: "inline-block",
    padding: "3px 10px",
    borderRadius: "20px",
    fontSize: "11px",
    fontWeight: "700",
    letterSpacing: "0.05em",
    whiteSpace: "nowrap",
  },
  riskBarTrack: {
    width: "80px",
    height: "5px",
    background: "#1e293b",
    borderRadius: "99px",
    overflow: "hidden",
    flexShrink: 0,
  },
  riskBarFill: {
    height: "100%",
    borderRadius: "99px",
    transition: "width 0.6s ease",
  },
  emptyState: {
    textAlign: "center",
    color: "#334155",
    padding: "40px 0",
    fontSize: "14px",
  },
  loadingText: {
    textAlign: "center",
    color: "#475569",
    fontSize: "13px",
    fontFamily: "'Courier New', monospace",
    padding: "20px 0",
  },
  footer: {
    textAlign: "center",
    fontSize: "12px",
    color: "#1e293b",
    paddingTop: "8px",
    fontFamily: "'Courier New', monospace",
  },
};
