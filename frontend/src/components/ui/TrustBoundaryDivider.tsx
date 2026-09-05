import React from "react";
import { ShieldCheck, ArrowRight, Lock } from "lucide-react";

interface TrustBoundaryDividerProps {
  className?: string;
  isDragging?: boolean;
  onPointerDown?: React.PointerEventHandler<HTMLDivElement>;
  onDoubleClick?: React.MouseEventHandler<HTMLDivElement>;
  onKeyDown?: React.KeyboardEventHandler<HTMLDivElement>;
}

export function TrustBoundaryDivider({
  className = "",
  isDragging = false,
  onPointerDown,
  onDoubleClick,
  onKeyDown,
}: TrustBoundaryDividerProps) {
  return (
    <div
      role="separator"
      aria-orientation="vertical"
      aria-label="Resize intent and Control Plane panels"
      tabIndex={0}
      title="Drag to resize panels • Double-click to reset"
      onPointerDown={onPointerDown}
      onDoubleClick={onDoubleClick}
      onKeyDown={onKeyDown}
      className={`relative hidden lg:flex flex-col items-center justify-center w-7 shrink-0 select-none touch-none cursor-col-resize bg-[#0a0f19] border-x-2 transition-colors focus:outline-none focus:ring-2 focus:ring-blue-500/70 ${
        isDragging
          ? "border-blue-500 bg-blue-950/30 shadow-[0_0_22px_rgba(59,130,246,0.45)]"
          : "border-slate-700/80 shadow-[0_0_15px_rgba(0,0,0,0.5)] hover:border-blue-500/70"
      } ${className}`}
    >
      {/* Repeating fine vertical dotted pattern or laser line */}
      <div className="absolute inset-y-0 w-[1px] bg-gradient-to-b from-blue-500/20 via-indigo-500/40 to-emerald-500/20" />

      {/* Center Fixed Trust Boundary Badge */}
      <div className="sticky top-1/2 -translate-y-1/2 z-30 flex flex-col items-center gap-2 py-4">
        {/* Glow pill badge */}
        <div className="flex flex-col items-center gap-1.5 p-1.5 bg-[#080d16] border border-blue-500/50 rounded-full shadow-[0_0_12px_rgba(59,130,246,0.3)]">
          <div className="p-1 rounded-full bg-blue-950 text-blue-400">
            <ShieldCheck className="w-3.5 h-3.5" />
          </div>
        </div>

        {/* Vertical Text Orientation */}
        <div
          className="[writing-mode:vertical-rl] rotate-180 font-mono text-[10px] font-black tracking-widest uppercase text-slate-300 py-3 flex items-center gap-2 bg-[#080d16]/95 px-1 rounded border border-slate-800"
        >
          <span className="text-blue-400">INTELLIGENCE PROPOSES</span>
          <span className="text-slate-600">|</span>
          <span className="text-amber-400 font-extrabold tracking-wider">
            TRUST BOUNDARY
          </span>
          <span className="text-slate-600">|</span>
          <span className="text-emerald-400">CONTROL PLANE DECIDES</span>
        </div>

        {/* Bottom Lock Icon */}
        <div className="p-1 rounded-full bg-slate-900 border border-slate-700 text-slate-400 mt-1">
          <Lock className="w-2.5 h-2.5" />
        </div>
      </div>
    </div>
  );
}
