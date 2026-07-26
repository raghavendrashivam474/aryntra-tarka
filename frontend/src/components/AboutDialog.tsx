// frontend/src/components/AboutDialog.tsx
import React from 'react'
import { X, Cpu, Heart } from 'lucide-react'
import { APP_VERSION, BUILD_DATE } from '../constants/version'

interface AboutDialogProps {
  onClose: () => void
}

export const AboutDialog: React.FC<AboutDialogProps> = ({ onClose }) => {
  return (
    <div
      className="
        fixed inset-0 z-50
        flex items-center justify-center
        bg-black/70 backdrop-blur-sm
        p-4
        animate-fade-in
      "
      onClick={onClose}
    >
      <div
        className="
          relative w-full max-w-sm
          bg-surface-900 border border-white/10
          rounded-2xl p-8
          shadow-2xl
        "
        onClick={(e) => e.stopPropagation()}
      >
        {/* Close */}
        <button
          onClick={onClose}
          className="
            absolute top-4 right-4
            p-1.5 rounded-lg
            text-white/40 hover:text-white/80
            hover:bg-white/8
            transition-colors
          "
          aria-label="Close"
        >
          <X size={16} />
        </button>

        {/* Logo */}
        <div className="flex flex-col items-center text-center mb-6">
          <div className="
            w-16 h-16 rounded-2xl
            bg-brand-500/15 border border-brand-500/30
            flex items-center justify-center
            mb-4
          ">
            <Cpu size={32} className="text-brand-400" />
          </div>
          <h2 className="text-xl font-bold text-white mb-1">Aryntra Tarka</h2>
          <p className="text-sm text-white/50">Autonomous Multi-Tool AI Agent</p>
        </div>

        {/* Version details */}
        <div className="
          rounded-xl bg-white/4 border border-white/8
          p-4 mb-6 space-y-2
        ">
          <InfoRow label="Version"    value={`v${APP_VERSION}`} />
          <InfoRow label="Build date" value={BUILD_DATE} />
          <InfoRow label="Sprint"     value="3.11 — Release Candidate" />
          <InfoRow label="License"    value="MIT" />
        </div>

        {/* Description */}
        <p className="text-sm text-white/50 text-center leading-relaxed mb-6">
          Tarka is an autonomous AI agent with multi-tool planning, streaming
          responses, persistent conversation history, and transparent reasoning.
        </p>

        {/* Links */}
        <div className="flex justify-center gap-3">
          <a
            href="https://github.com/aryntra/tarka"
            target="_blank"
            rel="noopener noreferrer"
            className="
              flex items-center gap-2
              px-4 py-2 rounded-lg text-sm
              bg-white/6 border border-white/10
              text-white/60 hover:text-white/90
              hover:border-white/20
              transition-all duration-150
            "
          >
            ⌥ GitHub
          </a>
          <span className="
            flex items-center gap-2
            px-4 py-2 rounded-lg text-sm
            bg-white/4 border border-white/8
            text-white/40
          ">
            <Heart size={14} className="text-red-400/70" />
            Built with care
          </span>
        </div>
      </div>
    </div>
  )
}

const InfoRow: React.FC<{ label: string; value: string }> = ({ label, value }) => (
  <div className="flex items-center justify-between">
    <span className="text-xs text-white/40">{label}</span>
    <span className="text-xs text-white/70 font-mono">{value}</span>
  </div>
)
