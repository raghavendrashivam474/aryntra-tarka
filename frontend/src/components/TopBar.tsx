// frontend/src/components/TopBar.tsx
import React from 'react'
import { Menu, Settings, Cpu } from 'lucide-react'
import { Link } from 'react-router-dom'
import { APP_VERSION } from '../constants/version'

interface TopBarProps {
  onToggleSidebar: () => void
  isMobile:        boolean
}

export const TopBar: React.FC<TopBarProps> = ({ onToggleSidebar, isMobile }) => {
  return (
    <header className="
      flex items-center justify-between
      h-14 px-4
      bg-surface-900/80 backdrop-blur-md
      border-b border-white/5
      shrink-0 z-30
    ">
      {/* Left — hamburger on mobile */}
      <div className="flex items-center gap-3">
        {isMobile && (
          <button
            onClick={onToggleSidebar}
            aria-label="Open sidebar"
            className="
              p-2 rounded-lg
              text-white/60 hover:text-white
              hover:bg-white/8
              transition-colors
            "
          >
            <Menu size={20} />
          </button>
        )}

        {/* Brand */}
        <Link to="/" className="flex items-center gap-2 select-none">
          <div className="
            w-7 h-7 rounded-lg
            bg-brand-500 flex items-center justify-center
          ">
            <Cpu size={14} className="text-white" />
          </div>
          <span className="font-semibold text-sm tracking-wide text-white">
            Aryntra Tarka
          </span>
          <span className="
            hidden sm:inline-block
            text-xs text-white/30 font-mono
            ml-1
          ">
            v{APP_VERSION}
          </span>
        </Link>
      </div>

      {/* Right — Settings */}
      <div className="flex items-center gap-2">
        <Link
          to="/settings"
          aria-label="Settings"
          className="
            p-2 rounded-lg
            text-white/60 hover:text-white
            hover:bg-white/8
            transition-colors
          "
        >
          <Settings size={18} />
        </Link>
      </div>
    </header>
  )
}