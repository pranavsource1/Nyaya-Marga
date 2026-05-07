'use client';

import { useState, useCallback } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useRouter } from 'next/navigation';
import { api } from '@/lib/api';
import { ActionPlan } from '@/lib/types';
import InteractivePDFViewer from './InteractivePDFViewer';
import FieldCard from './FieldCard';
import ActionPlanDisplay from '@/components/ActionPlanDisplay';
import LoadingSpinner from '@/components/LoadingSpinner';
import {
  ArrowLeft,
  Trash2,
  FileText,
  ListChecks,
  ClipboardList,
  AlertCircle,
  Cpu,
  RefreshCw,
  Loader2,
  CheckCircle2,
  AlertTriangle,
} from 'lucide-react';

interface VerificationScreenProps {
  caseId: string;
}

type RightPanelView = 'entities' | 'action-plan';

export default function VerificationScreen({ caseId }: VerificationScreenProps) {
  const [activeFieldId, setActiveFieldId] = useState<string | null>(null);
  const [rightPanel, setRightPanel] = useState<RightPanelView>('entities');
  const queryClient = useQueryClient();
  const router = useRouter();

  // Fetch case data (entities live here)
  const { data: caseData, isLoading, isError, error } = useQuery({
    queryKey: ['case', caseId],
    queryFn: () => api.getCaseStatus(caseId),
    refetchInterval: (query) => {
      const status = query.state.data?.status;
      if (status === 'processing' || status === 'pending_nlp') return 2000;
      return false;
    },
  });

  // Fetch action plan — returns null if not yet generated (202), polls until ready
  const {
    data: actionPlan,
    isLoading: actionPlanLoading,
    refetch: refetchActionPlan,
  } = useQuery<ActionPlan | null>({
    queryKey: ['action-plan', caseId],
    queryFn: () => api.getActionPlan(caseId),
    refetchInterval: (query) => {
      const plan = query.state.data;
      if (!plan || Object.keys(plan).length === 0) return 3000;
      return false;
    },
    retry: false,
  });

  // Trigger action plan generation
  const generateMutation = useMutation({
    mutationFn: () => api.generateActionPlan(caseId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['action-plan', caseId] });
    },
  });

  // Delete the case
  const deleteMutation = useMutation({
    mutationFn: () => api.deleteCase(caseId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['cases'] });
      router.push('/dashboard');
    },
  });

  const handleDelete = useCallback(() => {
    if (window.confirm('Delete this case permanently? This cannot be undone.')) {
      deleteMutation.mutate();
    }
  }, [deleteMutation]);

  const pdfUrl = api.getCasePdfUrl(caseId);

  /* ── Loading State ── */
  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-[calc(100vh-3.5rem)]">
        <LoadingSpinner message="Loading case data…" />
      </div>
    );
  }

  /* ── Error State ── */
  if (isError) {
    return (
      <div className="flex items-center justify-center h-[calc(100vh-3.5rem)]">
        <div className="bg-white rounded-lg border border-slate-200 p-8 max-w-md text-center">
          <AlertCircle className="w-10 h-10 text-ka-crimson-500 mx-auto mb-3" />
          <h2 className="text-lg font-bold text-slate-800 mb-2">Failed to load case</h2>
          <p className="text-sm text-slate-500 mb-6">
            {(error as any)?.message || 'An unexpected error occurred'}
          </p>
          <a
            href="/dashboard"
            className="inline-flex items-center gap-2 px-5 py-2 rounded-lg bg-gov-800 hover:bg-gov-700 text-white text-sm font-medium transition-all duration-200"
          >
            <ArrowLeft className="w-4 h-4" />
            Back to Dashboard
          </a>
        </div>
      </div>
    );
  }

  if (!caseData) return null;

  const isProcessing = caseData.status === 'processing' || caseData.status === 'pending_nlp';
  const entities = caseData.entities || [];
  const needsReview = entities.filter((e) => e.requires_review).length;
  const verified = entities.filter((e) => !e.requires_review).length;
  const hasActionPlan = !!actionPlan && Object.keys(actionPlan).length > 0;

  // Status badge styling
  const statusConfig: Record<string, string> = {
    pending_review:          'bg-ka-gold-100 text-ka-gold-800',
    pending_verification:    'bg-ka-gold-100 text-ka-gold-800',
    verification_in_progress:'bg-ka-gold-100 text-ka-gold-800',
    verified:                'bg-ka-green-100 text-ka-green-800',
    failed:                  'bg-ka-crimson-100 text-ka-crimson-800',
    processing:              'bg-blue-100 text-blue-800',
    pending_nlp:             'bg-blue-100 text-blue-800',
  };

  const statusBadge = statusConfig[caseData.status] || 'bg-slate-100 text-slate-700';

  return (
    <div className="flex h-[calc(100vh-3.5rem)] overflow-hidden bg-slate-50 -m-6 lg:-m-8">

      {/* ═══════════ LEFT PANEL: PDF Viewer ═══════════ */}
      <div className="w-1/2 flex flex-col h-full border-r border-slate-200">
        {/* Case Header */}
        <div className="shrink-0 px-5 py-3 bg-gov-800">
          <div className="flex items-center justify-between">
            <div>
              <div className="flex items-center gap-1.5 text-ka-gold-400 text-[10px] font-bold uppercase tracking-widest mb-0.5">
                <span>Case Verification</span>
                <span className="text-white/30">›</span>
                <span>{caseData.case_number}</span>
              </div>
              <h2 className="text-base font-bold text-white">{caseData.case_number}</h2>
              <span className={`mt-1.5 inline-block text-[10px] px-2 py-0.5 rounded-md font-semibold uppercase tracking-wide ${statusBadge}`}>
                {caseData.status.replace(/_/g, ' ')}
              </span>
            </div>
            <div className="flex items-center gap-2">
              <a
                href="/dashboard"
                className="inline-flex items-center gap-1.5 text-xs text-white/50 hover:text-white transition-colors duration-200"
              >
                <ArrowLeft className="w-3.5 h-3.5" />
                Dashboard
              </a>
              <button
                onClick={handleDelete}
                disabled={deleteMutation.isPending}
                className="p-1.5 rounded-md bg-white/5 hover:bg-ka-crimson-600/20 text-white/40 hover:text-ka-crimson-300 transition-all duration-200"
                title="Delete case"
              >
                <Trash2 className="w-4 h-4" />
              </button>
            </div>
          </div>
        </div>

        {/* PDF Viewer */}
        <div className="flex-1 overflow-hidden p-3">
          <InteractivePDFViewer
            pdfUrl={pdfUrl}
            entities={entities}
            activeFieldId={activeFieldId}
          />
        </div>
      </div>

      {/* ═══════════ RIGHT PANEL: Entities / Action Plan ═══════════ */}
      <div className="w-1/2 flex flex-col h-full bg-white">
        {/* Tab Bar */}
        <div className="shrink-0 border-b border-slate-200">
          <div className="flex">
            <button
              onClick={() => setRightPanel('entities')}
              className={`flex-1 flex items-center justify-center gap-2 px-4 py-3 text-sm font-semibold transition-all duration-200 relative ${
                rightPanel === 'entities'
                  ? 'text-gov-800'
                  : 'text-slate-400 hover:text-slate-600'
              }`}
              aria-selected={rightPanel === 'entities'}
              role="tab"
            >
              <ListChecks className="w-4 h-4" />
              Extracted Entities
              <span className="text-[11px] font-normal text-slate-400">({entities.length})</span>
              {rightPanel === 'entities' && (
                <span className="absolute bottom-0 left-4 right-4 h-0.5 bg-gov-800 rounded-full" />
              )}
            </button>
            <button
              onClick={() => setRightPanel('action-plan')}
              className={`flex-1 flex items-center justify-center gap-2 px-4 py-3 text-sm font-semibold transition-all duration-200 relative ${
                rightPanel === 'action-plan'
                  ? 'text-gov-800'
                  : 'text-slate-400 hover:text-slate-600'
              }`}
              aria-selected={rightPanel === 'action-plan'}
              role="tab"
            >
              <ClipboardList className="w-4 h-4" />
              Action Plan
              {hasActionPlan && (
                <span className="w-2 h-2 rounded-full bg-ka-green-500" />
              )}
              {rightPanel === 'action-plan' && (
                <span className="absolute bottom-0 left-4 right-4 h-0.5 bg-gov-800 rounded-full" />
              )}
            </button>
          </div>

          {/* Stats row — entities tab only */}
          {rightPanel === 'entities' && entities.length > 0 && (
            <div className="px-5 py-2 flex items-center gap-4 text-[11px] border-t border-slate-100 bg-slate-50/50">
              <span className="flex items-center gap-1.5 text-slate-600">
                <span className="w-1.5 h-1.5 rounded-full bg-blue-500" />
                {entities.length} total
              </span>
              {needsReview > 0 && (
                <span className="flex items-center gap-1.5 text-ka-gold-700">
                  <span className="w-1.5 h-1.5 rounded-full bg-ka-gold-500" />
                  {needsReview} need review
                </span>
              )}
              <span className="flex items-center gap-1.5 text-ka-green-700">
                <span className="w-1.5 h-1.5 rounded-full bg-ka-green-500" />
                {verified} verified
              </span>
            </div>
          )}
        </div>

        {/* Panel Content */}
        <div className="flex-1 overflow-y-auto p-5" role="tabpanel">
          {rightPanel === 'entities' ? (
            /* ── Entities List ── */
            <div className="space-y-3">
              {isProcessing ? (
                <div className="flex flex-col items-center justify-center h-48 gap-3">
                  <LoadingSpinner message="Processing document…" />
                  <p className="text-xs text-slate-400">Extracting entities from your PDF. This may take a minute.</p>
                </div>
              ) : entities.length === 0 ? (
                <div className="flex flex-col items-center justify-center h-48 text-center gap-3">
                  <FileText className="w-10 h-10 text-slate-300" />
                  <p className="text-sm font-medium text-slate-500">No entities extracted yet</p>
                  <p className="text-xs text-slate-400 max-w-xs">
                    The NLP pipeline didn&apos;t find entities in this document, or processing is still queued.
                  </p>
                </div>
              ) : (
                entities.map((entity) => (
                  <FieldCard
                    key={entity.id}
                    entity={entity}
                    caseId={caseId}
                    isActive={activeFieldId === String(entity.id)}
                    onHover={setActiveFieldId}
                  />
                ))
              )}
            </div>
          ) : (
            /* ── Action Plan ── */
            <div className="space-y-4">
              {/* Generate / Refresh controls */}
              <div className="flex items-center gap-3 pb-3 border-b border-slate-100">
                <button
                  onClick={() => generateMutation.mutate()}
                  disabled={generateMutation.isPending || entities.length === 0}
                  className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-gov-800 hover:bg-gov-700
                             text-white text-sm font-medium transition-all duration-200 shadow-sm
                             disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {generateMutation.isPending ? (
                    <>
                      <Loader2 className="w-4 h-4 animate-spin" />
                      Generating…
                    </>
                  ) : (
                    <>
                      <Cpu className="w-4 h-4" />
                      {hasActionPlan ? 'Regenerate' : 'Generate'} Action Plan
                    </>
                  )}
                </button>

                {hasActionPlan && (
                  <button
                    onClick={() => refetchActionPlan()}
                    className="inline-flex items-center gap-1.5 px-3 py-2 rounded-lg border border-slate-200 text-slate-600 hover:bg-slate-50 text-xs font-medium transition-all duration-200"
                  >
                    <RefreshCw className="w-3.5 h-3.5" />
                    Refresh
                  </button>
                )}
              </div>

              {generateMutation.isError && (
                <div className="flex items-center gap-2 p-3 rounded-lg bg-ka-crimson-50 border border-ka-crimson-200 text-ka-crimson-700 text-sm">
                  <AlertTriangle className="w-4 h-4 shrink-0" />
                  Failed to trigger generation. Ensure entities are extracted first.
                </div>
              )}

              {generateMutation.isSuccess && !hasActionPlan && (
                <div className="flex items-center gap-2 p-3 rounded-lg bg-blue-50 border border-blue-200 text-blue-700 text-sm">
                  <Loader2 className="w-4 h-4 animate-spin shrink-0" />
                  Action plan is being generated… Checking every few seconds.
                </div>
              )}

              {/* Action plan content */}
              {actionPlanLoading ? (
                <LoadingSpinner message="Loading action plan…" />
              ) : hasActionPlan ? (
                <div>
                  <div className="mb-3 flex items-center gap-2">
                    <span className="inline-flex items-center gap-1 text-xs font-semibold text-ka-green-700 bg-ka-green-50 px-2.5 py-1 rounded-md ring-1 ring-ka-green-200">
                      <CheckCircle2 className="w-3 h-3" />
                      Generated
                    </span>
                  </div>
                  <ActionPlanDisplay plan={actionPlan!} />
                </div>
              ) : !generateMutation.isSuccess ? (
                <div className="flex flex-col items-center justify-center py-16 text-center gap-3">
                  <ClipboardList className="w-12 h-12 text-slate-300" />
                  <p className="text-sm font-semibold text-slate-600">No Action Plan Yet</p>
                  <p className="text-xs text-slate-400 max-w-xs">
                    Click &quot;Generate Action Plan&quot; to create a structured compliance assessment,
                    litigation ROI, statutory timeline, and action directives.
                  </p>
                </div>
              ) : null}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
