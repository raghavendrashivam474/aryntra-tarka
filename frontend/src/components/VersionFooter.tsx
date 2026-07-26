// frontend/src/components/VersionFooter.tsx
import React from 'react'
import { APP_VERSION, APP_NAME } from '../constants/version'

export const VersionFooter: React.FC = () => (
  <div className="
    px-4 py-3
    border-t border-white/5
    flex items-center justify-center
  ">
    <p className="text-xs text-white/20 font-mono select-none">
      {APP_NAME} · v{APP_VERSION}
    </p>
  </div>
)