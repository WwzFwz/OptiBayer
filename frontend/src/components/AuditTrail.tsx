"use client";
// Audit Trail — keputusan advisory (terima/tolak) yang dicatat operator.
// Human-in-the-loop yang bisa diaudit (port dari Overview Streamlit).
import { useStore } from "@/lib/store";
import { C } from "@/lib/theme";

export default function AuditTrail() {
  const { decisions } = useStore();
  const rows = Object.entries(decisions).map(([key, d]) => {
    // key = "scenario-hour-title"
    const parts = key.split("-");
    const hour = parts[1] ?? "?";
    const title = parts.slice(2).join("-");
    return { hour, title, decision: d };
  }).reverse();

  return (
    <div className="rounded-xl p-3" style={{ background: C.surface, border: `1px solid ${C.grid}` }}>
      <p className="mb-2 text-sm font-semibold" style={{ color: C.ink }}>
        Audit Trail Keputusan Advisory
      </p>
      {rows.length === 0 ? (
        <p className="text-sm" style={{ color: C.muted }}>
          Belum ada keputusan. Klik Terima/Tolak pada kartu advisory — setiap
          keputusan tercatat di sini (human-in-the-loop, dapat diaudit).
        </p>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-xs" style={{ color: C.ink2 }}>
            <thead><tr style={{ color: C.muted }}>
              <th className="p-1.5 text-left">Jam Sim</th>
              <th className="p-1.5 text-left">Advisory</th>
              <th className="p-1.5 text-left">Keputusan</th>
            </tr></thead>
            <tbody>
              {rows.map((r, i) => (
                <tr key={i} style={{ borderTop: `1px solid ${C.grid}` }}>
                  <td className="p-1.5 font-mono">{r.hour}:00</td>
                  <td className="p-1.5">{r.title}</td>
                  <td className="p-1.5 font-semibold"
                      style={{ color: r.decision === "terima" ? C.status.good : C.status.critical }}>
                    {r.decision === "terima" ? "✓ DITERIMA" : "✗ DITOLAK"}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          <p className="mt-2 text-xs" style={{ color: C.muted }}>
            {rows.length} keputusan tercatat di sesi ini.
          </p>
        </div>
      )}
    </div>
  );
}
