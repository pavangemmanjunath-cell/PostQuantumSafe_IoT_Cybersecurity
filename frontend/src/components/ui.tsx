import type { ReactNode } from "react";

export function Kpi({ label, value, hint, tone, testId }: { label: string; value: ReactNode; hint?: ReactNode; tone?: string; testId?: string }) {
  return (
    <div className={`kpi-card ${tone ?? ""}`} data-testid={testId}>
      <div className="label">{label}</div>
      <div className="value">{value}</div>
      {hint !== undefined && <div className="hint2">{hint}</div>}
    </div>
  );
}

export function Tabs<T extends string>({ tabs, active, onChange, testPrefix = "subtab" }: {
  tabs: { id: T; label: string; count?: number }[];
  active: T;
  onChange: (id: T) => void;
  testPrefix?: string;
}) {
  return (
    <div className="subtabs" role="tablist">
      {tabs.map((t) => (
        <button key={t.id} role="tab" aria-selected={active === t.id} className={`subtab ${active === t.id ? "active" : ""}`}
          onClick={() => onChange(t.id)} data-testid={`${testPrefix}-${t.id}`}>
          {t.label}{t.count !== undefined && <span className="count">{t.count}</span>}
        </button>
      ))}
    </div>
  );
}

export function Panel({ title, right, children, testId }: { title: string; right?: ReactNode; children: ReactNode; testId?: string }) {
  return (
    <div className="panel" data-testid={testId}>
      <div className="panel-h"><h3>{title}</h3>{right}</div>
      <div className="panel-b">{children}</div>
    </div>
  );
}

export const usd = (n: number) => `$${Math.round(n).toLocaleString("en-US")}`;
export const pretty = (s: string) => s.replaceAll("_", " ");
