import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";
import { fileURLToPath } from "node:url";

// Tes frontend: sebelumnya NOL. CI hanya menjaga tsc + eslint + build, jadi
// logika seperti sinkronisasi URL dan tampilan kepercayaan tidak terjaga sama
// sekali. DOM sungguhan dipakai supaya komponen benar-benar dirender, bukan
// cuma diperiksa tipenya.
//
// happy-dom, bukan jsdom: rantai dependensi CSS jsdom (@asamuzakjp/css-color ->
// @csstools/css-calc) memuat ESM lewat require() dan meledak ERR_REQUIRE_ESM di
// Node yang terpasang di sini.
export default defineConfig({
  plugins: [react()],
  test: {
    environment: "happy-dom",
    globals: true,
    include: ["src/**/*.test.{ts,tsx}"],
    // CATATAN: `restoreMocks` sengaja TIDAK dipakai. Ia memulihkan mock
    // sebelum SETIAP tes, termasuk implementasi yang dipasang di dalam factory
    // `vi.mock(...)` saat modul dievaluasi — akibatnya fungsi API mock berubah
    // jadi undefined dan store gagal di `.then`. Tiap berkas tes mengatur
    // ulang mock-nya sendiri di `beforeEach`.
  },
  resolve: {
    alias: {
      "@": fileURLToPath(new URL("./src", import.meta.url)),
    },
  },
});
