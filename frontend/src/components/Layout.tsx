// frontend/src/components/Layout.tsx
// Sprint 3.21.1 — Theme state lifted into Layout.
//                 useTheme hook wired in.
//                 Theme props passed down to TopBar.

import React, { useState, useEffect } from "react";
import { Sidebar } from "./Sidebar";
import { TopBar  } from "./TopBar";
import { useTheme } from "../hooks/useTheme";
import type { Theme } from "../hooks/useTheme";

interface LayoutProps {
  children: React.ReactNode;
}

export const Layout: React.FC<LayoutProps> = ({ children }) => {
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [isMobile,    setIsMobile]    = useState(false);

  const { theme, setTheme, toggleTheme } = useTheme();

  // ── Detect mobile viewport ────────────────────────────────────────────────
  useEffect(() => {
    const mq     = window.matchMedia("(max-width: 768px)");
    const handle = (e: MediaQueryListEvent) => {
      setIsMobile(e.matches);
      if (!e.matches) setSidebarOpen(false);
    };
    setIsMobile(mq.matches);
    mq.addEventListener("change", handle);
    return () => mq.removeEventListener("change", handle);
  }, []);

  const toggleSidebar = () => setSidebarOpen((prev) => !prev);
  const closeSidebar  = () => setSidebarOpen(false);

  return (
    <div className="flex h-screen w-screen overflow-hidden bg-surface-950 text-white">

      {/* Desktop sidebar — always visible on md+ */}
      <aside className="hidden md:flex flex-col w-64 shrink-0 bg-surface-900 border-r border-white/5">
        <Sidebar onClose={closeSidebar} />
      </aside>

      {/* Mobile sidebar — slide-over drawer */}
      {isMobile && (
        <>
          {sidebarOpen && (
            <div
              className="fixed inset-0 z-40 bg-black/60 backdrop-blur-sm"
              onClick={closeSidebar}
              aria-hidden="true"
            />
          )}
          <aside className={`
            fixed inset-y-0 left-0 z-50
            w-72 flex flex-col
            bg-surface-900 border-r border-white/5
            transform transition-transform duration-300 ease-out
            ${sidebarOpen ? "translate-x-0" : "-translate-x-full"}
          `}>
            <Sidebar onClose={closeSidebar} />
          </aside>
        </>
      )}

      {/* Main content area */}
      <div className="flex flex-col flex-1 min-w-0 overflow-hidden">
        <TopBar
          onToggleSidebar={toggleSidebar}
          isMobile={isMobile}
          theme={theme}
          onToggleTheme={toggleTheme}
          onSetTheme={setTheme}
        />
        <main className="flex-1 overflow-hidden">
          {children}
        </main>
      </div>

    </div>
  );
};