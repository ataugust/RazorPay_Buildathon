import React from "react";

interface BadgeProps extends React.HTMLAttributes<HTMLSpanElement> {
  variant?: "default" | "pass" | "fail" | "warn" | "info" | "outline" | "mandate";
  size?: "sm" | "md";
}

export function Badge({
  className = "",
  variant = "default",
  size = "md",
  children,
  ...props
}: BadgeProps) {
  const baseClasses =
    "inline-flex items-center font-mono font-bold uppercase tracking-wider rounded transition-all";

  const sizeClasses = {
    sm: "px-1.5 py-0.5 text-[9px]",
    md: "px-2 py-0.5 text-[10px]",
  };

  const variantClasses = {
    default: "bg-slate-800 text-slate-300 border border-slate-700",
    pass: "bg-emerald-950/90 text-emerald-300 border border-emerald-700/80 shadow-[0_0_8px_rgba(16,185,129,0.2)]",
    fail: "bg-rose-950/90 text-rose-300 border border-rose-700/80 shadow-[0_0_8px_rgba(244,63,94,0.2)]",
    warn: "bg-amber-950/90 text-amber-300 border border-amber-700/80 shadow-[0_0_8px_rgba(245,158,11,0.2)]",
    info: "bg-blue-950/90 text-blue-300 border border-blue-700/80 shadow-[0_0_8px_rgba(59,130,246,0.2)]",
    outline: "border border-slate-700 text-slate-400 bg-transparent",
    mandate: "bg-indigo-950/90 text-indigo-300 border border-indigo-700/80",
  };

  return (
    <span
      className={`${baseClasses} ${sizeClasses[size]} ${variantClasses[variant]} ${className}`}
      {...props}
    >
      {children}
    </span>
  );
}
