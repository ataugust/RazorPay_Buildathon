import React, { ReactNode } from "react";

interface AppShellProps {
  children: ReactNode;
}

/**
 * Layout wrapper that provides the overall flex structure:
 * - Fixed sidebar on the left
 * - Main content area on the right (header + page content)
 */
export default function AppShell({ children }: AppShellProps) {
  return (
    <div className="flex h-screen bg-background text-textPrimary font-sans selection:bg-accent selection:text-white overflow-hidden">
      {children}
    </div>
  );
}
