import { useEffect, useState } from "react";
import { branding } from "../branding";
import type { ThemePreference } from "../branding/types";

export type { ThemePreference };

const STORAGE_KEY = "theme-preference";

function applyTheme(preference: ThemePreference) {
  const root = document.documentElement;
  if (preference === "system") {
    root.removeAttribute("data-theme");
  } else {
    root.setAttribute("data-theme", preference);
  }
}

function readStoredPreference(): ThemePreference {
  const stored = localStorage.getItem(STORAGE_KEY);
  if (stored === "light" || stored === "dark" || stored === "system") return stored;
  return branding.defaultTheme ?? "system";
}

export function useTheme() {
  const [preference, setPreference] = useState<ThemePreference>(() => readStoredPreference());

  useEffect(() => {
    applyTheme(preference);
    localStorage.setItem(STORAGE_KEY, preference);
  }, [preference]);

  return { preference, setPreference };
}
