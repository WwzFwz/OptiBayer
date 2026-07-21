// Palet OptiBayer — samakan dengan app/ui.py (dark HMI + status semantik).
export const C = {
  surface: "#1a1a19",
  page: "#0d0d0d",
  ink: "#ffffff",
  ink2: "#c3c2b7",
  muted: "#898781",
  grid: "#2c2c2a",
  series: ["#3987e5", "#199e70", "#c98500", "#008300", "#9085e9"],
  status: {
    good: "#0ca30c",
    warning: "#fab219",
    serious: "#ec835a",
    critical: "#d03b3b",
    info: "#3987e5",
  },
} as const;

export type Severity = keyof typeof C.status;

// KPI: metrik yang NAIK = BURUK (delta hijau bila turun)
export const INVERTED = new Set([
  "total_opex",
  "reactive_sio2_pct",
  "red_mud_t",
]);

export function statusOf(key: string, v: number): Severity {
  switch (key) {
    case "recovery_pct":
      return v >= 85 ? "good" : v >= 82 ? "warning" : "critical";
    case "precip_yield_pct":
      return v >= 79 ? "good" : v >= 76 ? "warning" : "critical";
    case "reactive_sio2_pct":
      return v <= 5.5 ? "good" : v <= 6.3 ? "warning" : "critical";
    case "total_opex":
      return v <= 25000 ? "good" : v <= 40000 ? "warning" : "critical";
    case "red_mud_t":
      return v <= 500 ? "good" : v <= 580 ? "warning" : "critical";
    default:
      return "good";
  }
}
