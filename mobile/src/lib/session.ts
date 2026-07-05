import * as SecureStore from "expo-secure-store";
import { Platform } from "react-native";

const ACCESS = "access_token";
const REFRESH = "refresh_token";

// expo-secure-store es solo nativo (iOS/Android). En web usamos localStorage.
const isWeb = Platform.OS === "web";

type WebStore = {
  getItem(k: string): string | null;
  setItem(k: string, v: string): void;
  removeItem(k: string): void;
};

function webStore(): WebStore | undefined {
  return (globalThis as any).localStorage as WebStore | undefined;
}

async function setItem(key: string, value: string): Promise<void> {
  if (isWeb) {
    webStore()?.setItem(key, value);
    return;
  }
  await SecureStore.setItemAsync(key, value);
}

async function getItem(key: string): Promise<string | null> {
  if (isWeb) {
    return webStore()?.getItem(key) ?? null;
  }
  return SecureStore.getItemAsync(key);
}

async function deleteItem(key: string): Promise<void> {
  if (isWeb) {
    webStore()?.removeItem(key);
    return;
  }
  await SecureStore.deleteItemAsync(key);
}

export async function saveTokens(access: string, refresh: string): Promise<void> {
  await setItem(ACCESS, access);
  await setItem(REFRESH, refresh);
}

export async function loadTokens(): Promise<{ access: string; refresh: string } | null> {
  const access = await getItem(ACCESS);
  const refresh = await getItem(REFRESH);
  if (!access || !refresh) return null;
  return { access, refresh };
}

export async function clearTokens(): Promise<void> {
  await deleteItem(ACCESS);
  await deleteItem(REFRESH);
}
