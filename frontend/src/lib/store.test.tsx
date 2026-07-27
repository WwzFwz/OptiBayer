import { act, cleanup, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

// API di-mock seluruhnya: yang diuji di sini adalah PERILAKU STORE
// (sinkronisasi URL, pembatalan keputusan saat audit gagal), bukan jaringan.
vi.mock("@/lib/api", () => ({
  getReplay: vi.fn(),
  getHour: vi.fn(),
  catatKeputusan: vi.fn(),
}));

import { catatKeputusan, getHour, getReplay } from "@/lib/api";
import { StoreProvider, useStore } from "./store";

function Probe() {
  const s = useStore();
  return (
    <div>
      <span data-testid="page">{s.page}</span>
      <span data-testid="scenario">{s.scenario}</span>
      <span data-testid="hour">{s.hour}</span>
      <span data-testid="gagal">{s.gagalCatat}</span>
      <span data-testid="api">{s.apiState}</span>
      <span data-testid="pernah-main">{String(s.pernahMain)}</span>
      <button onClick={() => s.setPlaying(true)}>main</button>
      <button onClick={() => s.setPage("redmud")}>ke-redmud</button>
      <button onClick={() => s.setHour(14)}>ke-jam-14</button>
      <button onClick={() => s.decide("k1", "terima", "Silika tinggi")}>putuskan</button>
    </div>
  );
}

function pasang() {
  return render(<StoreProvider><Probe /></StoreProvider>);
}

beforeEach(() => {
  window.history.replaceState(null, "", "/");
  vi.mocked(getReplay).mockResolvedValue({ scenario: "spike", n: 48, hours: [] });
  vi.mocked(getHour).mockResolvedValue(
    { hour: 8, fast: false, kpi: {}, cards: [] } as never);
  vi.mocked(catatKeputusan).mockResolvedValue(undefined);
});
afterEach(cleanup);

describe("sinkronisasi URL", () => {
  it("membaca halaman, skenario, dan jam dari query string", async () => {
    window.history.replaceState(null, "", "/?p=redmud&s=0&h=14");
    pasang();
    await waitFor(() => expect(screen.getByTestId("page").textContent).toBe("redmud"));
    expect(screen.getByTestId("scenario").textContent).toBe("0");
    expect(screen.getByTestId("hour").textContent).toBe("14");
  });

  it("mengabaikan halaman ngawur dan tetap di default", async () => {
    window.history.replaceState(null, "", "/?p=halaman-palsu");
    pasang();
    await waitFor(() => expect(screen.getByTestId("page").textContent).toBe("overview"));
  });

  it("mengabaikan skenario di luar 0/1", async () => {
    window.history.replaceState(null, "", "/?s=99");
    pasang();
    await waitFor(() => expect(screen.getByTestId("scenario").textContent).toBe("1"));
  });

  it("menulis keadaan kembali ke URL supaya bisa dikirim sbg link", async () => {
    pasang();
    await waitFor(() => expect(window.location.search).toContain("p=overview"));
    expect(window.location.search).toContain("s=1");
    expect(window.location.search).toContain("h=8");
  });

  it("ganti halaman menambah riwayat (tombol Back berguna)", async () => {
    pasang();
    await waitFor(() => expect(window.location.search).toContain("p=overview"));
    const sebelum = window.history.length;

    act(() => { screen.getByText("ke-redmud").click(); });
    await waitFor(() => expect(window.location.search).toContain("p=redmud"));
    expect(window.history.length).toBeGreaterThan(sebelum);
  });

  it("geser jam TIDAK membanjiri riwayat", async () => {
    // Slider jam bisa digeser puluhan kali; kalau tiap langkah masuk riwayat,
    // tombol Back jadi tak berguna.
    pasang();
    await waitFor(() => expect(window.location.search).toContain("h=8"));
    const sebelum = window.history.length;

    act(() => { screen.getByText("ke-jam-14").click(); });
    await waitFor(() => expect(window.location.search).toContain("h=14"));
    expect(window.history.length).toBe(sebelum);
  });

  it("tombol Back browser memulihkan keadaan", async () => {
    window.history.replaceState(null, "", "/?p=overview&s=1&h=8");
    pasang();
    await waitFor(() => expect(screen.getByTestId("page").textContent).toBe("overview"));

    act(() => { screen.getByText("ke-redmud").click(); });
    await waitFor(() => expect(screen.getByTestId("page").textContent).toBe("redmud"));

    act(() => {
      window.history.replaceState(null, "", "/?p=overview&s=1&h=8");
      window.dispatchEvent(new PopStateEvent("popstate"));
    });
    await waitFor(() => expect(screen.getByTestId("page").textContent).toBe("overview"));
  });
});

describe("keadaan backend", () => {
  const HOUR_OK = { hour: 8, fast: false, kpi: {}, cards: [] } as never;

  it("menyebut kegagalan pertama 'menyiapkan', BUKAN 'mati'", async () => {
    // Hosting gratis menidurkan container; permintaan pertama pengunjung
    // membangunkannya dan wajar gagal/lambat. Menampilkan "API terputus" merah
    // di detik pertama membuat aplikasi yang sehat dibaca sebagai rusak.
    vi.mocked(getReplay).mockRejectedValue(new Error("cold start"));
    vi.mocked(getHour).mockRejectedValue(new Error("cold start"));
    pasang();
    await waitFor(() =>
      expect(screen.getByTestId("api").textContent).toBe("menyiapkan"));
  });

  it("menyebutnya 'mati' kalau backend PERNAH hidup lalu putus", async () => {
    // Beda kelas dari cold start: ini benar-benar putus di tengah jalan, dan
    // menyamarkannya sebagai "sedang menyiapkan" akan menyesatkan.
    pasang();
    await waitFor(() =>
      expect(screen.getByTestId("api").textContent).toBe("hidup"));

    vi.mocked(getHour).mockRejectedValue(new Error("putus"));
    act(() => { screen.getByText("ke-jam-14").click(); });
    await waitFor(() =>
      expect(screen.getByTestId("api").textContent).toBe("mati"));
  });

  it("mencoba lagi sendiri dan pulih TANPA refresh", async () => {
    // Pengunjung yang mengira aplikasinya rusak tidak akan me-refresh, jadi
    // pemulihan tidak boleh bergantung padanya.
    vi.useFakeTimers();
    try {
      vi.mocked(getReplay).mockRejectedValueOnce(new Error("cold start"));
      vi.mocked(getHour).mockRejectedValueOnce(new Error("cold start"));
      pasang();

      await act(async () => { await vi.advanceTimersByTimeAsync(0); });
      expect(screen.getByTestId("api").textContent).toBe("menyiapkan");

      // lewati jeda percobaan ulang
      await act(async () => { await vi.advanceTimersByTimeAsync(5_000); });
      expect(screen.getByTestId("api").textContent).toBe("hidup");
    } finally {
      vi.useRealTimers();
    }
  });

  it("mencatat pernahMain supaya sorotan ajakan Play padam", async () => {
    vi.mocked(getHour).mockResolvedValue(HOUR_OK);
    pasang();
    await waitFor(() =>
      expect(screen.getByTestId("pernah-main").textContent).toBe("false"));

    act(() => { screen.getByText("main").click(); });
    await waitFor(() =>
      expect(screen.getByTestId("pernah-main").textContent).toBe("true"));
  });
});

describe("keputusan advisory", () => {
  it("mengirim judul kartu ke audit trail, bukan key internal", async () => {
    pasang();
    act(() => { screen.getByText("putuskan").click(); });
    await waitFor(() => expect(catatKeputusan).toHaveBeenCalledWith(
      8, "Silika tinggi", "terima"));
  });

  it("MEMBATALKAN tanda keputusan kalau server gagal mencatat", async () => {
    // Menampilkan "DITERIMA — tercatat" padahal audit gagal jauh lebih
    // berbahaya daripada gagal terang-terangan.
    vi.mocked(catatKeputusan).mockRejectedValueOnce(new Error("401"));
    pasang();
    act(() => { screen.getByText("putuskan").click(); });
    await waitFor(() => expect(screen.getByTestId("gagal").textContent).toBe("1"));
  });
});
