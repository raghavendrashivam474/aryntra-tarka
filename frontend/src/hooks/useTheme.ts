// frontend/src/hooks/useTheme.ts
// Sprint 3.21.1 — Theme system.
// Single source of truth for theme state across the application.
//
// Responsibilities:
//   - Read saved theme from localStorage on first load
//   - Apply dark/light class to document.documentElement immediately
//   - Write to localStorage on every change
//   - React to OS preference changes when theme is set to 'system'
//
// Usage:
//   const { theme, setTheme, toggleTheme } = useTheme()

import { useState, useEffect, useCallback } from "react";

export type Theme = "dark" | "light" | "system";

const STORAGE_KEY = "tarka_theme";

// ── Resolve 'system' to an actual applied theme ──────────────────────────────
function resolveEffective(theme: Theme): "dark" | "light" {
  if (theme === "system") {
    return window.matchMedia("(prefers-color-scheme: dark)").matches
      ? "dark"
      : "light";
  }
  return theme;
}

// ── Apply theme class to <html> element ──────────────────────────────────────
// Tailwind reads the 'dark' class on document.documentElement.
// darkMode: 'class' is confirmed set in tailwind.config.js.
function applyToDocument(theme: Theme): void {
  const effective = resolveEffective(theme);
  const root      = document.documentElement;
  root.classList.toggle("dark",  effective === "dark");
  root.classList.toggle("light", effective === "light");
}

// ── Read stored theme from localStorage ──────────────────────────────────────
function readStored(): Theme {
  try {
    const stored = localStorage.getItem(STORAGE_KEY);
    if (stored === "dark" || stored === "light" || stored === "system") {
      return stored;
    }
  } catch {
    // localStorage blocked (private browsing, permissions, etc.)
  }
  return "dark"; // Default: dark
}

// ── Hook ─────────────────────────────────────────────────────────────────────
export function useTheme() {
  const [theme, setThemeState] = useState<Theme>(readStored);

  // Apply to document whenever theme changes
  useEffect(() => {
    applyToDocument(theme);
  }, [theme]);

  // When theme is 'system', listen for OS preference changes
  useEffect(() => {
    if (theme !== "system") return;
    const mq      = window.matchMedia("(prefers-color-scheme: dark)");
    const handler = () => applyToDocument("system");
    mq.addEventListener("change", handler);
    return () => mq.removeEventListener("change", handler);
  }, [theme]);

  // Persist and apply new theme
  const setTheme = useCallback((next: Theme) => {
    try {
      localStorage.setItem(STORAGE_KEY, next);
    } catch {
      // Silent — UI still works, just won't persist
    }
    setThemeState(next);
  }, []);

  // Quick toggle between dark and light only
  const toggleTheme = useCallback(() => {
    setTheme(theme === "light" ? "dark" : "light");
  }, [theme, setTheme]);

  return { theme, setTheme, toggleTheme };
}