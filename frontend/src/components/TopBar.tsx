// frontend/src/components/TopBar.tsx
// Sprint 3.21.1 — Theme toggle + Settings link added.

import React from "react";
import { Link } from "react-router-dom";
import { Menu, Zap, Moon, Sun, Monitor, Settings } from "lucide-react";
import type { Theme } from "../hooks/useTheme";

interface TopBarProps {
  onToggleSidebar: () => void;
  isMobile:        boolean;
  theme:           Theme;
  onToggleTheme:   () => void;
  onSetTheme:      (theme: Theme) => void;
}

export const TopBar: React.FC<TopBarProps> = ({
  onToggleSidebar,
  isMobile,
  theme,
  onToggleTheme,
}) => {

  const ThemeIcon =
    theme === "light"  ? Sun     :
    theme === "system" ? Monitor :
                         Moon;

  return (
    <header className="flex items-center justify-between h-14 px-4 bg-surface-900 border-b border-white/5 shrink-0">

      {/* Left */}
      <div className="flex items-center gap-3">
        {isMobile && (
          <button
            onClick={onToggleSidebar}
            className="p-2 rounded-md hover:bg-white/5 text-white/70"
            aria-label="Toggle sidebar"
          >
            <Menu size={20} />
          </button>
        )}
        <Link to="/" className="flex items-center gap-2 text-white/90">
          <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center">
            <span className="text-sm font-bold">A</span>
          </div>
          <div>
            <div className="text-sm font-semibold leading-tight">Aryntra Tarka</div>
            <div className="text-[10px] text-white/40 leading-tight">v1.0.0</div>
          </div>
        </Link>
      </div>

      {/* Right */}
      <div className="flex items-center gap-2">

        {/* Theme toggle */}
        <button
          onClick={onToggleTheme}
          className="p-2 rounded-md text-white/50 hover:text-white/90 hover:bg-white/5 transition-colors duration-150"
          aria-label={`Current theme: ${theme}. Click to toggle.`}
          title={`Theme: ${theme}`}
        >
          <ThemeIcon size={18} />
        </button>

        {/* Settings link */}
        <Link
          to="/settings"
          className="p-2 rounded-md text-white/50 hover:text-white/90 hover:bg-white/5 transition-colors duration-150"
          title="Settings"
          aria-label="Open Settings"
        >
          <Settings size={18} />
        </Link>

        {/* Command Center link */}
        <Link
          to="/command-center"
          className="flex items-center gap-2 px-3 py-1.5 rounded-md bg-gradient-to-r from-indigo-600/20 to-purple-600/20 hover:from-indigo-600/30 hover:to-purple-600/30 border border-indigo-500/30 hover:border-indigo-400 text-indigo-200 hover:text-white text-xs font-medium transition-all duration-150"
          title="Open Command Center"
        >
          <Zap size={14} />
          <span className="hidden sm:inline">Command Center</span>
        </Link>

      </div>
    </header>
  );
};

export default TopBar;
