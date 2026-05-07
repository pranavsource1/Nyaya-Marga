'use client';

import { useState } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { Entity, UpdateEntityPayload } from '@/lib/types';
import { api } from '@/lib/api';
import {
  CheckCircle,
  Pencil,
  X,
  Save,
  Loader2,
  AlertTriangle,
  FileText,
} from 'lucide-react';

interface FieldCardProps {
  entity: Entity;
  caseId: string;
  isActive: boolean;
  onHover: (id: string | null) => void;
}

function ConfidenceBadge({ score }: { score: number }) {
  const pct = Math.round(score * 100);

  let classes: string;
  let label: string;

  if (pct < 75) {
    classes = 'bg-ka-crimson-50 text-ka-crimson-700 ring-1 ring-ka-crimson-200';
    label = 'Review required';
  } else if (pct < 90) {
    classes = 'bg-ka-gold-50 text-ka-gold-700 ring-1 ring-ka-gold-200';
    label = 'Acceptable';
  } else {
    classes = 'bg-ka-green-50 text-ka-green-700 ring-1 ring-ka-green-200';
    label = 'High confidence';
  }

  return (
    <span className={`text-[10px] px-2 py-0.5 rounded-md font-semibold ${classes}`}>
      {pct}% — {label}
    </span>
  );
}

export default function FieldCard({ entity, caseId, isActive, onHover }: FieldCardProps) {
  const [editMode, setEditMode] = useState(false);
  const [editValue, setEditValue] = useState(entity.extracted_text);
  const queryClient = useQueryClient();

  const mutation = useMutation({
    mutationFn: (payload: UpdateEntityPayload) =>
      api.updateEntity(caseId, String(entity.id), payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['case', caseId] });
    },
  });

  const handleApprove = () => {
    mutation.mutate({ status: 'VERIFIED' });
  };

  const handleSaveEdit = () => {
    mutation.mutate({
      extracted_value: editValue,
      status: 'VERIFIED',
    });
    setEditMode(false);
  };

  const handleReject = () => {
    mutation.mutate({ status: 'REJECTED' });
  };

  // Border and background based on state
  const borderClass = isActive
    ? 'ring-2 ring-gov-600 shadow-sm'
    : entity.requires_review
    ? 'ring-1 ring-ka-gold-300'
    : 'ring-1 ring-slate-200';

  const bgClass = mutation.isSuccess
    ? 'bg-ka-green-50/50'
    : entity.requires_review
    ? 'bg-ka-gold-50/30'
    : 'bg-white';

  return (
    <div
      onMouseEnter={() => onHover(String(entity.id))}
      onMouseLeave={() => onHover(null)}
      className={`rounded-lg p-4 cursor-pointer transition-all duration-200 ${borderClass} ${bgClass}`}
    >
      {/* Header row */}
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-2">
          <span className="text-[10px] font-bold text-slate-500 uppercase tracking-wider">
            {entity.entity_type.replace(/_/g, ' ')}
          </span>
          {entity.requires_review && (
            <AlertTriangle className="w-3.5 h-3.5 text-ka-gold-500" />
          )}
        </div>
        <ConfidenceBadge score={entity.confidence_score} />
      </div>

      {/* Extracted Value */}
      {editMode ? (
        <textarea
          value={editValue}
          onChange={(e) => setEditValue(e.target.value)}
          onClick={(e) => e.stopPropagation()}
          className="w-full min-h-[60px] text-sm p-2.5 rounded-lg border border-slate-300 bg-white
                     focus:outline-none focus:ring-2 focus:ring-gov-600 focus:border-transparent
                     resize-y transition-shadow"
        />
      ) : (
        <p className="text-sm text-slate-800 leading-relaxed break-words">
          {entity.extracted_text}
        </p>
      )}

      {/* Bounding box page info */}
      {entity.bounding_box_coords && (
        <div className="flex items-center gap-1 mt-1.5 text-[11px] text-slate-400">
          <FileText className="w-3 h-3" />
          Page {entity.bounding_box_coords.page + 1}
        </div>
      )}

      {/* Action buttons */}
      {isActive && (
        <div
          className="flex items-center gap-2 mt-3 pt-3 border-t border-slate-100"
          onClick={(e) => e.stopPropagation()}
        >
          {mutation.isPending ? (
            <span className="text-xs text-slate-400 flex items-center gap-1.5">
              <Loader2 className="w-3.5 h-3.5 animate-spin" />
              Saving…
            </span>
          ) : mutation.isSuccess ? (
            <span className="text-xs text-ka-green-700 font-medium flex items-center gap-1">
              <CheckCircle className="w-3.5 h-3.5" />
              Updated
            </span>
          ) : !editMode ? (
            <>
              <button
                onClick={handleApprove}
                className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-md bg-ka-green-600 hover:bg-ka-green-700
                           text-white text-xs font-medium transition-all duration-200"
              >
                <CheckCircle className="w-3 h-3" />
                Approve
              </button>
              <button
                onClick={() => setEditMode(true)}
                className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-md bg-gov-700 hover:bg-gov-600
                           text-white text-xs font-medium transition-all duration-200"
              >
                <Pencil className="w-3 h-3" />
                Edit
              </button>
              <button
                onClick={handleReject}
                className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-md bg-ka-crimson-600 hover:bg-ka-crimson-700
                           text-white text-xs font-medium transition-all duration-200"
              >
                <X className="w-3 h-3" />
                Reject
              </button>
            </>
          ) : (
            <>
              <button
                onClick={handleSaveEdit}
                className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-md bg-ka-green-600 hover:bg-ka-green-700
                           text-white text-xs font-medium transition-all duration-200"
              >
                <Save className="w-3 h-3" />
                Save Edit
              </button>
              <button
                onClick={() => {
                  setEditMode(false);
                  setEditValue(entity.extracted_text);
                }}
                className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-md bg-slate-200 hover:bg-slate-300
                           text-slate-700 text-xs font-medium transition-all duration-200"
              >
                Cancel
              </button>
            </>
          )}

          {mutation.isError && (
            <span className="text-xs text-ka-crimson-600 ml-auto">Failed to save</span>
          )}
        </div>
      )}
    </div>
  );
}
