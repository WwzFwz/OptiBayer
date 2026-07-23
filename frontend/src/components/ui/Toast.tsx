"use client";
// Sistem toast ringan — umpan balik aksi (Terima/Tolak advisory, simpan
// Knowledge) yang sekarang cuma teks kecil mudah kelewat. Auto-hilang 3.2s,
// bisa ditutup manual, aria-live utk pembaca layar.
import {
  createContext, useCallback, useContext, useState,
} from "react";
import { Check, Info, TriangleAlert, X } from "lucide-react";
import { C } from "@/lib/theme";

type Kind = "success" | "error" | "info";
type Toast = { id: number; kind: Kind; msg: string };

const Ctx = createContext<(kind: Kind, msg: string) => void>(() => {});

/** Panggil `toast("success", "Advisory diterima")` dari komponen mana pun. */
export function useToast() {
  return useContext(Ctx);
}

const ICON: Record<Kind, React.ReactNode> = {
  success: <Check size={15} />,
  error: <TriangleAlert size={15} />,
  info: <Info size={15} />,
};
const COLOR: Record<Kind, string> = {
  success: C.status.good, error: C.status.critical, info: C.accent,
};

export function ToastProvider({ children }: { children: React.ReactNode }) {
  const [items, setItems] = useState<Toast[]>([]);

  const push = useCallback((kind: Kind, msg: string) => {
    const id = Date.now() + Math.random();
    setItems((p) => [...p, { id, kind, msg }]);
    setTimeout(() => setItems((p) => p.filter((t) => t.id !== id)), 3200);
  }, []);

  const close = (id: number) => setItems((p) => p.filter((t) => t.id !== id));

  return (
    <Ctx.Provider value={push}>
      {children}
      <div className="pointer-events-none fixed bottom-4 right-4 z-[60] flex flex-col gap-2"
           aria-live="polite" aria-atomic="false">
        {items.map((t) => (
          <div key={t.id}
               className="toast-in pointer-events-auto flex items-center gap-2 rounded-lg px-3 py-2 text-sm shadow-lg"
               style={{ background: C.surface, border: `1px solid ${COLOR[t.kind]}`,
                        color: C.ink, minWidth: 220, maxWidth: 340 }}>
            <span style={{ color: COLOR[t.kind] }}>{ICON[t.kind]}</span>
            <span className="flex-1">{t.msg}</span>
            <button onClick={() => close(t.id)} aria-label="Tutup notifikasi"
                    style={{ color: C.muted }}>
              <X size={14} />
            </button>
          </div>
        ))}
      </div>
    </Ctx.Provider>
  );
}
