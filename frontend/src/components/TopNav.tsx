import React from "react";
import Image from "next/image";
import { ShieldCheck, Bell, User } from "lucide-react";

/**
 * Top navigation bar – 64px height, dark background, subtle bottom border.
 * Contains logo, product name, status badge, demo mode badge, notification icon, and user avatar.
 */
export default function TopNav() {
  return (
    <header className="flex shrink-0 items-center justify-between h-16 px-4 bg-[#0a0d12] border-b border-[#202631]">
      {/* Left side – logo and product identity */}
      <div className="flex items-center gap-3">
        {/* Placeholder logo – replace with actual ASC logo asset if available */}
        <div className="w-8 h-8 rounded-md bg-gradient-to-br from-blue-600 via-indigo-600 to-emerald-500 flex items-center justify-center">
          <ShieldCheck className="w-4 h-4 text-white" />
        </div>
        <div className="flex flex-col">
          <span className="text-sm font-semibold text-textPrimary">ASC</span>
          <span className="text-xs text-textSecondary">Autonomous Sales Counterparty</span>
        </div>
      </div>

      {/* Center / Right side – status badges and actions */}
      <div className="flex items-center gap-4">
        {/* System Operational */}
        <div className="flex items-center gap-1 text-xs text-textSecondary">
          <span className="w-2 h-2 bg-green-500 rounded-full animate-beacon" />
          <span>System Operational</span>
        </div>
        {/* Demo Mode */}
        <div className="px-2 py-0.5 text-xs font-medium bg-[#06090f] text-textSecondary rounded border border-[#202631]">
          Demo Mode
        </div>
        {/* Notification icon */}
        <button aria-label="Notifications" className="p-1 rounded-full hover:bg-[#06090f]">
          <Bell className="w-4 h-4 text-textSecondary" />
        </button>
        {/* User avatar */}
        <button aria-label="User menu" className="p-1 rounded-full hover:bg-[#06090f]">
          <User className="w-4 h-4 text-textSecondary" />
        </button>
      </div>
    </header>
  );
}
