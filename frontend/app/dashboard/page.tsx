'use client';

import React, { useState } from 'react';
import Link from 'next/link';
import { api, handleApiError } from '@/lib/api';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  CheckCircle, Upload, Search, AlertTriangle, Clock,
  Download, Hourglass, Check, Trash2, FileBarChart,
  Loader2, FileText, ExternalLink, ArrowUpRight,
  ShieldAlert, TrendingUp,
} from 'lucide-react';

/* ═══════════════════════════════════════════
   STATUS UTILITIES
   ═══════════════════════════════════════════ */

type StatusColor = 'crimson' | 'gold' | 'green' | 'blue';

function getStatusColor(status: string): StatusColor {
  switch (status) {
    case 'failed':
      return 'crimson';
    case 'processing':
    case 'pending_review':
    case 'pending_nlp':
    case 'pending_verification':
      return 'gold';
    case 'verified':
      return 'green';
    default:
      return 'blue';
  }
}

function getStatusBadgeClasses(color: StatusColor): string {
  const map: Record<StatusColor, string> = {
    crimson: 'bg-rose-50 border border-rose-200 text-rose-800',
    gold:    'bg-amber-50 border border-amber-200 text-amber-800',
    green:   'bg-emerald-50 border border-emerald-200 text-emerald-800',
    blue:    'bg-sky-50 border border-sky-200 text-sky-800',
  };
  return map[color];
}

function formatStatusLabel(status: string): string {
  return status.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase());
}

function formatDate(dateStr: string | null): string {
  if (!dateStr) return '—';
  try {
    return new Date(dateStr).toLocaleDateString('en-IN', {
      day: '2-digit', month: 'short', year: 'numeric',
    });
  } catch { return '—'; }
}

/* ═══════════════════════════════════════════
   KPI METRIC BOX — Dense, flat, no rounded-xl
   ═══════════════════════════════════════════ */

function MetricBox({
  title, value, subtitle, icon: Icon, borderColor,
}: {
  title: string;
  value: string;
  subtitle: string;
  icon: React.ElementType;
  borderColor: string;
}) {
  return (
    <div className={`bg-white border border-slate-200 p-4 flex flex-col border-t-[3px] ${borderColor}`}>
      <div className="flex items-start justify-between mb-2">
        <h3 className="text-[10px] font-bold text-slate-500 uppercase tracking-[0.1em] leading-snug max-w-[140px]">
          {title}
        </h3>
        <Icon className="w-4 h-4 text-slate-400 shrink-0" strokeWidth={1.8} />
      </div>
      <div className="mt-auto">
        <div className="text-2xl font-bold text-slate-900 tabular-nums tracking-tight">{value}</div>
        <p className="text-[11px] text-slate-400 mt-0.5 font-medium">{subtitle}</p>
      </div>
    </div>
  );
}

/* ═══════════════════════════════════════════
   DASHBOARD PAGE
   ═══════════════════════════════════════════ */

