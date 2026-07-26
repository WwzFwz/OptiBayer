import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { catatKeputusan, getAudit, getHour, getReplay } from "./api";

function mockFetch(body: unknown, ok = true, status = 200) {
  const f = vi.fn().mockResolvedValue({
    ok, status, json: async () => body,
  });
  vi.stubGlobal("fetch", f);
  return f;
}

beforeEach(() => vi.unstubAllGlobals());

describe("klien REST", () => {
  it("getReplay memanggil path skenario yang benar", async () => {
    const f = mockFetch({ n: 0, hours: [] });
    await getReplay(1);
    expect(f.mock.calls[0][0]).toContain("/v1/replay/1");
  });

  it("getHour meneruskan flag fast — penentu jalur ringan saat mode Play", async () => {
    const f = mockFetch({});
    await getHour(1, 8, true);
    expect(f.mock.calls[0][0]).toContain("/v1/replay/1/hour/8?fast=true");

    await getHour(0, 3, false);
    expect(f.mock.calls[1][0]).toContain("/v1/replay/0/hour/3?fast=false");
  });

  it("membuang cache supaya angka jam tidak basi", async () => {
    const f = mockFetch({});
    await getReplay(0);
    expect(f.mock.calls[0][1]).toMatchObject({ cache: "no-store" });
  });

  it("melempar kalau server menjawab error", async () => {
    mockFetch({}, false, 500);
    await expect(getReplay(0)).rejects.toThrow(/500/);
  });
});

describe("alamat backend", () => {
  afterEach(() => {
    delete window.__OPTIBAYER_API__;
    vi.resetModules();
  });

  it("memakai suntikan runtime kalau ada — kunci satu image untuk banyak env", async () => {
    // Tanpa ini, URL backend terkunci saat build dan image produksi tidak bisa
    // diarahkan ulang tanpa build ulang (masalah nyata saat deploy).
    window.__OPTIBAYER_API__ = "https://api.contoh.id";
    vi.resetModules();
    const segar = await import("./api");
    expect(segar.API).toBe("https://api.contoh.id");
  });

  it("jatuh ke default lokal kalau tidak ada suntikan", async () => {
    delete window.__OPTIBAYER_API__;
    vi.resetModules();
    const segar = await import("./api");
    expect(segar.API).toBe("http://localhost:8000");
  });
});

describe("catatKeputusan (audit trail)", () => {
  it("mengirim POST berisi jam, judul, keputusan, dan asal", async () => {
    const f = mockFetch({ ok: true });
    await catatKeputusan(12, "Silika reaktif tinggi", "terima");

    const [url, opsi] = f.mock.calls[0];
    expect(url).toContain("/v1/audit/decision");
    expect(opsi.method).toBe("POST");
    expect(JSON.parse(opsi.body)).toEqual({
      hour: 12, title: "Silika reaktif tinggi",
      decision: "terima", sumber: "react",
    });
  });

  it("MELEMPAR saat server menolak — pemanggil wajib bisa membatalkan", async () => {
    // Kalau kegagalan ditelan diam-diam, UI akan bilang "tercatat di audit"
    // padahal tidak ada apa pun yang tersimpan.
    mockFetch({}, false, 401);
    await expect(catatKeputusan(1, "x", "tolak")).rejects.toThrow(/401/);
  });

  it("getAudit meneruskan limit", async () => {
    const f = mockFetch({ n_total: 0, decisions: [] });
    await getAudit(5);
    expect(f.mock.calls[0][0]).toContain("limit=5");
  });
});
