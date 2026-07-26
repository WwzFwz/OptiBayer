import { describe, expect, it } from "vitest";
import { isPageId, PAGE_IDS } from "./pages";

describe("isPageId", () => {
  it("menerima semua id halaman yang terdaftar", () => {
    for (const id of PAGE_IDS) expect(isPageId(id)).toBe(true);
  });

  it("menolak nilai asing — ini penjaga URL dari luar", () => {
    // URL bisa diisi siapa saja; kalau validasi bocor, Shell akan merender
    // halaman yang tidak ada dan layar jadi kosong tanpa penjelasan.
    for (const jahat of ["", "overview ", "OVERVIEW", "../etc", "<script>"]) {
      expect(isPageId(jahat)).toBe(false);
    }
  });

  it("menolak null/undefined", () => {
    expect(isPageId(null)).toBe(false);
    expect(isPageId(undefined)).toBe(false);
  });

  it("daftar halaman tidak punya duplikat", () => {
    expect(new Set(PAGE_IDS).size).toBe(PAGE_IDS.length);
  });
});
