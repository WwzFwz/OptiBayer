"use client";
// Primitif umpan-balik kecil: Spinner (dalam tombol), Skeleton (loading),
// EmptyState (kosong informatif). Dipakai lintas halaman utk konsistensi.
import { C } from "@/lib/theme";

/** Spinner mikro — warna mengikuti `currentColor` tombol induk. */
export function Spinner({ size = 13 }: { size?: number }) {
  return (
    <span className="spin" aria-hidden
          style={{ width: size, height: size, verticalAlign: "-2px" }} />
  );
}

/** Balok skeleton shimmer. */
export function Skeleton({ h = 16, w = "100%", className = "" }: {
  h?: number | string; w?: number | string; className?: string;
}) {
  return <div className={`skeleton ${className}`}
              style={{ height: h, width: w }} aria-hidden />;
}

/** Placeholder chart saat memuat — beberapa baris skeleton. */
export function ChartSkeleton({ height = 200 }: { height?: number }) {
  return (
    <div className="flex flex-col justify-end gap-2" style={{ height }}
         role="status" aria-label="Memuat…">
      <Skeleton h="60%" />
      <div className="flex gap-2">
        <Skeleton h={14} w="30%" /><Skeleton h={14} w="20%" /><Skeleton h={14} w="25%" />
      </div>
    </div>
  );
}

/** Empty state: ikon + judul + 1 kalimat + CTA opsional (menggantikan
    kalimat abu-abu polos). */
export function EmptyState({ icon, title, hint, cta }: {
  icon?: React.ReactNode; title: string; hint?: string; cta?: React.ReactNode;
}) {
  return (
    <div className="flex flex-col items-center justify-center gap-2 rounded-lg px-4 py-8 text-center"
         style={{ border: `1px dashed ${C.grid}`, background: C.page }}>
      {icon && <div style={{ color: C.muted }}>{icon}</div>}
      <p className="text-sm font-semibold" style={{ color: C.ink2 }}>{title}</p>
      {hint && <p className="max-w-xs text-xs" style={{ color: C.muted }}>{hint}</p>}
      {cta}
    </div>
  );
}
