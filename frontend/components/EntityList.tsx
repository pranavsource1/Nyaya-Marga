'use client';

import React from 'react';
import { Entity } from '@/lib/types';

interface EntityListProps {
  entities: Entity[];
}

const getEntityColor = (entityType: string): string => {
  const colors: Record<string, string> = {
    PERSON: 'bg-blue-100 text-blue-800 border-blue-300',
    LOCATION: 'bg-green-100 text-green-800 border-green-300',
    DATE: 'bg-purple-100 text-purple-800 border-purple-300',
    ORGANIZATION: 'bg-yellow-100 text-yellow-800 border-yellow-300',
    MONETARY: 'bg-red-100 text-red-800 border-red-300',
    STATUTE: 'bg-indigo-100 text-indigo-800 border-indigo-300',
    DEFAULT: 'bg-gray-100 text-gray-800 border-gray-300',
  };
  return colors[entityType] || colors.DEFAULT;
};

export default function EntityList({ entities }: EntityListProps) {
  if (entities.length === 0) {
    return (
      <div className="card text-center py-12 bg-yellow-50 border border-yellow-200">
        <p className="text-yellow-800">
          No entities extracted yet. Processing is ongoing...
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between mb-6">
        <h3 className="text-lg font-semibold">Total Entities: {entities.length}</h3>
        <div className="flex gap-2 flex-wrap justify-end">
          {Array.from(new Set(entities.map(e => e.entity_type))).map(type => (
            <span key={type} className={`text-xs px-2 py-1 rounded border ${getEntityColor(type)}`}>
              {type}
            </span>
          ))}
        </div>
      </div>

      <div className="grid gap-4">
        {entities.map((entity) => (
          <div
            key={entity.id}
            className={`card border-l-4 ${
              entity.requires_review ? 'border-l-orange-500 bg-orange-50' : 'border-l-green-500'
            }`}
          >
            <div className="flex items-start justify-between gap-4">
              <div className="flex-1">
                <div className="flex items-center gap-2 mb-2">
                  <span className={`text-xs px-2 py-1 rounded border font-semibold ${getEntityColor(entity.entity_type)}`}>
                    {entity.entity_type}
                  </span>
                  {entity.requires_review && (
                    <span className="text-xs bg-orange-200 text-orange-800 px-2 py-1 rounded">
                      Requires Review
                    </span>
                  )}
                </div>
                <p className="text-gray-800 font-medium break-words">
                  {entity.extracted_text}
                </p>
                <p className="text-sm text-gray-500 mt-2">
                  Confidence: <span className="font-semibold">{(entity.confidence_score * 100).toFixed(1)}%</span>
                </p>
                {entity.bounding_box_coords && (
                  <p className="text-xs text-gray-400 mt-1">
                    Page {entity.bounding_box_coords.page + 1}
                  </p>
                )}
              </div>
              <div className="text-right text-sm text-gray-500">
                {new Date(entity.created_at).toLocaleDateString()}
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
