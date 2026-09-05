import React, { useState } from "react";
import { ChevronDown } from "lucide-react";

interface AccordionProps {
  title: string;
  badge?: string;
  defaultOpen?: boolean;
  children: React.ReactNode;
  className?: string;
}

export function Accordion({
  title,
  badge,
  defaultOpen = false,
  children,
  className = "",
}: AccordionProps) {
  const [isOpen, setIsOpen] = useState(defaultOpen);

  return (
    <div
      className={`border border-slate-800 rounded-lg overflow-hidden bg-[#0a0f18] transition-colors ${className}`}
    >
      <button
        type="button"
        onClick={() => setIsOpen(!isOpen)}
        className="w-full px-3 py-2 flex items-center justify-between text-left hover:bg-slate-900/60 transition-colors focus:outline-none"
      >
        <div className="flex items-center gap-2">
          <span className="font-mono text-xs font-semibold text-slate-300">
            {title}
          </span>
          {badge && (
            <span className="px-1.5 py-0.2 bg-blue-950/80 text-blue-300 border border-blue-800/60 rounded text-[9px] font-mono">
              {badge}
            </span>
          )}
        </div>
        <div className="flex items-center gap-1.5 text-slate-400 text-xs font-mono">
          <span>{isOpen ? "Hide JSON" : "View Raw JSON"}</span>
          <ChevronDown
            className={`w-3.5 h-3.5 transition-transform duration-200 ${
              isOpen ? "rotate-180 text-blue-400" : "text-slate-500"
            }`}
          />
        </div>
      </button>

      {isOpen && (
        <div className="p-3 border-t border-slate-800/80 bg-[#06090f] overflow-x-auto text-[11px] font-mono">
          {children}
        </div>
      )}
    </div>
  );
}