export default function Dashboard() {
  const queryClient = useQueryClient();
  const [searchQuery, setSearchQuery] = useState('');

  const { data: casesData = [], isLoading: casesLoading } = useQuery({
    queryKey: ['dashboard-cases'],
    queryFn: () => api.listCases(),
    refetchInterval: 30000,
  });

  const { data: stats, isLoading: statsLoading } = useQuery({
    queryKey: ['dashboard-stats'],
    queryFn: () => api.getDashboardStats(),
    refetchInterval: 30000,
  });

  const isLoading = casesLoading || statsLoading;

  const cases = casesData.map((c: any) => ({
    id: c.case_id,
    caseNumber: c.case_number,
    status: c.status,
    createdAt: c.created_at,
    updatedAt: c.updated_at,
    entityCount: c.entity_count || 0,
    errorMessage: c.error_message || null,
  }));

  const filteredCases = searchQuery.trim()
    ? cases.filter((c: any) =>
        c.caseNumber.toLowerCase().includes(searchQuery.toLowerCase()) ||
        c.status.toLowerCase().includes(searchQuery.toLowerCase())
      )
    : cases;

  const deleteMutation = useMutation({
    mutationFn: (caseId: string) => api.deleteCase(caseId),
    onSuccess: () => { queryClient.invalidateQueries({ queryKey: ['dashboard-cases'] }); },
    onError: (error: any) => { alert(`Failed to delete: ${handleApiError(error).detail}`); },
  });

  const handleDelete = (e: React.MouseEvent, caseId: string) => {
    e.stopPropagation();
    if (window.confirm('Delete this case permanently? This cannot be undone.')) {
      deleteMutation.mutate(caseId);
    }
  };

  const [ragQuery, setRagQuery] = useState('');
  const [ragResult, setRagResult] = useState<any>(null);
  const [isSearching, setIsSearching] = useState(false);

  const handleRagSearch = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!ragQuery.trim()) return;
    setIsSearching(true);
    setRagResult(null);
    try {
      const res = await api.ragSearch(ragQuery);
      setRagResult({
        answer: res.synthesis?.guidance || 'No synthesized answer available.',
        citations: res.precedents || [],
        semantic_hits: res.retrieval_stats?.semantic_hits || 0,
        keyword_hits: res.retrieval_stats?.keyword_hits || 0,
      });
    } catch (error: any) {
      console.error('RAG Search failed:', handleApiError(error).detail);
    } finally {
      setIsSearching(false);
    }
  };

  const pendingCases = cases.filter((c: any) =>
    ['processing', 'pending_nlp', 'pending_review', 'pending_verification', 'verification_in_progress', 'needs_reprocessing'].includes(c.status)
  );
  const verifyHref = pendingCases.length > 0 ? `/verify/${pendingCases[0].id}` : '#';

  const exportCasesCsv = () => {
    const header = ['case_number', 'status', 'entity_count', 'created_at', 'updated_at'];
    const values = (row: any) => [row.caseNumber, row.status, row.entityCount, row.createdAt, row.updatedAt];
    const csvRows = [
      header.join(','),
      ...cases.map((row: any) =>
        values(row).map((v) => `"${String(v ?? '').replace(/"/g, '""')}"`).join(',')
      ),
    ];
    const blob = new Blob([csvRows.join('\n')], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `nyaya-marga-cases-${new Date().toISOString().slice(0, 10)}.csv`;
    link.click();
    URL.revokeObjectURL(url);
  };

  const urgentCount = cases.filter((c: any) => c.status === 'failed').length;

  return (
    <div className="max-w-7xl mx-auto space-y-6 pb-12">

      {/* ══ PAGE HEADER ══ */}
      <section className="flex flex-col sm:flex-row items-start sm:items-end justify-between gap-4 border-b border-slate-200 pb-5">
        <div>
          <p className="text-[10px] font-bold text-slate-400 uppercase tracking-[0.14em] mb-1">
            Centre for e-Governance, Karnataka
          </p>
          <h1 className="text-xl font-extrabold text-slate-900 tracking-tight uppercase">
            Departmental Action Plan Overview
          </h1>
          <p className="text-[13px] text-slate-500 mt-1 font-medium">
            Real-time case pipeline status · Report generated{' '}
            {new Date().toLocaleDateString('en-IN', { day: '2-digit', month: 'short', year: 'numeric' })}
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Link
            href="/"
            className="inline-flex items-center gap-2 px-4 py-2 border border-slate-300 bg-white text-slate-700 font-semibold text-[13px] hover:bg-slate-50 transition-colors"
          >
            <Upload className="w-3.5 h-3.5" /> Upload
          </Link>
          <Link
            href={verifyHref}
            className={`inline-flex items-center gap-2 px-4 py-2 border text-[13px] font-semibold transition-colors ${
              pendingCases.length > 0
                ? 'border-amber-300 bg-amber-50 text-amber-800 hover:bg-amber-100'
                : 'border-slate-200 bg-white text-slate-400 cursor-not-allowed'
            }`}
          >
            <CheckCircle className="w-3.5 h-3.5" /> Verify Queue ({pendingCases.length})
          </Link>
        </div>
      </section>

      {/* ══ KPI METRICS ══ */}
      <section className="grid grid-cols-2 lg:grid-cols-4 gap-px bg-slate-200 border border-slate-200" aria-label="Key performance indicators">
        <MetricBox
          title="Verified This Month"
          value={stats?.verified_this_month?.toString() || '0'}
          icon={Check}
          borderColor="border-t-emerald-500"
          subtitle="Cases verified this month"
        />
        <MetricBox
          title="Pending Verification"
          value={stats?.pending_verification?.toString() || '0'}
          icon={Hourglass}
          borderColor="border-t-amber-500"
          subtitle="Awaiting officer review"
        />
        <MetricBox
          title="High Urgency Directives"
          value={urgentCount.toString()}
          icon={ShieldAlert}
          borderColor="border-t-rose-500"
          subtitle="Failed / require attention"
        />
        <MetricBox
          title="Total Records"
          value={cases.length.toString()}
          icon={FileBarChart}
          borderColor="border-t-gov-700"
          subtitle="All cases in system"
        />
      </section>

      {/* ══ PRECEDENT INTELLIGENCE ══ */}
      <section className="bg-white border border-slate-200 overflow-hidden">
        <div className="px-5 py-3 border-b border-slate-200 bg-slate-50 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Search className="w-3.5 h-3.5 text-gov-700" />
            <h2 className="text-[13px] font-bold text-slate-800 uppercase tracking-wide">Precedent Intelligence</h2>
          </div>
          <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">RAG-Powered</span>
        </div>
        <div className="p-5">
          <form onSubmit={handleRagSearch} className="flex gap-2 mb-4">
            <input
              type="text" value={ragQuery} onChange={(e) => setRagQuery(e.target.value)}
              placeholder="Query the verified knowledge base…"
              className="flex-1 text-[13px] px-3 py-2 border border-slate-300 focus:outline-none focus:ring-2 focus:ring-gov-600 focus:border-transparent transition-shadow"
            />
            <button
              type="submit" disabled={isSearching || !ragQuery.trim()}
              className="px-4 py-2 bg-gov-800 hover:bg-gov-700 text-white text-[13px] font-semibold transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
            >
              {isSearching && <Loader2 className="w-3.5 h-3.5 animate-spin" />}
              {isSearching ? 'Searching…' : 'Search'}
            </button>
          </form>
          {ragResult ? (
            <div className="bg-slate-50 p-4 border border-slate-200 text-[13px] space-y-3">
              <p className="text-slate-800 leading-relaxed">{ragResult.answer}</p>
              <div className="flex gap-4 text-[11px] font-semibold text-slate-500 border-t border-slate-200 pt-3">
                <span>Semantic Hits: {ragResult.semantic_hits}</span>
                <span>Keyword Hits: {ragResult.keyword_hits}</span>
              </div>
            </div>
          ) : (
            <div className="flex items-center justify-center text-slate-400 text-[12px] text-center border-2 border-dashed border-slate-200 py-6">
              Enter a query to search across the verified case database.
            </div>
          )}
        </div>
      </section>

      {/* ══ CASES DATA TABLE ══ */}
      <section className="bg-white border border-slate-200 overflow-hidden">
        <div className="px-5 py-3 border-b border-slate-200 bg-slate-50 flex flex-col lg:flex-row lg:items-center justify-between gap-3">
          <div>
            <h2 className="text-[13px] font-bold text-slate-800 uppercase tracking-wide">Case Register</h2>
            <p className="text-[11px] text-slate-400 font-medium mt-0.5">
              {filteredCases.length} record{filteredCases.length !== 1 ? 's' : ''} · All statuses
            </p>
          </div>
          <div className="flex items-center gap-2">
            <div className="relative">
              <Search className="w-3.5 h-3.5 absolute left-2.5 top-1/2 -translate-y-1/2 text-slate-400" />
              <input
                type="text" value={searchQuery} onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Filter cases…"
                className="pl-8 pr-3 py-1.5 text-[13px] border border-slate-300 focus:outline-none focus:ring-2 focus:ring-gov-600 focus:border-transparent w-48 transition-shadow"
              />
            </div>
            <button
              onClick={exportCasesCsv}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 border border-slate-300 text-slate-600 text-[13px] font-semibold hover:bg-slate-100 transition-colors"
              title="Export CSV"
            >
              <Download className="w-3.5 h-3.5" /> Export
            </button>
          </div>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left" aria-label="Cases table">
            <thead>
              <tr className="border-b border-slate-300 bg-slate-100">
                <th scope="col" className="px-5 py-2.5 text-[10px] font-extrabold text-slate-500 uppercase tracking-[0.1em]">Case Number</th>
                <th scope="col" className="px-5 py-2.5 text-[10px] font-extrabold text-slate-500 uppercase tracking-[0.1em]">Status</th>
                <th scope="col" className="px-5 py-2.5 text-[10px] font-extrabold text-slate-500 uppercase tracking-[0.1em]">Entities</th>
                <th scope="col" className="px-5 py-2.5 text-[10px] font-extrabold text-slate-500 uppercase tracking-[0.1em]">Date Filed</th>
                <th scope="col" className="px-5 py-2.5 text-[10px] font-extrabold text-slate-500 uppercase tracking-[0.1em] text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {isLoading ? (
                <tr>
                  <td colSpan={5} className="px-5 py-12 text-center">
                    <div className="flex flex-col items-center gap-3 text-slate-500">
                      <Loader2 className="w-5 h-5 animate-spin text-gov-600" />
                      <span className="text-[13px] font-semibold">Loading records…</span>
                    </div>
                  </td>
                </tr>
              ) : filteredCases.length === 0 ? (
                <tr>
                  <td colSpan={5} className="px-5 py-12 text-center">
                    <div className="flex flex-col items-center gap-2">
                      <FileText className="w-6 h-6 text-slate-300" />
                      <span className="text-[13px] font-semibold text-slate-500">
                        {searchQuery ? 'No cases match your filter.' : 'No cases found. Upload a judgment to begin.'}
                      </span>
                    </div>
                  </td>
                </tr>
              ) : (
                filteredCases.map((row: any, idx: number) => {
                  const statusColor = getStatusColor(row.status);
                  return (
                    <tr
                      key={row.id || idx}
                      className="hover:bg-slate-50 transition-colors duration-100 cursor-pointer group"
                      onClick={() => row.id && (window.location.href = `/verify/${row.id}`)}
                    >
                      <td className="px-5 py-3">
                        <div className="flex items-center gap-2">
                          <FileText className="w-3.5 h-3.5 text-slate-400 shrink-0" />
                          <span className="text-[13px] font-semibold text-slate-800">{row.caseNumber}</span>
                        </div>
                      </td>
                      <td className="px-5 py-3">
                        <span className={`inline-flex items-center px-2 py-0.5 text-[10px] font-bold uppercase tracking-wide ${getStatusBadgeClasses(statusColor)}`}>
                          {formatStatusLabel(row.status)}
                        </span>
                      </td>
                      <td className="px-5 py-3">
                        <span className="text-[13px] text-slate-600 tabular-nums font-medium">{row.entityCount}</span>
                      </td>
                      <td className="px-5 py-3">
                        <span className="text-[13px] text-slate-500 font-medium">{formatDate(row.createdAt)}</span>
                      </td>
                      <td className="px-5 py-3 text-right">
                        <div className="flex items-center justify-end gap-1">
                          <Link
                            href={`/verify/${row.id}`}
                            onClick={(e) => e.stopPropagation()}
                            className="p-1.5 text-slate-400 hover:text-gov-700 hover:bg-gov-50 transition-colors"
                            title="View & Verify"
                          >
                            <ExternalLink className="w-3.5 h-3.5" />
                          </Link>
                          <button
                            onClick={(e) => handleDelete(e, row.id)}
                            className="p-1.5 text-slate-400 hover:text-rose-700 hover:bg-rose-50 transition-colors"
                            title="Delete Case"
                          >
                            <Trash2 className="w-3.5 h-3.5" />
                          </button>
                        </div>
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
}
