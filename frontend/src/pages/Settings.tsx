// frontend/src/pages/Settings.tsx
// Sprint 3.21.1 — Theme buttons wired to useTheme hook.
//                 Theme selection now persists and applies immediately.
//                 Removed local useState('dark') that did nothing.

import React, { useState } from 'react'
import {
  Settings as SettingsIcon,
  Trash2,
  Info,
  Moon,
  Sun,
  Monitor,
  ChevronRight,
  AlertTriangle,
} from 'lucide-react'
import { APP_VERSION, BUILD_DATE } from '../constants/version'
import { AboutDialog }    from '../components/AboutDialog'
import { useConversations } from '../hooks/useConversations'
import { useTheme }       from '../hooks/useTheme'
import type { Theme }     from '../hooks/useTheme'

const THEMES: { value: Theme; label: string; icon: React.ReactNode }[] = [
  { value: 'dark',   label: 'Dark',   icon: <Moon    size={16} /> },
  { value: 'light',  label: 'Light',  icon: <Sun     size={16} /> },
  { value: 'system', label: 'System', icon: <Monitor size={16} /> },
]

export const SettingsPage: React.FC = () => {
  // Sprint 3.21.1 — reads and writes shared theme state
  // Previously: useState('dark') — local only, did nothing to the UI
  const { theme, setTheme }         = useTheme()
  const [showAbout,    setShowAbout] = useState(false)
  const [confirmClear, setConfirm]  = useState(false)
  const { clearAllConversations }   = useConversations()

  const handleClearAll = () => {
    if (confirmClear) {
      clearAllConversations()
      setConfirm(false)
    } else {
      setConfirm(true)
    }
  }

  return (
    <div className="
      flex flex-col items-center
      h-full overflow-y-auto
      px-4 py-8
      bg-surface-950
    ">
      <div className="w-full max-w-lg animate-fade-in">

        {/* Header */}
        <div className="flex items-center gap-3 mb-8">
          <div className="
            w-9 h-9 rounded-xl
            bg-brand-500/15 border border-brand-500/25
            flex items-center justify-center
          ">
            <SettingsIcon size={18} className="text-brand-400" />
          </div>
          <div>
            <h1 className="text-lg font-semibold text-white">Settings</h1>
            <p className="text-xs text-white/40">Configure your Tarka experience</p>
          </div>
        </div>

        {/* ── Appearance ── */}
        <Section title="Appearance">
          <div className="p-4">
            <p className="text-sm text-white/60 mb-3">Theme</p>
            <div className="flex gap-2">
              {THEMES.map((t) => (
                <button
                  key={t.value}
                  onClick={() => setTheme(t.value)}
                  className={`
                    flex items-center gap-2
                    px-4 py-2 rounded-lg text-sm
                    border transition-all duration-150
                    ${theme === t.value
                      ? 'bg-brand-500/20 border-brand-500/50 text-brand-400'
                      : 'bg-white/4 border-white/8 text-white/50 hover:text-white/80 hover:border-white/20'
                    }
                  `}
                >
                  {t.icon}
                  {t.label}
                </button>
              ))}
            </div>
            <p className="text-xs text-white/30 mt-3">
              Theme is saved automatically and applied on next visit.
            </p>
          </div>
        </Section>

        {/* ── Data ── */}
        <Section title="Data">
          <SettingsRow
            icon={<Trash2 size={16} className="text-red-400" />}
            label="Clear all conversations"
            description="Permanently delete all conversation history"
            danger
          >
            <button
              onClick={handleClearAll}
              className={`
                px-4 py-1.5 rounded-lg text-sm font-medium
                border transition-all duration-150
                ${confirmClear
                  ? 'bg-red-500/20 border-red-500/50 text-red-400 hover:bg-red-500/30'
                  : 'bg-white/6 border-white/10 text-white/60 hover:text-white/90 hover:border-white/20'
                }
              `}
            >
              {confirmClear ? (
                <span className="flex items-center gap-1.5">
                  <AlertTriangle size={14} />
                  Confirm
                </span>
              ) : 'Clear all'}
            </button>
          </SettingsRow>
        </Section>

        {/* ── About ── */}
        <Section title="About">
          <SettingsRow
            icon={<Info size={16} className="text-brand-400" />}
            label="About Aryntra Tarka"
            description={`Version ${APP_VERSION} · Built ${BUILD_DATE}`}
          >
            <button
              onClick={() => setShowAbout(true)}
              className="
                p-1.5 rounded-lg
                text-white/40 hover:text-white/80
                hover:bg-white/8
                transition-colors
              "
            >
              <ChevronRight size={16} />
            </button>
          </SettingsRow>
        </Section>

      </div>

      {showAbout && <AboutDialog onClose={() => setShowAbout(false)} />}
    </div>
  )
}

/* ── Sub-components ── */

const Section: React.FC<{ title: string; children: React.ReactNode }> = ({ title, children }) => (
  <div className="mb-6">
    <p className="
      text-xs font-semibold uppercase tracking-widest
      text-white/30 mb-2 px-1
    ">
      {title}
    </p>
    <div className="
      rounded-xl border border-white/8
      bg-surface-900
      overflow-hidden
      divide-y divide-white/5
    ">
      {children}
    </div>
  </div>
)

interface SettingsRowProps {
  icon:        React.ReactNode
  label:       string
  description: string
  danger?:     boolean
  children?:   React.ReactNode
}

const SettingsRow: React.FC<SettingsRowProps> = ({ icon, label, description, children }) => (
  <div className="flex items-center justify-between gap-4 p-4">
    <div className="flex items-start gap-3 min-w-0">
      <div className="mt-0.5 shrink-0">{icon}</div>
      <div className="min-w-0">
        <p className="text-sm text-white/80">{label}</p>
        <p className="text-xs text-white/40 mt-0.5 leading-snug">{description}</p>
      </div>
    </div>
    {children && (
      <div className="shrink-0">{children}</div>
    )}
  </div>
)