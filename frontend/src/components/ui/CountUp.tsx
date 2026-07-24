"use client";
// Angka beranimasi (count-up) — menegaskan PERUBAHAN nilai saat ganti jam.
// requestAnimationFrame, easing halus, ~420ms. Menghormati reduced-motion
// (langsung ke nilai akhir). `format` mengubah angka -> string tampilan.
import { useEffect, useRef, useState } from "react";

const DUR = 420;
const easeOut = (t: number) => 1 - Math.pow(1 - t, 3);

const reduced = () =>
  typeof window !== "undefined" &&
  window.matchMedia?.("(prefers-reduced-motion: reduce)").matches;

export default function CountUp({ value, format }: {
  value: number; format: (v: number) => string;
}) {
  const [disp, setDisp] = useState(value);
  const from = useRef(value);
  const raf = useRef<number>(0);

  useEffect(() => {
    // sinkronisasi angka tampil dgn jam paint browser (requestAnimationFrame)
    // — ini justru kegunaan sah useEffect ("subscribe to external system").
    // eslint-disable-next-line react-hooks/set-state-in-effect
    if (reduced()) { setDisp(value); return; }
    const start = performance.now();
    const a = from.current, b = value;
    const tick = (now: number) => {
      const t = Math.min(1, (now - start) / DUR);
      setDisp(a + (b - a) * easeOut(t));
      if (t < 1) raf.current = requestAnimationFrame(tick);
      else from.current = b;
    };
    cancelAnimationFrame(raf.current);
    raf.current = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf.current);
  }, [value]);

  return <>{format(disp)}</>;
}
