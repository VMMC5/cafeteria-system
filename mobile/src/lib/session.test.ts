jest.mock("expo-secure-store", () => ({
  getItemAsync: jest.fn(),
  setItemAsync: jest.fn(),
  deleteItemAsync: jest.fn(),
}));
jest.mock("react-native", () => ({ Platform: { OS: "web" } }));

import { clearTokens, loadTokens, saveTokens } from "./session";

describe("session en web (localStorage)", () => {
  beforeEach(() => {
    const store: Record<string, string> = {};
    (globalThis as any).localStorage = {
      getItem: (k: string) => (k in store ? store[k] : null),
      setItem: (k: string, v: string) => {
        store[k] = v;
      },
      removeItem: (k: string) => {
        delete store[k];
      },
    };
  });

  test("guarda y carga tokens", async () => {
    await saveTokens("a", "r");
    expect(await loadTokens()).toEqual({ access: "a", refresh: "r" });
  });

  test("loadTokens devuelve null sin tokens", async () => {
    expect(await loadTokens()).toBeNull();
  });

  test("clearTokens los borra", async () => {
    await saveTokens("a", "r");
    await clearTokens();
    expect(await loadTokens()).toBeNull();
  });
});
