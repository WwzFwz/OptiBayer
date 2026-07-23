"use client";
// Sistem tombol terpusat — satu sumber gaya untuk SEMUA tombol aksi.
// variant: primary (emas keemasan, aksi utama) · ghost (outline netral) ·
// success/danger (Terima/Tolak). Radius lembut konsisten (rounded-lg).
import { C } from "@/lib/theme";

type Variant = "primary" | "ghost" | "success" | "danger";
type Size = "sm" | "md";

export default function Button({
  children, onClick, variant = "primary", size = "md", disabled, active,
  full, title, className = "",
}: {
  children: React.ReactNode;
  onClick?: () => void;
  variant?: Variant;
  size?: Size;
  disabled?: boolean;
  active?: boolean;   // untuk toggle (mis. tombol lapisan/dock terpilih)
  full?: boolean;
  title?: string;
  className?: string;
}) {
  const pad = size === "sm" ? "px-2.5 py-1 text-xs" : "px-3.5 py-2 text-sm";
  // variant terisi (primary/success) dpt efek angkat; ghost/danger cukup halus
  const lift = variant === "primary" || variant === "success" ? "btn-lift " : "";
  const base =
    `inline-flex items-center justify-center gap-1.5 rounded-lg font-semibold ` +
    `disabled:opacity-40 disabled:cursor-not-allowed ` +
    `${lift}${full ? "w-full " : ""}${pad} ${className}`;

  const style: React.CSSProperties =
    variant === "primary"
      ? { background: C.accent, color: "#1a1408", border: `1px solid ${C.accent}` }
    : variant === "success"
      ? { background: C.status.good, color: "#fff", border: `1px solid ${C.status.good}` }
    : variant === "danger"
      ? { background: "transparent", color: C.status.critical,
          border: `1px solid ${C.status.critical}` }
    : // ghost / toggle
      { background: active ? `${C.accent}22` : "transparent",
        color: active ? C.ink : C.ink2,
        border: `1px solid ${active ? C.accent : C.grid}` };

  return (
    <button onClick={onClick} disabled={disabled} title={title}
            className={base} style={style}>
      {children}
    </button>
  );
}
