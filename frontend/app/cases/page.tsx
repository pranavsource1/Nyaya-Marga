'use client';

import Link from 'next/link';
import { useQuery } from '@tanstack/react-query';
import { api } from '@/lib/api';
import { CaseSummary } from '@/lib/types';
import { ExternalLink, FileText, Loader2 } from 'lucide-react';

function formatDate(value: string | null) {
  if (!value) return '-';
  return new Date(value).toLocaleDateString('en-IN', {
    day: '2-digit',
    month: 'short',
    year: 'numeric',
  });
}

function formatStatus(value: string) {
  return value.replace(/_/g, ' ').replace(/\b\w/g, (char) => char.toUpperCase());
}

export default function CasesPage() {
  const { data = [], isLoading } = useQuery({
    queryKey: ['cases'],
    queryFn: () => api.listCases(),
    refetchInterval: 30000,
  });

  return (
    <div className="max-w-7xl mx-auto space-y-6 pb-12">
      <section>
        <h1 className="text-2xl font-bold text-slate-900 tracking-tight">All Cases</h1>
        <p className="text-sm text-slate-500 mt-1">Complete case list returned by the backend dashboard API.</p>
      </section>

      <section className="bg-white rounded-lg border border-slate-200 overflow-hidden">
        <div className="px-5 py-4 border-b border-slate-100 flex items-center gap-2">
          <FileText className="w-4 h-4 text-gov-700" />
          <h2 className="text-sm font-bold text-slate-800">Cases</h2>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-left">
            <thead>
              <tr className="border-b border-slate-200 bg-slate-50/80">
                <th className="px-5 py-3 text-[11px] font-bold text-slate-500 uppercase tracking-wider">Case Number</th>
                <th className="px-5 py-3 text-[11px] font-bold text-slate-500 uppercase tracking-wider">Court</th>
                <th className="px-5 py-3 text-[11px] font-bold text-slate-500 uppercase tracking-wider">Status</th>
                <th className="px-5 py-3 text-[11px] font-bold text-slate-500 uppercase tracking-wider">Entities</th>
                <th className="px-5 py-3 text-[11px] font-bold text-slate-500 uppercase tracking-wider">Created</th>
                <th className="px-5 py-3 text-[11px] font-bold text-slate-500 uppercase tracking-wider text-right">Open</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {isLoading ? (
                <tr>
                  <td colSpan={6} className="px-5 py-12 text-center text-sm text-slate-500">
                    <span className="inline-flex items-center gap-2">
                      <Loader2 className="w-5 h-5 animate-spin text-gov-700" />
                      Loading cases...
                    </span>
                  </td>
                </tr>
              ) : data.length === 0 ? (
                <tr>
                  <td colSpan={6} className="px-5 py-12 text-center text-sm text-slate-500">
                    No cases have been uploaded yet.
                  </td>
                </tr>
              ) : (
                data.map((item: CaseSummary) => (
                  <tr key={item.case_id} className="hover:bg-slate-50">
                    <td className="px-5 py-3.5 text-sm font-semibold text-slate-800">{item.case_number}</td>
                    <td className="px-5 py-3.5 text-sm text-slate-600">{item.court_name || '-'}</td>
                    <td className="px-5 py-3.5 text-sm text-slate-600">{formatStatus(item.status)}</td>
                    <td className="px-5 py-3.5 text-sm text-slate-600">{item.entity_count}</td>
                    <td className="px-5 py-3.5 text-sm text-slate-600">{formatDate(item.created_at)}</td>
                    <td className="px-5 py-3.5 text-right">
                      <Link
                        href={`/verify/${item.case_id}`}
                        className="inline-flex items-center justify-center p-1.5 rounded-md text-slate-400 hover:text-gov-700 hover:bg-gov-50"
                        title="Open case"
                      >
                        <ExternalLink className="w-4 h-4" />
                      </Link>
                    </td>
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
