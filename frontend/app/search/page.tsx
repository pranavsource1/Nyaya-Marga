'use client';

import { FormEvent, useState } from 'react';
import { api, handleApiError } from '@/lib/api';
import { AlertCircle, Loader2, Search } from 'lucide-react';

export default function SearchPage() {
  const [query, setQuery] = useState('');
  const [result, setResult] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);
  const [isSearching, setIsSearching] = useState(false);

  const handleSubmit = async (event: FormEvent) => {
    event.preventDefault();
    if (!query.trim()) return;

    setIsSearching(true);
    setError(null);
    setResult(null);

    try {
      setResult(await api.ragSearch(query.trim()));
    } catch (err) {
      setError(handleApiError(err).detail);
    } finally {
      setIsSearching(false);
    }
  };

  const precedents = result?.precedents || [];

  return (
    <div className="max-w-5xl mx-auto space-y-6 pb-12">
      <section>
        <h1 className="text-2xl font-bold text-slate-900 tracking-tight">Precedent Search</h1>
        <p className="text-sm text-slate-500 mt-1">Search the backend RAG index for verified legal context.</p>
      </section>

      <section className="bg-white rounded-lg border border-slate-200 overflow-hidden">
        <div className="px-5 py-4 border-b border-slate-100 flex items-center gap-2">
          <Search className="w-4 h-4 text-gov-700" />
          <h2 className="text-sm font-bold text-slate-800">Knowledge Base Query</h2>
        </div>
        <form onSubmit={handleSubmit} className="p-5 flex gap-2">
          <input
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="Search verified judgments, statutory issues, or compliance questions..."
            className="flex-1 min-w-0 px-3 py-2 rounded-lg border border-slate-300 text-sm focus:outline-none focus:ring-2 focus:ring-gov-600"
          />
          <button
            type="submit"
            disabled={isSearching || !query.trim()}
            className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-gov-800 hover:bg-gov-700 text-white text-sm font-medium disabled:opacity-50"
          >
            {isSearching ? <Loader2 className="w-4 h-4 animate-spin" /> : <Search className="w-4 h-4" />}
            Search
          </button>
        </form>
      </section>

      {error && (
        <div className="rounded-lg border border-ka-crimson-200 bg-ka-crimson-50 p-4 text-sm text-ka-crimson-800 flex gap-2">
          <AlertCircle className="w-4 h-4 shrink-0 mt-0.5" />
          {error}
        </div>
      )}

      {result && (
        <section className="bg-white rounded-lg border border-slate-200 overflow-hidden">
          <div className="px-5 py-4 border-b border-slate-100">
            <h2 className="text-sm font-bold text-slate-800">Backend Results</h2>
            <p className="text-xs text-slate-500 mt-1">
              Semantic hits: {result.retrieval_stats?.semantic_hits || 0} / Keyword hits:{' '}
              {result.retrieval_stats?.keyword_hits || 0}
            </p>
          </div>
          <div className="p-5 space-y-4">
            <div className="rounded-lg bg-slate-50 border border-slate-200 p-4">
              <h3 className="text-xs font-bold text-slate-500 uppercase tracking-wider mb-2">Synthesis</h3>
              <p className="text-sm text-slate-800 leading-relaxed">
                {result.synthesis?.guidance || 'No synthesis returned by backend.'}
              </p>
            </div>

            <div className="space-y-3">
              <h3 className="text-xs font-bold text-slate-500 uppercase tracking-wider">Precedents</h3>
              {precedents.length === 0 ? (
                <p className="text-sm text-slate-500">No precedents returned for this query.</p>
              ) : (
                precedents.map((precedent: string, index: number) => (
                  <div key={`${index}-${precedent.slice(0, 24)}`} className="rounded-lg border border-slate-200 p-4">
                    <p className="text-sm text-slate-700 whitespace-pre-wrap">{precedent}</p>
                  </div>
                ))
              )}
            </div>
          </div>
        </section>
      )}
    </div>
  );
}
