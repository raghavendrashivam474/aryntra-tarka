// frontend/src/components/TopBar.tsx
// Sprint 3.20.1 - Added Command Center link
import React from "react";
import { Link } from "react-router-dom";
import { Menu, Zap } from "lucide-react";

interface TopBarProps {
  onToggleSidebar: () => void;
  isMobile: boolean;
}

export const TopBar: React.FC<TopBarProps> = ({ onToggleSidebar, isMobile }) => {
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
        {/* Command Center Button */}
        <Link
          to="/command-center"
          className="
            flex items-center gap-2
            px-3 py-1.5 rounded-md
            bg-gradient-to-r from-indigo-600/20 to-purple-600/20
            hover:from-indigo-600/30 hover:to-purple-600/30
            border border-indigo-500/30 hover:border-indigo-400
            text-indigo-200 hover:text-white
            text-xs font-medium
            transition-all
          "
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
