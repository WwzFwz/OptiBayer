"use client";
// Diagram Proses HMI (SVG) — sirkuit Bayer live, 3 lapisan analitik.
// Port dari app/views/pfd.py; SVG lebih tajam & mudah dianimasikan dari Plotly.
import { useState } from "react";
import { Line, LineChart, ResponsiveContainer } from "recharts";
import { useStore } from "@/lib/store";
import { C, Severity } from "@/lib/theme";

function Spark({ data, dataKey, title, color, cur }: {
  data: Array<Record<string, number>>; dataKey: string; title: string;
  color: string; cur: number;
}) {
  return (
    <div className="rounded-lg p-2" style={{ background: C.surface, border: `1px solid ${C.grid}` }}>
      <p className="mb-1 text-xs" style={{ color: C.ink2 }}>
        {title} · <b style={{ color }}>{cur.toFixed(1)}</b>
      </p>
      <ResponsiveContainer width="100%" height={44}>
        <LineChart data={data}>
          <Line type="monotone" dataKey={dataKey} stroke={color} strokeWidth={2}
                dot={false} isAnimationActive={false} />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}

type Layer = "operasi" | "aluminium" | "kebocoran" | "karbon";
const PIPE = {
  liquor: C.series[0], slurry: "#b08968", redmud: C.status.serious,
  product: C.status.good, water: C.series[1], recycle: C.series[1],
};

export default function Diagram() {
  const { hourData, seq, hour } = useStore();
  const [layer, setLayer] = useState<Layer>("operasi");
  if (!hourData) return <p style={{ color: C.muted }}>Memuat…</p>;

  // sparkline 12 jam terakhir (konteks tren di atas diagram)
  const h12 = seq?.hours.slice(Math.max(0, hour - 11), hour + 1)
    .map((h, i) => ({ i, ...h })) ?? [];

  const nb = hourData.na_balance;
  const cb = hourData.carbonation;
  const kpi = hourData.kpi;
  const sio2 = kpi.reactive_sio2_pct;
  const feedStat: Severity = hourData.silika_level === "critical" ? "critical"
    : hourData.silika_level === "warning" ? "warning" : "good";

  // highlight per lapisan
  const hl = (tag: string): string | null => {
    if (layer === "aluminium")
      // jalur Al: masuk (feed+recycle) → proses → produk (hijau) / red mud (merah)
      return { feed: C.series[0], slurry2: C.series[0], recycle: C.series[4],
               dig: C.series[0], overflow: C.series[0],
               product: C.status.good, underflow: C.status.critical,
               tailing: C.status.critical }[tag] ?? null;
    if (layer === "kebocoran")
      return { naoh: C.status.info, recycle: C.status.warning,
               underflow: C.status.critical, tailing: C.status.critical,
               recovered: C.status.good }[tag] ?? null;
    if (layer === "karbon")
      return { underflow: C.status.good, tailing: C.status.good }[tag] ?? null;
    return "keep";
  };
  const pipeColor = (tag: string, kind: keyof typeof PIPE) => {
    const h = hl(tag);
    if (h === "keep") return PIPE[kind];
    return h ?? C.grid;
  };
  const pipeW = (tag: string) =>
    layer === "operasi" ? 5 : hl(tag) ? 6.5 : 2.5;

  return (
    <div className="space-y-3">
      <div className="flex gap-2">
        {([["operasi", "Operasi"], ["aluminium", "Aliran Aluminium"],
           ["kebocoran", "Kebocoran NaOH"],
           ["karbon", "Jalur Karbon (CCUS)"]] as const).map(([id, lbl]) => (
          <button key={id} onClick={() => setLayer(id)}
            className="rounded-lg px-3 py-1.5 text-sm"
            style={{ border: `1px solid ${layer === id ? C.series[0] : C.grid}`,
                     background: layer === id ? "#26262450" : "transparent",
                     color: layer === id ? C.ink : C.muted }}>
            {lbl}
          </button>
          ))}
      </div>

      {/* sparkline konteks 12 jam */}
      {h12.length > 2 && (
        <div className="grid grid-cols-3 gap-2">
          <Spark data={h12} dataKey="recovery_pct" title="Recovery 12 jam (%)"
                 color={C.series[0]} cur={kpi.recovery_pct} />
          <Spark data={h12} dataKey="reactive_sio2_pct" title="SiO₂ feed 12 jam (%)"
                 color={C.series[4]} cur={sio2} />
          <Spark data={h12} dataKey="red_mud_t" title="Red mud 12 jam (t)"
                 color={C.series[1]} cur={kpi.red_mud_t} />
        </div>
      )}

      <div className="rounded-xl p-2" style={{ background: C.surface, border: `1px solid ${C.grid}` }}>
        <svg viewBox="0 0 1420 640" className="w-full" style={{ maxHeight: "62vh" }}>
          {/* PIPA */}
          <Pipe d="M175,120 H330 V180" color={pipeColor("feed", "slurry")} w={pipeW("feed")} />
          <Pipe d="M175,250 H235" color={pipeColor("naoh", "liquor")} w={pipeW("naoh")} />
          <Pipe d="M175,380 H330 V310" color={pipeColor("cao", "water")} w={pipeW("cao")} />
          <Pipe d="M445,430 H205 V250 H235" color={pipeColor("recycle", "recycle")} w={pipeW("recycle")} dash />
          <Pipe d="M425,250 H590 V190" color={pipeColor("slurry2", "slurry")} w={pipeW("slurry2")} />
          <Pipe d="M685,120 H775" color={pipeColor("dig", "liquor")} w={pipeW("dig")} />
          <Pipe d="M870,165 V405" color={pipeColor("overflow", "liquor")} w={pipeW("overflow")} />
          <Pipe d="M965,120 H1150 V265" color={pipeColor("underflow", "redmud")} w={pipeW("underflow")} />
          <Pipe d="M870,495 V665" color={pipeColor("product", "product")} w={pipeW("product")} />
          <Pipe d="M775,450 H535 V475" color={pipeColor("spent", "liquor")} w={pipeW("spent")} />
          <Pipe d="M1330,120 V310 H1245" color={pipeColor("water", "water")} w={pipeW("water")} />
          <Pipe d="M1150,355 V500" color={pipeColor("tailing", "redmud")} w={pipeW("tailing")} />
          <Pipe d="M1055,310 H1000 V430 H630" color={pipeColor("recovered", "recycle")} w={pipeW("recovered")} dash />

          {/* TERMINAL */}
          <Term x={100} y={120} label="Washed Bauxite" />
          <Term x={100} y={250} label="NaOH" />
          <Term x={100} y={380} label="CaO" />
          <Term x={1330} y={95} label="Air Cuci" />
          <Term x={870} y={700} label="Produk Al(OH)₃" />
          <Term x={1150} y={535} label="Tailing → CCUS" />

          {/* STASIUN */}
          <Unit x={330} y={250} label="Pre-Desilication" stat={feedStat} />
          <Unit x={590} y={120} label="Digestion" stat="good" />
          <Unit x={870} y={120} label="Filtration" stat="good" />
          <Unit x={870} y={450} label="Precipitation"
                stat={kpi.precip_yield_pct >= 79 ? "good" : "warning"} />
          <Unit x={535} y={430} label="Conditioning" stat="good" />
          <Unit x={1150} y={310} label="RM Washing" stat="good" />

          {/* READOUT per lapisan */}
          {layer === "operasi" && <>
            <Readout x={250} y={70} label="SiO₂ reaktif" val={`${sio2.toFixed(1)} %`}
                     color={feedStat !== "good" ? C.status[feedStat] : "#ffd84d"} />
            <Readout x={735} y={70} label="Recovery" val={`${kpi.recovery_pct.toFixed(1)} %`} />
            <Readout x={735} y={470} label="Yield" val={`${kpi.precip_yield_pct.toFixed(1)} %`} />
            <Readout x={985} y={360} label="Al(OH)₃" val="produk" color={C.status.good} />
            <Readout x={1265} y={410} label="Red mud" val={`${kpi.red_mud_t.toFixed(0)} t`}
                     color={C.status.serious} />
          </>}
          {layer === "aluminium" && (() => {
            const ab = hourData.al_balance ?? {};
            const feed = ab.feed_t ?? 0, lost = ab.lost_redmud_t ?? 0;
            const pct = feed > 0 ? (lost / feed * 100) : 0;
            return <>
              <Readout x={250} y={70} label="Al feed bauksit"
                       val={`${feed.toFixed(0)} t`} color={C.series[0]} />
              <Readout x={320} y={200} label="Al recycle"
                       val={`${(ab.recycled_t ?? 0).toFixed(0)} t`} color={C.series[4]} />
              <Readout x={985} y={360} label="Produk Al(OH)₃"
                       val={`${(ab.hydrate_t ?? 0).toFixed(0)} t`} color={C.status.good} />
              <Readout x={1265} y={410} label="Al HILANG ke red mud"
                       val={`${lost.toFixed(1)} t · ${pct.toFixed(1)}%`}
                       color={C.status.critical} />
              <Readout x={735} y={70} label="Recovery"
                       val={`${kpi.recovery_pct.toFixed(1)} %`}
                       color={kpi.recovery_pct >= 85 ? C.status.good : C.status.critical} />
            </>;
          })()}
          {layer === "kebocoran" && <>
            <Readout x={490} y={330} label="Make-up NaOH" val={`${nb.makeup_t?.toFixed(1)} t`} color={C.status.info} />
            <Readout x={735} y={70} label="Terkunci DSP" val={`${nb.dsp_loss_t?.toFixed(1)} t`} color={C.status.warning} />
            <Readout x={320} y={200} label="Soda mati" val={`${nb.dead_soda_net_t?.toFixed(1)} t`} color={C.status.serious} />
            <Readout x={1265} y={280} label="Loss fisik" val={`${nb.physical_loss_t?.toFixed(1)} t`} color={C.status.critical} />
          </>}
          {layer === "karbon" && <>
            <Readout x={1265} y={410} label="Red mud" val={`${kpi.red_mud_t.toFixed(0)} t`} color={C.status.good} />
            <Readout x={985} y={360} label="Potensi CO₂" val={`${cb.co2_sequestered_t?.toFixed(1)} t`} color={C.status.good} />
            <Readout x={735} y={470} label="Nilai karbon" val={`Rp${(cb.carbon_value_idr ?? 0).toLocaleString("id-ID", { maximumFractionDigits: 0 })}`} color={C.status.good} />
          </>}
        </svg>
      </div>

      <div className="grid grid-cols-3 gap-2">
        <Gauge title="Recovery Al" val={kpi.recovery_pct} good={85} warn={82} />
        <Gauge title="Yield Presipitasi" val={kpi.precip_yield_pct} good={79} warn={76} />
        <Gauge title="Silika (inv)" val={sio2} good={5.5} warn={6.3} inverted />
      </div>
      <p className="text-xs" style={{ color: C.muted }}>
        PFD gambaran besar · satuan ton/jam (skala pabrik) · ganti lapisan untuk
        cerita kebocoran NaOH / jalur karbon.
      </p>
    </div>
  );
}

function Pipe({ d, color, w, dash }: { d: string; color: string; w: number; dash?: boolean }) {
  return <path d={d} fill="none" stroke={color} strokeWidth={w}
               strokeDasharray={dash ? "8 6" : undefined} strokeLinejoin="round" />;
}
function Unit({ x, y, label, stat }: { x: number; y: number; label: string; stat: Severity }) {
  return (
    <g>
      <rect x={x - 95} y={y - 32} width={190} height={64} rx={4}
            fill="#262624" stroke={C.status[stat]} strokeWidth={2.5} />
      <circle cx={x + 78} cy={y - 20} r={5} fill={C.status[stat]} />
      <text x={x} y={y + 5} textAnchor="middle" fill={C.ink} fontSize={13} fontWeight={700}>{label}</text>
    </g>
  );
}
function Term({ x, y, label }: { x: number; y: number; label: string }) {
  return (
    <g>
      <rect x={x - 72} y={y - 20} width={144} height={40} rx={3}
            fill={C.surface} stroke={C.muted} />
      <text x={x} y={y + 5} textAnchor="middle" fill={C.ink2} fontSize={12}>{label}</text>
    </g>
  );
}
function Readout({ x, y, label, val, color = "#ffd84d" }: {
  x: number; y: number; label: string; val: string; color?: string;
}) {
  return (
    <g>
      <rect x={x - 70} y={y - 14} width={140} height={30} rx={2}
            fill="#0c0c0b" stroke="#3a3a38" />
      <text x={x} y={y - 20} textAnchor="middle" fill={C.muted} fontSize={9}>{label}</text>
      <text x={x} y={y + 6} textAnchor="middle" fill={color} fontSize={13}
            fontWeight={700} fontFamily="monospace">{val}</text>
    </g>
  );
}
function Gauge({ title, val, good, warn, inverted }: {
  title: string; val: number; good: number; warn: number; inverted?: boolean;
}) {
  const ok = inverted ? val <= good : val >= good;
  const mid = inverted ? val <= warn : val >= warn;
  const col = ok ? C.status.good : mid ? C.status.warning : C.status.critical;
  const pct = Math.max(0, Math.min(100, inverted ? 100 - val : val));
  return (
    <div className="rounded-xl p-3" style={{ background: C.surface, border: `1px solid ${C.grid}` }}>
      <p className="mb-1 text-xs" style={{ color: C.ink2 }}>{title}</p>
      <p className="text-xl font-bold" style={{ color: C.ink }}>{val.toFixed(1)}</p>
      <div className="mt-2 h-1.5 w-full rounded-full" style={{ background: C.grid }}>
        <div className="h-full rounded-full" style={{ width: `${pct}%`, background: col }} />
      </div>
    </div>
  );
}
