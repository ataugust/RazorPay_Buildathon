import React from "react";
import {
  LayoutDashboard,
  Handshake,
  ShoppingCart,
  Package,
  Brain,
  ShieldCheck,
  Activity,
  Settings,
} from "lucide-react";
import Link from "next/link";

/**
 * Fixed sidebar navigation. Width ~240px.
 * Uses the custom color tokens defined in tailwind.config.js.
 */
export default function Sidebar({
  activePage = "overview",
}: {
  activePage?: string;
}) {
  const navItems = [
    { id: "overview", label: "Overview", icon: <LayoutDashboard className="w-4 h-4" /> },
    { id: "negotiations", label: "Negotiations", icon: <Handshake className="w-4 h-4" /> },
    { id: "orders", label: "Orders", icon: <ShoppingCart className="w-4 h-4" /> },
    { id: "products", label: "Products", icon: <Package className="w-4 h-4" /> },
    { id: "strategies", label: "Strategy Engine", icon: <Brain className="w-4 h-4" /> },
    { id: "audit", label: "Audit Trail", icon: <Activity className="w-4 h-4" /> },
    { id: "settings", label: "System", icon: <Settings className="w-4 h-4" /> },
  ];

  return (
    <aside className="w-60 flex flex-col bg-card border-r border-border text-textSecondary">
      <nav className="flex-1 py-4">
        {navItems.map((item) => (
          <Link
            key={item.id}
            href="#"
            className={`flex items-center gap-2 px-4 py-2 m-1 rounded-lg transition-colors 
              ${activePage === item.id ? "bg-accent text-textPrimary" : "text-textSecondary hover:bg-[#0a0d12]"}`}
          >
            <span className={activePage === item.id ? "text-textPrimary" : ""}>{item.icon}</span>
            <span className="text-sm font-medium">{item.label}</span>
          </Link>
        ))}
      </nav>
      {/* System status section */}
      <div className="px-4 py-3 border-t border-border text-xs text-textMuted">
        <div className="font-semibold mb-1 text-textSecondary">SYSTEM STATUS</div>
        <div className="flex flex-col gap-0.5">
          <StatusBadge label="Control Plane" status="operational" />
          <StatusBadge label="AI Negotiator" status="ready" />
          <StatusBadge label="Commerce Engine" status="active" />
        </div>
      </div>
    </aside>
  );
}

/** Small status badge used in the sidebar */
function StatusBadge({
  label,
  status,
}: {
  label: string;
  status: "operational" | "active" | "ready" | "passed" | "blocked" | "warning";
}) {
  const statusColorMap: Record<string, string> = {
    operational: "bg-green-500",
    active: "bg-blue-500",
    ready: "bg-indigo-500",
    passed: "bg-emerald-500",
    blocked: "bg-rose-500",
    warning: "bg-amber-500",
  };
  return (
    <div className="flex items-center gap-1">
      <span className={`w-2 h-2 rounded-full ${statusColorMap[status]}`} />
      <span>{label}</span>
    </div>
  );
}
