'use client';

import Link from 'next/link';
import { useQuery } from '@tanstack/react-query';
import { api } from '@/lib/api';
import { CaseSummary } from '@/lib/types';
import { CheckCircle, ExternalLink, FileText, Loader2 } from 'lucide-react';

const REVIEW_STATUSES = new Set([
  'pending_review',
  'pending_verification',
  'verification_in_progress',
  'needs_reprocessing',
  'processing',
  'pending_nlp',
]);

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

export default function VerifyQueuePage() {
  const { data = [], isLoading } = useQuery({
    queryKey: ['verification-queue'],
    queryFn: () => api.listCases(),
    refetchInterval: 30000,
  });

  const queue = data.filter((item: CaseSummary) => REVIEW_STATUSES.has(item.status));

  return (
    <div className="max-w-6xl mx-auto space-y-6 pb-12">
      <section className="flex items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 tracking-tight">Verification Queue</h1>
          <p className="text-sm text-slate-500 mt-1">Cases currently awaiting officer review or processing.</p>
        </div>
        <Link
          href="/"
          className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-gov-800 hover:bg-gov-700 text-white text-sm font-medium"
        >
          <FileText className="w-4 h-4" />
          Upload Judgment
        </Link>
      </section>

      <section className="bg-white rounded-lg border border-slate-200 overflow-hidden">
        <div className="px-5 py-4 border-b border-slate-100 flex items-center gap-2">
          <CheckCircle className="w-4 h-4 text-gov-700" />
          <h2 className="text-sm font-bold text-slate-800">Pending Work</h2>
        </div>

        {isLoading ? (
          <div className="py-16 flex items-center justify-center gap-2 text-sm text-slate-500">
            <Loader2 className="w-5 h-5 animate-spin text-gov-700" />
            Loading queue...
          </div>
        ) : queue.length === 0 ? (
          <div className="py-16 text-center">
            <CheckCircle className="w-10 h-10 text-ka-green-500 mx-auto mb-3" />
            <p className="text-sm font-semibold text-slate-700">No cases require verification.</p>
            <p className="text-xs text-slate-400 mt-1">Newly processed cases will appear here from the backend.</p>
          </div>
        ) : (
          <div className="divide-y divide-slate-100">
            {queue.map((item) => (
              <Link
                key={item.case_id}
                href={`/verify/${item.case_id}`}
                className="flex items-center justify-between gap-4 px-5 py-4 hover:bg-slate-50"
              >
                <div className="min-w-0">
                  <div className="flex items-center gap-2">
                    <FileText className="w-4 h-4 text-slate-400 shrink-0" />
                    <span className="text-sm font-semibold text-slate-800 truncate">{item.case_number}</span>
                  </div>
                  <div className="mt-1 flex flex-wrap items-center gap-3 text-xs text-slate-500">
                    <span>{formatStatus(item.status)}</span>
                    <span>{item.entity_count} entities</span>
                    <span>Created {formatDate(item.created_at)}</span>
                  </div>
                </div>
                <ExternalLink className="w-4 h-4 text-slate-400" />
              </Link>
            ))}
          </div>
        )}
      </section>
    </div>
  );
}
