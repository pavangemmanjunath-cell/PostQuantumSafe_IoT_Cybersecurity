/** Lightweight SVG charts (no chart library): score gauge, TIPPSS radar, sparkline. */

const riskColor = (score: number) => (score > 75 ? "#f43f5e" : score > 50 ? "#f97316" : score > 25 ? "#f59e0b" : "#22c55e");
const healthColor = (score: number) => riskColor(100 - score);

export function Gauge({ value, label }: { value: number; label: string }) {
  const v = Math.max(0, Math.min(100, value));
  const c = Math.PI * 52;
  const color = riskColor(v);
  return (
    <svg viewBox="0 0 140 92" width="100%" style={{ maxWidth: 220 }} role="img" aria-label={`${label}: ${v} of 100`} data-testid="gauge">
      <path d="M18 76 A52 52 0 0 1 122 76" fill="none" stroke="#1e293b" strokeWidth="12" strokeLinecap="round" />
      {v > 0 && (
        <path d="M18 76 A52 52 0 0 1 122 76" fill="none" stroke={color} strokeWidth="12" strokeLinecap="round"
          strokeDasharray={`${(v / 100) * c} ${c}`} style={{ transition: "stroke-dasharray 0.8s ease" }} />
      )}
      <text x="70" y="66" textAnchor="middle" fontSize="26" fontWeight="700" fill={color}>{v}</text>
      <text x="18" y="89" textAnchor="middle" fontSize="8" fill="#64748b">0</text>
      <text x="122" y="89" textAnchor="middle" fontSize="8" fill="#64748b">100</text>
      <text x="70" y="89" textAnchor="middle" fontSize="9" fill="#94a3b8">{label}</text>
    </svg>
  );
}

export function Radar({ scores }: { scores: Record<string, number> }) {
  const keys = Object.keys(scores);
  const cx = 160, cy = 118, R = 78;
  const pt = (i: number, v: number, r = R) => {
    const a = (Math.PI * 2 * i) / keys.length - Math.PI / 2;
    return [cx + Math.cos(a) * r * (v / 100), cy + Math.sin(a) * r * (v / 100)];
  };
  return (
    <svg viewBox="0 0 320 236" width="100%" style={{ maxWidth: 360 }} role="img" aria-label="TIPPSS pillar scores" data-testid="radar">
      {[25, 50, 75, 100].map((lvl) => (
        <polygon key={lvl} points={keys.map((_, i) => pt(i, lvl).join(",")).join(" ")} fill="none" stroke="#1e293b" />
      ))}
      {keys.map((_, i) => {
        const [x, y] = pt(i, 100);
        return <line key={i} x1={cx} y1={cy} x2={x} y2={y} stroke="#1e293b" />;
      })}
      <polygon points={keys.map((k, i) => pt(i, Math.max(scores[k], 2)).join(",")).join(" ")} fill="rgba(56,189,248,0.18)"
        stroke="#38bdf8" strokeWidth="2" style={{ transition: "all 0.6s" }} />
      {keys.map((k, i) => {
        const [x, y] = pt(i, 100, R + 16);
        const anchor = Math.abs(x - cx) < 4 ? "middle" : x > cx ? "start" : "end";
        return (
          <text key={k} x={x} y={y} textAnchor={anchor} dominantBaseline="middle" fontSize="11" fill="#cbd5e1">
            {k} <tspan fill={healthColor(scores[k])} fontWeight="700">{scores[k]}</tspan>
          </text>
        );
      })}
    </svg>
  );
}

export function Sparkline({ values, color = "#38bdf8", height = 34 }: { values: number[]; color?: string; height?: number }) {
  if (values.length < 2) return <svg height={height} width="100%" />;
  const max = Math.max(...values, 1e-9);
  const w = 200;
  const pts = values.map((v, i) => `${(i / (values.length - 1)) * w},${height - 2 - (v / max) * (height - 4)}`).join(" ");
  return (
    <svg viewBox={`0 0 ${w} ${height}`} width="100%" height={height} preserveAspectRatio="none">
      <polyline points={pts} fill="none" stroke={color} strokeWidth="1.6" vectorEffect="non-scaling-stroke" />
    </svg>
  );
}
