import { create } from "zustand";

import * as client from "../api/client";
import { clearTokens, loadTokens, saveTokens } from "../lib/session";

type Status = "loading" | "auth" | "noauth";

type AuthState = {
  status: Status;
  user: client.Usuario | null;
  accessToken: string | null;
  refreshToken: string | null;
  bootstrap: () => Promise<void>;
  login: (correo: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
};

export const useAuth = create<AuthState>((set) => ({
  status: "loading",
  user: null,
  accessToken: null,
  refreshToken: null,

  bootstrap: async () => {
    const tokens = await loadTokens();
    if (!tokens) {
      set({ status: "noauth" });
      return;
    }
    try {
      const user = await client.getMe(tokens.access);
      set({
        status: "auth",
        user,
        accessToken: tokens.access,
        refreshToken: tokens.refresh,
      });
    } catch {
      try {
        const nt = await client.refresh(tokens.refresh);
        await saveTokens(nt.access_token, nt.refresh_token);
        const user = await client.getMe(nt.access_token);
        set({
          status: "auth",
          user,
          accessToken: nt.access_token,
          refreshToken: nt.refresh_token,
        });
      } catch {
        await clearTokens();
        set({ status: "noauth", user: null, accessToken: null, refreshToken: null });
      }
    }
  },

  login: async (correo, password) => {
    const t = await client.login(correo, password);
    await saveTokens(t.access_token, t.refresh_token);
    const user = await client.getMe(t.access_token);
    set({
      status: "auth",
      user,
      accessToken: t.access_token,
      refreshToken: t.refresh_token,
    });
  },

  logout: async () => {
    await clearTokens();
    set({ status: "noauth", user: null, accessToken: null, refreshToken: null });
  },
}));
