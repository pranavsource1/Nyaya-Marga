'use client';

import React from 'react';
import { ActionPlan } from '@/lib/types';
import {
  Scale,
  Calendar,
  ClipboardList,
  TrendingUp,
  ShieldAlert,
  Pin,
  Download,
  Copy,
  CheckCircle,
} from 'lucide-react';

interface ActionPlanDisplayProps {
  plan: ActionPlan;
}

// Recursively renders any JSON value
function RenderValue({ value, depth = 0 }: { value: any; depth?: number }) {
  if (value === null || value === undefined) return <span className="text-slate-400 italic">—</span>;
  if (typeof value === 'boolean')
    return (
      <span className={value ? 'text-ka-green-700 font-semibold' : 'text-ka-crimson-600 font-semibold'}>
        {value ? '✓ Yes' : '✗ No'}
      </span>
    );
  if (typeof value === 'number')
    return <span className="font-semibold text-gov-700 tabular-nums">{value.toLocaleString('en-IN')}</span>;
  if (typeof value === 'string') return <span className="text-slate-800">{value}</span>;

  if (Array.isArray(value)) {
    if (value.length === 0) return <span className="text-slate-400 italic">None</span>;
    return (
      <ul className="mt-1.5 space-y-1.5 pl-4 list-disc marker:text-slate-300">
        {value.map((item, i) => (
          <li key={i} className="text-slate-700 text-sm">
            {typeof item === 'object' ? <RenderValue value={item} depth={depth + 1} /> : String(item)}
          </li>
        ))}
      </ul>
    );
  }

  if (typeof value === 'object') {
    return (
      <div className={`space-y-2 ${depth > 0 ? 'mt-1.5 pl-3 border-l-2 border-slate-200' : ''}`}>
        {Object.entries(value).map(([k, v]) => (
          <div key={k}>
            <span className="text-[11px] font-bold text-slate-500 uppercase tracking-wider">
              {k.replace(/_/g, ' ')}
            </span>
            <div className="mt-0.5 text-sm">
              <RenderValue value={v} depth={depth + 1} />
            </div>
          </div>
        ))}
      </div>
    );
  }
  return <span className="text-slate-800 text-sm">{String(value)}</span>;
}

// Per-section styling with Lucide icons
const SECTION_CONFIG: Record<string, { borderColor: string; bgColor: string; icon: React.ElementType }> = {
  compliance_assessment: { borderColor: 'border-l-ka-green-500', bgColor: 'bg-ka-green-50/50', icon: Scale },
  statutory_timeline:    { borderColor: 'border-l-ka-gold-500',  bgColor: 'bg-ka-gold-50/50',  icon: Calendar },
  action_directives:     { borderColor: 'border-l-gov-600',      bgColor: 'bg-gov-50',          icon: ClipboardList },
  litigation_roi:        { borderColor: 'border-l-violet-500',   bgColor: 'bg-violet-50/50',    icon: TrendingUp },
  risk_assessment:       { borderColor: 'border-l-ka-crimson-500', bgColor: 'bg-ka-crimson-50/50', icon: ShieldAlert },
};

export default function ActionPlanDisplay({ plan }: ActionPlanDisplayProps) {
  if (!plan || Object.keys(plan).length === 0) {
    return (
      <div className="py-10 text-center text-blue-800 bg-blue-50 rounded-lg border border-blue-200 text-sm">
        Action plan is empty or still being generated…
      </div>
    );
  }

  return (
    <div className="space-y-3">
      {Object.entries(plan).map(([section, content]) => {
        const config = SECTION_CONFIG[section] ?? {
          borderColor: 'border-l-slate-400',
          bgColor: 'bg-slate-50',
          icon: Pin,
        };
        const IconComponent = config.icon;

        return (
          <div key={section} className={`rounded-lg border-l-4 p-4 ${config.borderColor} ${config.bgColor}`}>
            <h3 className="text-sm font-bold text-slate-800 mb-2 flex items-center gap-2">
              <IconComponent className="w-4 h-4 text-slate-500" />
              {section.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase())}
            </h3>
            <div className="text-sm text-slate-700">
              <RenderValue value={content} depth={0} />
            </div>
          </div>
        );
      })}

      {/* Export actions */}
      <div className="flex gap-2 pt-3 border-t border-slate-100">
        <button
          onClick={() => {
            const blob = new Blob([JSON.stringify(plan, null, 2)], { type: 'application/json' });
            const a = Object.assign(document.createElement('a'), {
              href: URL.createObjectURL(blob),
              download: 'action-plan.json',
            });
            a.click();
          }}
          className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs rounded-lg bg-gov-800 text-white hover:bg-gov-700 transition-all duration-200 font-medium"
        >
          <Download className="w-3 h-3" />
          Download JSON
        </button>
        <button
          onClick={() => {
            navigator.clipboard.writeText(JSON.stringify(plan, null, 2));
          }}
          className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs rounded-lg border border-slate-200 text-slate-600 hover:bg-slate-50 transition-all duration-200 font-medium"
        >
          <Copy className="w-3 h-3" />
          Copy
        </button>
      </div>
    </div>
  );
}
