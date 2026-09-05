import { Check, Circle } from "lucide-react";
import { AuditEvent } from "../types/commerce";
import { dateTime } from "../lib/format";
import { eventLabels } from "../lib/status";

const hidden = new Set(["GATE_CHECK_PASS", "GATE_CHECK_FAIL"]);

export function DealTimeline({ events = [], compact = false }: { events?: AuditEvent[]; compact?: boolean }) {
  const visible = events.filter((event) => !hidden.has(event.event_type));
  if (!visible.length) return <p className="py-6 text-sm text-slate-500">Timeline events will appear as the deal progresses.</p>;
  return (
    <ol className="relative ml-2 border-l border-slate-200">
      {visible.map((event, index) => (
        <li key={event.id || `${event.event_type}-${index}`} className={`${compact ? "mb-4 ml-5" : "mb-6 ml-6"} animate-in fade-in slide-in-from-bottom-1 duration-300`}>
          <span className={`absolute -left-2 flex h-4 w-4 items-center justify-center rounded-full border-2 border-white ${event.status === "FAIL" ? "bg-red-500" : event.status === "WARN" ? "bg-amber-500" : "bg-emerald-500"}`}>
            {index < visible.length - 1 ? <Check className="h-2.5 w-2.5 text-white" /> : <Circle className="h-2 w-2 fill-white text-white" />}
          </span>
          <div className="flex flex-wrap items-center justify-between gap-2">
            <p className="text-sm font-semibold text-slate-900">{eventLabels[event.event_type] || event.event_type.replaceAll("_", " ")}</p>
            <time className="text-xs text-slate-400">{dateTime(event.timestamp)}</time>
          </div>
          <p className="mt-1 text-sm leading-5 text-slate-500">{event.message}</p>
          {!compact && <span className="mt-1 inline-block text-[11px] font-medium uppercase tracking-wide text-slate-400">{event.component.replaceAll("_", " ")}</span>}
        </li>
      ))}
    </ol>
  );
}
