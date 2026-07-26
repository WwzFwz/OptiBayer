"use client";
// Tampilan "seberapa boleh dipercaya angka ini" — satu bahasa visual dipakai
// di KPI, Advisory, dan Prediction Lab.
//
// Tiga sinyal, sengaja dibedakan karena artinya berbeda:
//   1. Interval konformal  — lebar ketidakpastian model (±, dgn cakupan teruji)
//   2. Guard OOD           — apakah titik operasi masih di wilayah data latih
//   3. Wasit fisika        — apakah neraca massa deterministik setuju
import { ShieldCheck, ShieldAlert, TriangleAlert } from "lucide-react";
import { Interval, Ood, PhysicsCheck } from "@/lib/api";
import { C } from "@/lib/theme";

/** "±0,22" — lebar interval di bawah sebuah angka KPI. */
export function IntervalBadge({
  interval, digits = 2, suffix = "",
}: { interval?: Interval | null; digits?: number; suffix?: string }) {
  if (!interval) return null;
  return (
    <span
      className="text-[0.68rem] tabular-nums"
      style={{ color: C.muted }}
      title={`Interval konformal ${(interval.level * 100).toFixed(0)}% — `
           + `rentang ${interval.lo.toFixed(digits)} s/d ${interval.hi.toFixed(digits)}. `
           + `Dihitung dari residual validasi silang, bukan taksiran.`}
    >
      ±{interval.half.toFixed(digits)}{suffix}
    </span>
  );
}

/** Strip ringkas: status OOD + kesepakatan fisika. Diam kalau tak ada data. */
export function TrustBar({
  ood, physics, className = "",
}: { ood?: Ood; physics?: PhysicsCheck; className?: string }) {
  if (!ood && !physics) return null;

  const oodBermasalah = ood && !ood.ok;
  const fisikaBermasalah = physics && physics.rows?.length > 0 && !physics.ok;
  const aman = !oodBermasalah && !fisikaBermasalah;

  const warna = aman ? C.status.good
    : oodBermasalah ? C.status.critical : C.status.warning;
  const Icon = aman ? ShieldCheck : oodBermasalah ? ShieldAlert : TriangleAlert;

  const pesan = aman
    ? "Dalam rentang data latih · cocok dengan neraca massa"
    : [
        oodBermasalah ? `Ekstrapolasi: ${ood!.alasan.join("; ")}` : null,
        fisikaBermasalah
          ? `Surrogate menyimpang dari neraca massa pada ${physics!.gagal_label.join(", ")}`
          : null,
      ].filter(Boolean).join(" · ");

  return (
    <div
      className={`flex items-start gap-2 rounded-lg px-2.5 py-1.5 text-xs ${className}`}
      style={{ background: `${warna}18`, color: warna, border: `1px solid ${warna}44` }}
    >
      <Icon size={14} className="mt-px shrink-0" />
      <span>{pesan}</span>
    </div>
  );
}

/** Tabel perbandingan ML vs fisika — dipakai di Lab & panel detail. */
export function PhysicsTable({ physics }: { physics?: PhysicsCheck }) {
  if (!physics?.rows?.length) return null;
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-xs tabular-nums">
        <thead>
          <tr style={{ color: C.muted }}>
            <th className="py-1 pr-2 text-left font-semibold">Target</th>
            <th className="py-1 pr-2 text-right font-semibold">Surrogate ML</th>
            <th className="py-1 pr-2 text-right font-semibold">Neraca massa</th>
            <th className="py-1 text-right font-semibold">Selisih</th>
          </tr>
        </thead>
        <tbody>
          {physics.rows.map((r) => (
            <tr key={r.target} style={{ borderTop: `1px solid ${C.grid}` }}>
              <td className="py-1 pr-2" style={{ color: C.ink2 }}>{r.label}</td>
              <td className="py-1 pr-2 text-right" style={{ color: C.ink2 }}>
                {r.ml.toLocaleString("id-ID", { maximumFractionDigits: 2 })}
              </td>
              <td className="py-1 pr-2 text-right" style={{ color: C.ink }}>
                {r.fisika.toLocaleString("id-ID", { maximumFractionDigits: 2 })}
              </td>
              <td className="py-1 text-right"
                  style={{ color: r.ok ? C.muted : C.status.warning }}>
                {r.selisih > 0 ? "+" : ""}
                {r.selisih.toLocaleString("id-ID", { maximumFractionDigits: 2 })}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      <p className="mt-1 text-[0.68rem]" style={{ color: C.muted }}>
        Angka neraca massa adalah hasil kalkulator deterministik (port formula
        workbook). Bila keduanya berselisih jauh, yang dipakai adalah neraca massa.
      </p>
    </div>
  );
}
