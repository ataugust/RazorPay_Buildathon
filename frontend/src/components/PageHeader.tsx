import React from 'react';
import { Plus } from 'lucide-react';

interface KPI {
  label: string;
  value: string | number;
}

interface PageHeaderProps {
  title: string;
  subtitle: string;
  description: string;
  kpis: KPI[];
  onNewNegotiation: () => void;
}

export default function PageHeader({ title, subtitle, description, kpis, onNewNegotiation }: PageHeaderProps) {
  return (
    <section className="p-6">
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center mb-4">
        <div>
          <h1 className="text-2xl font-semibold text-textPrimary">{title}</h1>
          <h2 className="text-lg font-medium text-textSecondary">{subtitle}</h2>
          <p className="mt-2 text-sm text-textMuted">{description}</p>
        </div>
        <button
          onClick={onNewNegotiation}
          className="mt-3 md:mt-0 px-4 py-2 bg-accent text-textPrimary rounded-lg hover:bg-accent/90 transition"
        >
          <Plus className="mr-2 inline h-4 w-4" /> New Negotiation
        </button>
      </div>
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-4">
        {kpis.map((kpi) => (
          <div key={kpi.label} className="rounded-lg border border-border bg-card p-4">
            <div className="text-xs text-textSecondary">{kpi.label}</div>
            <div className="mt-1 text-xl font-semibold text-textPrimary">{kpi.value}</div>
          </div>
        ))}
      </div>
    </section>
  );
}
