'use client';

import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { api } from '@/lib/api';
import { CaseSummary } from '@/lib/types';
import LoadingSpinner from '@/components/LoadingSpinner';

function StatusBadge({ status }: { status: string }) {
  const config: Record<string, string> = {
    verified: 'bg-emerald-100 text-emerald-800 ring-1 ring-emerald-200',
    pending_review: 'bg-amber-100 text-amber-800 ring-1 ring-amber-200',
    processing: 'bg-blue-100 text-blue-800 ring-1 ring-blue-200',
    pending_nlp: 'bg-indigo-100 text-indigo-800 ring-1 ring-indigo-200',
    failed: 'bg-red-100 text-red-800 ring-1 ring-red-200',
  };

  return (
    <span
      className={`text-[11px] px-2.5 py-1 rounded-full font-semibold uppercase tracking-wide ${
        config[status] || 'bg-slate-100 text-slate-600 ring-1 ring-slate-200'
      }`}
    >
      {status.replace(/_/g, ' ')}
    </span>
  );
}

export default function Dashboard() {
  const {
    data: cases,
    isLoading,
    isError,
    error,
  } = useQuery<CaseSummary[]>({
    queryKey: ['cases'],
    queryFn: api.listCases,
    refetchInterval: 10000,
  });

  const allCases = cases || [];
  const verifiedCases = allCases.filter((c) => c.status === 'verified');
  const pendingCases = allCases.filter(
    (c) => c.status === 'pending_review' || c.status === 'pending_nlp'
  );
  const processingCases = allCases.filter((c) => c.status === 'processing');
  const failedCases = allCases.filter((c) => c.status === 'failed');

  return (
    <div className="min-h-screen bg-slate-50">
      <div className="max-w-7xl mx-auto px-6 py-8">
        {/* Page header */}
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-slate-900">
            Compliance & Intelligence Dashboard
          </h1>
          <p className="text-sm text-slate-500 mt-1">
            Monitor case processing pipeline and verification status
          </p>
        </div>

        {/* Summary cards */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
          <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-5">
            <p className="text-xs font-semibold uppercase tracking-wider text-slate-400 mb-1">
              Total Cases
            </p>
            <p className="text-3xl font-bold text-slate-800">{allCases.length}</p>
          </div>
          <div className="bg-white rounded-xl shadow-sm border border-emerald-200 p-5">
            <p className="text-xs font-semibold uppercase tracking-wider text-emerald-500 mb-1">
              Verified
            </p>
            <p className="text-3xl font-bold text-emerald-700">{verifiedCases.length}</p>
          </div>
          <div className="bg-white rounded-xl shadow-sm border border-amber-200 p-5">
            <p className="text-xs font-semibold uppercase tracking-wider text-amber-500 mb-1">
              Pending Review
            </p>
            <p className="text-3xl font-bold text-amber-700">{pendingCases.length}</p>
          </div>
          <div className="bg-white rounded-xl shadow-sm border border-red-200 p-5">
            <p className="text-xs font-semibold uppercase tracking-wider text-red-500 mb-1">
              Failed
            </p>
            <p className="text-3xl font-bold text-red-700">{failedCases.length}</p>
          </div>
        </div>

        {isLoading && <LoadingSpinner message="Loading cases…" />}

        {isError && (
          <div className="bg-red-50 border border-red-200 rounded-xl p-6 text-center">
            <p className="text-red-700 font-medium">
              Failed to load cases: {(error as any)?.message || 'Unknown error'}
            </p>
          </div>
        )}

        {!isLoading && !isError && (
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* All Cases Table */}
            <div className="lg:col-span-2 bg-white rounded-xl shadow-sm border border-slate-200 overflow-hidden">
              <div className="px-6 py-4 border-b border-slate-100">
                <h2 className="text-lg font-bold text-slate-800">All Cases</h2>
              </div>

              {allCases.length === 0 ? (
                <div className="px-6 py-12 text-center">
                  <p className="text-slate-400">
                    No cases found. Upload a document to get started.
                  </p>
                </div>
              ) : (
                <div className="overflow-x-auto">
                  <table className="w-full text-left">
                    <thead>
                      <tr className="border-b border-slate-100 bg-slate-50/50">
                        <th className="px-6 py-3 text-xs font-semibold uppercase tracking-wider text-slate-500">
                          Case Number
                        </th>
                        <th className="px-6 py-3 text-xs font-semibold uppercase tracking-wider text-slate-500">
                          Status
                        </th>
                        <th className="px-6 py-3 text-xs font-semibold uppercase tracking-wider text-slate-500">
                          Created
                        </th>
                        <th className="px-6 py-3 text-xs font-semibold uppercase tracking-wider text-slate-500">
                          Actions
                        </th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-100">
                      {allCases.map((c) => (
                        <tr
                          key={c.case_id}
                          className="hover:bg-slate-50/50 transition-colors"
                        >
                          <td className="px-6 py-3.5">
                            <span className="font-medium text-slate-800 text-sm">
                              {c.case_number}
                            </span>
                          </td>
                          <td className="px-6 py-3.5">
                            <StatusBadge status={c.status} />
                          </td>
                          <td className="px-6 py-3.5 text-sm text-slate-500">
                            {c.created_at
                              ? new Date(c.created_at).toLocaleDateString('en-IN', {
                                  day: '2-digit',
                                  month: 'short',
                                  year: 'numeric',
                                })
                              : '—'}
                          </td>
                          <td className="px-6 py-3.5">
                            <a
                              href={`/verify/${c.case_id}`}
                              className="text-xs font-medium text-blue-600 hover:text-blue-800
                                         transition-colors underline-offset-2 hover:underline"
                            >
                              View & Verify →
                            </a>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>

            {/* Hybrid RAG Search panel */}
            <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-6">
              <h2 className="text-lg font-bold text-slate-800 mb-4">
                Hybrid RAG Search
              </h2>
              <input
                type="text"
                placeholder="Search past precedents…"
                className="w-full px-4 py-2.5 border border-slate-300 rounded-lg text-sm
                           focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent
                           transition-shadow mb-3"
              />
              <button className="px-4 py-2 rounded-lg bg-blue-600 hover:bg-blue-700 text-white text-sm font-medium transition-colors">
                Search
              </button>
              <p className="text-xs text-slate-400 mt-4 italic">
                Note: Basic setup mode. Full Llama+FAISS RAG disabled.
              </p>
            </div>

            {/* Quick Stats panel */}
            <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-6">
              <h2 className="text-lg font-bold text-slate-800 mb-4">
                Pipeline Health
              </h2>
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <span className="text-sm text-slate-600">Processing</span>
                  <span className="text-sm font-semibold text-blue-700">
                    {processingCases.length}
                  </span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-sm text-slate-600">Awaiting Review</span>
                  <span className="text-sm font-semibold text-amber-700">
                    {pendingCases.length}
                  </span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-sm text-slate-600">Verified</span>
                  <span className="text-sm font-semibold text-emerald-700">
                    {verifiedCases.length}
                  </span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-sm text-slate-600">Failed</span>
                  <span className="text-sm font-semibold text-red-700">
                    {failedCases.length}
                  </span>
                </div>
                <div className="pt-3 border-t border-slate-100">
                  <div className="w-full bg-slate-100 rounded-full h-2 overflow-hidden">
                    {allCases.length > 0 && (
                      <div
                        className="h-full bg-gradient-to-r from-emerald-500 to-emerald-400 rounded-full transition-all duration-500"
                        style={{
                          width: `${(verifiedCases.length / allCases.length) * 100}%`,
                        }}
                      />
                    )}
                  </div>
                  <p className="text-[11px] text-slate-400 mt-1.5 text-center">
                    {allCases.length > 0
                      ? `${Math.round((verifiedCases.length / allCases.length) * 100)}% completion rate`
                      : 'No cases yet'}
                  </p>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
