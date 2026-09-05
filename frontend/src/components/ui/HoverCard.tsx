import React, { useState } from "react";

interface HoverCardProps {
  trigger: React.ReactNode;
  content: React.ReactNode;
  align?: "left" | "right" | "center";
}

export function HoverCard({
  trigger,
  content,
  align = "right",
}: HoverCardProps) {
  const [visible, setVisible] = useState(false);

  const alignClasses = {
    left: "left-0",
    right: "right-0",
    center: "left-1/2 -translate-x-1/2",
  };

  return (
    <div
      className="relative inline-block"
      onMouseEnter={() => setVisible(true)}
      onMouseLeave={() => setVisible(false)}
    >
      <div className="cursor-pointer">{trigger}</div>

      {visible && (
        <div
          className={`absolute bottom-full mb-2 z-50 w-72 sm:w-80 p-3 bg-[#0d131f] border border-slate-700/90 rounded-xl shadow-2xl backdrop-blur-md animate-in fade-in zoom-in-95 duration-150 ${alignClasses[align]}`}
        >
          <div className="absolute top-full -mt-1 left-1/2 -translate-x-1/2 border-4 border-transparent border-t-[#0d131f] pointer-events-none" />
          {content}
        </div>
      )}
    </div>
  );
}
