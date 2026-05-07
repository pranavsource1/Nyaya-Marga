'use client';

import React, { useState } from 'react';
import { api, handleApiError } from '@/lib/api';

interface PdfUploadFormProps {
  onSuccess: (response: any) => void;
  onError: (error: string) => void;
}

export default function PdfUploadForm({ onSuccess, onError }: PdfUploadFormProps) {
  const [file, setFile] = useState<File | null>(null);
  const [caseNumber, setCaseNumber] = useState('');
  const [loading, setLoading] = useState(false);
  const [fileName, setFileName] = useState('');

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const selectedFile = e.target.files?.[0];
    if (selectedFile) {
      if (selectedFile.type !== 'application/pdf') {
        onError('Please select a PDF file');
        return;
      }
      setFile(selectedFile);
      setFileName(selectedFile.name);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!file) {
      onError('Please select a PDF file');
      return;
    }

    if (!caseNumber.trim()) {
      onError('Please enter a case number');
      return;
    }

    setLoading(true);

    try {
      const response = await api.uploadCase(file, caseNumber);
      onSuccess(response);
    } catch (err) {
      const apiError = handleApiError(err);
      onError(apiError.detail);
    } finally {
      setLoading(false);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="card space-y-6 max-w-md">
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-2">
          Case Number *
        </label>
        <input
          type="text"
          value={caseNumber}
          onChange={(e) => setCaseNumber(e.target.value)}
          placeholder="e.g., CASE-2024-001"
          className="input-field"
          disabled={loading}
        />
      </div>

      <div>
        <label className="block text-sm font-medium text-gray-700 mb-2">
          PDF Document *
        </label>
        <div className="border-2 border-dashed border-gray-300 rounded-lg p-6 text-center hover:border-blue-500 hover:bg-blue-50 transition-colors cursor-pointer">
          <input
            type="file"
            accept="application/pdf"
            onChange={handleFileChange}
            className="hidden"
            id="pdf-input"
            disabled={loading}
          />
          <label htmlFor="pdf-input" className="cursor-pointer">
            <div className="text-4xl mb-2">📄</div>
            <p className="text-gray-600">
              {fileName || 'Click to select PDF or drag and drop'}
            </p>
            <p className="text-xs text-gray-400 mt-2">Maximum file size: 50MB</p>
          </label>
        </div>
      </div>

      <button
        type="submit"
        disabled={!file || !caseNumber.trim() || loading}
        className="w-full button button-primary disabled:opacity-50 py-3 font-semibold"
      >
        {loading ? 'Uploading...' : 'Upload & Process'}
      </button>
    </form>
  );
}
