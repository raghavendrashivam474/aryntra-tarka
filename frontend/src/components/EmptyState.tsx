// frontend/src/components/EmptyState.tsx
import React from 'react'
import { Cpu, Zap, Brain, Wrench } from 'lucide-react'
import { APP_VERSION } from '../constants/version'

const SAMPLE_PROMPTS = [
  {
    icon:  <Zap size={16} className="text-yellow-400" />,
    label: 'Run a calculation',
    text:  'What is 1847 × 293 plus the square root of 2401?',
  },
  {
    icon:  <Brain size={16} className="text-purple-400" />,
    label: 'Multi-step reasoning',
    text:  'Plan a 3-day itinerary for Tokyo, then convert the budget to GBP.',
  },
  {
    icon:  <Wrench size={16} className="text-cyan-400" />,
    label: 'Use multiple tools',
    text:  'Get the current time, calculate how many hours until midnight, then summarise.',
  },
  {
    icon:  <Cpu size={16} className="text-brand-400" />,
    label: 'Code generation',
    text:  'Write a Python function to merge two sorted lists, with type hints and docstring.',
  },
]

interface EmptyStateProps {
  onPrompt: (text: string) => void
}

export const EmptyState: React.FC<EmptyStateProps> = ({ onPrompt }) => {
  return (
    <div className="
      flex flex-col items-center justify-center
      h-full w-full px-6
      animate-fade-in
    ">
      {/* Logo */}
      <div className="
        w-16 h-16 rounded-2xl
        bg-brand-500/15 border border-brand-500/30
        flex items-center justify-center
        mb-6
      ">
        <Cpu size={32} className="text-brand-400" />
      </div>

      {/* Heading */}
      <h1 className="text-2xl font-semibold text-white mb-2 text-center">
        Aryntra Tarka
      </h1>
      <p className="text-white/40 text-sm mb-1 text-center">
        Autonomous multi-tool AI agent
      </p>
      <p className="text-white/20 text-xs font-mono mb-10 text-center">
        Version {APP_VERSION}
      </p>

      {/* Prompt suggestions */}
      <div className="
        grid grid-cols-1 sm:grid-cols-2
        gap-3 w-full max-w-xl
      ">
        {SAMPLE_PROMPTS.map((prompt) => (
          <button
            key={prompt.text}
            onClick={() => onPrompt(prompt.text)}
            className="
              flex flex-col gap-1.5
              p-4 rounded-xl text-left
              bg-white/4 border border-white/8
              hover:bg-white/8 hover:border-white/16
              transition-all duration-200
              group
            "
          >
            <div className="flex items-center gap-2">
              {prompt.icon}
              <span className="text-xs font-medium text-white/60 group-hover:text-white/80 transition-colors">
                {prompt.label}
              </span>
            </div>
            <p className="text-sm text-white/80 leading-snug">
              {prompt.text}
            </p>
          </button>
        ))}
      </div>
    </div>
  )
}