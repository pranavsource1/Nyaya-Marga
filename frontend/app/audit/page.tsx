'use client';

import Link from 'next/link';
import { useQuery } from '@tanstack/react-query';
import { api } from '@/lib/api';
import { AuditLogEntry } from '@/lib/types';
import { ExternalLink, Loader2, ScrollText } from 'lucide-react';

function formatDate(value: string | null) {
  if (!value) return '-';
  return new Date(value).toLocaleString('en-IN', {
    day: '2-digit',
    month: 'short',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
}

export default function AuditPage() {
  const { data = [], isLoading } = useQuery({
    queryKey: ['audit-log'],
    queryFn: () => api.listAuditLogs(),
    refetchInterval: 30000,
  });

  return (
    <div className="max-w-7xl mx-auto space-y-6 pb-12">
      <section>
        <h1 className="text-2xl font-bold text-slate-900 tracking-tight">Audit Trail</h1>
        <p className="text-sm text-slate-500 mt-1">Immutable backend verification events and officer actions.</p>
      </section>

      <section className="bg-white rounded-lg border border-slate-200 overflow-hidden">
        <div className="px-5 py-4 border-b border-slate-100 flex items-center gap-2">
          <ScrollText className="w-4 h-4 text-gov-700" />
          <h2 className="text-sm font-bold text-slate-800">Latest Events</h2>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left">
            <thead>
              <tr className="border-b border-slate-200 bg-slate-50/80">
                <th className="px-5 py-3 text-[11px] font-bold text-slate-500 uppercase tracking-wider">Time</th>
                <th className="px-5 py-3 text-[11px] font-bold text-slate-500 uppercase tracking-wider">Case</th>
                <th className="px-5 py-3 text-[11px] font-bold text-slate-500 uppercase tracking-wider">Action</th>
                <th className="px-5 py-3 text-[11px] font-bold text-slate-500 uppercase tracking-wider">Officer</th>
                <th className="px-5 py-3 text-[11px] font-bold text-slate-500 uppercase tracking-wider">Reason</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {isLoading ? (
                <tr>
                  <td colSpan={5} className="px-5 py-12 text-center text-sm text-slate-500">
                    <span className="inline-flex items-center gap-2">
                      <Loader2 className="w-5 h-5 animate-spin text-gov-700" />
                      Loading audit log...
                    </span>
                  </td>
                </tr>
              ) : data.length === 0 ? (
                <tr>
                  <td colSpan={5} className="px-5 py-12 text-center text-sm text-slate-500">
                    No audit events have been recorded by the backend yet.
                  </td>
                </tr>
              ) : (
                data.map((entry: AuditLogEntry) => (
                  <tr key={entry.id} className="hover:bg-slate-50">
                    <td className="px-5 py-3.5 text-sm text-slate-600 whitespace-nowrap">{formatDate(entry.created_at)}</td>
                    <td className="px-5 py-3.5">
                      <Link
                        href={`/verify/${entry.case_id}`}
                        className="inline-flex items-center gap-1.5 text-sm font-semibold text-gov-700 hover:text-gov-900"
                      >
                        {entry.case_number}
                        <ExternalLink className="w-3.5 h-3.5" />
                      </Link>
                    </td>
                    <td className="px-5 py-3.5">
                      <span className="inline-flex rounded-md bg-slate-100 px-2 py-0.5 text-[11px] font-bold text-slate-700 uppercase tracking-wide">
                        {entry.action}
                      </span>
                    </td>
                    <td className="px-5 py-3.5">
                      <div className="text-sm text-slate-800">{entry.actor_name}</div>
                      <div className="text-xs text-slate-500">{entry.actor_email}</div>
                    </td>
                    <td className="px-5 py-3.5 text-sm text-slate-600 max-w-sm truncate">{entry.reason || '-'}</td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
}
