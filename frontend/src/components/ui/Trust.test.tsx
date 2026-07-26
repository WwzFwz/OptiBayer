import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";
import { IntervalBadge, PhysicsTable, TrustBar } from "./Trust";
import type { Interval, Ood, PhysicsCheck } from "@/lib/api";

afterEach(cleanup);

const iv: Interval = { lo: 91.5, hi: 91.9, half: 0.219, level: 0.9, coverage: 0.903 };

describe("IntervalBadge", () => {
  it("menampilkan lebar interval dgn presisi yang diminta", () => {
    render(<IntervalBadge interval={iv} digits={2} />);
    expect(screen.getByText("±0.22")).toBeTruthy();
  });

  it("DIAM kalau model belum punya interval", () => {
    // Lebih baik tidak menampilkan apa pun daripada memasang angka yang
    // tidak pernah dihitung.
    const { container } = render(<IntervalBadge interval={null} />);
    expect(container.textContent).toBe("");
  });
});

describe("TrustBar", () => {
  const oodBersih: Ood = {
    ok: true, n_out: 0, labels: [], komposisi_total_pct: 100,
    komposisi_wajar: true, alasan: [],
  };
  const fisikaCocok: PhysicsCheck = {
    ok: true, gagal_label: [],
    rows: [{ target: "recovery_pct", label: "Recovery Al (%)", ml: 91.7,
             fisika: 91.6, selisih: 0.1, tol: 0.44, ok: true }],
  };

  it("hijau & menenangkan saat semua pemeriksaan lolos", () => {
    render(<TrustBar ood={oodBersih} physics={fisikaCocok} />);
    expect(screen.getByText(/dalam rentang data latih/i)).toBeTruthy();
  });

  it("menyuarakan alasan ekstrapolasi apa adanya", () => {
    const ood: Ood = {
      ...oodBersih, ok: false, n_out: 1,
      alasan: ["1 fitur di luar rentang data latih"],
    };
    render(<TrustBar ood={ood} />);
    expect(screen.getByText(/Ekstrapolasi/)).toBeTruthy();
    expect(screen.getByText(/1 fitur di luar rentang/)).toBeTruthy();
  });

  it("menyebut target mana yang tidak disepakati fisika", () => {
    const fisika: PhysicsCheck = {
      ...fisikaCocok, ok: false, gagal_label: ["Total OPEX (/jam)"],
    };
    render(<TrustBar ood={oodBersih} physics={fisika} />);
    expect(screen.getByText(/Total OPEX/)).toBeTruthy();
  });

  it("tidak merender apa pun kalau tak ada data — jangan bikin bising", () => {
    const { container } = render(<TrustBar />);
    expect(container.firstChild).toBeNull();
  });

  it("physics dgn rows kosong tidak dianggap gagal", () => {
    // Mode Play melewati optimizer; rows kosong berarti 'belum diperiksa',
    // bukan 'tidak sepakat'.
    render(<TrustBar ood={oodBersih} physics={{ ok: false, gagal_label: [], rows: [] }} />);
    expect(screen.getByText(/dalam rentang data latih/i)).toBeTruthy();
  });
});

describe("PhysicsTable", () => {
  it("menyandingkan angka ML dan neraca massa", () => {
    const physics: PhysicsCheck = {
      ok: true, gagal_label: [],
      rows: [{ target: "total_opex", label: "Total OPEX (/jam)", ml: 19903,
               fisika: 20944, selisih: -1041, tol: 2919, ok: true }],
    };
    render(<PhysicsTable physics={physics} />);
    expect(screen.getByText("Total OPEX (/jam)")).toBeTruthy();
    // kolom header ML & fisika berdampingan, plus catatan kaki di bawahnya
    expect(screen.getByRole("columnheader", { name: /neraca massa/i })).toBeTruthy();
    expect(screen.getByRole("columnheader", { name: /surrogate ml/i })).toBeTruthy();
  });

  it("diam saat tidak ada hasil pemeriksaan", () => {
    const { container } = render(<PhysicsTable />);
    expect(container.firstChild).toBeNull();
  });
});
