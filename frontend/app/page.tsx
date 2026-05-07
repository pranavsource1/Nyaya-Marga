'use client';

import React, { useState, useCallback } from 'react';
import { useDropzone } from 'react-dropzone';
import {
  Upload,
  FileText,
  Activity,
  AlertCircle,
  CheckCircle,
  Loader2,
} from 'lucide-react';
import { api, handleApiError } from '@/lib/api';
import { useQuery } from '@tanstack/react-query';

export default function IntakeWorkspace() {
  const [caseNumber, setCaseNumber] = useState('');
  const [file, setFile] = useState<File | null>(null);
  const [isUploading, setIsUploading] = useState(false);
  const [uploadStatus, setUploadStatus] = useState<{ type: 'success' | 'error'; msg: string } | null>(null);
  const [mounted, setMounted] = useState(false);

  React.useEffect(() => {
    setMounted(true);
  }, []);

  const onDrop = useCallback((acceptedFiles: File[]) => {
    if (acceptedFiles.length > 0) {
      setFile(acceptedFiles[0]);
      setUploadStatus(null);
    }
  }, []);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: { 'application/pdf': ['.pdf'] },
    maxSize: 50 * 1024 * 1024,
    multiple: false,
  });

  const handleUpload = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!file || !caseNumber) return;

    setIsUploading(true);
    setUploadStatus(null);

    try {
      const data = await api.uploadCase(file, caseNumber);
      setUploadStatus({ type: 'success', msg: `Case ${data.case_number} uploaded successfully.` });
      setFile(null);
      setCaseNumber('');
    } catch (error: any) {
      const apiErr = handleApiError(error);
      setUploadStatus({ type: 'error', msg: apiErr.detail });
    } finally {
      setIsUploading(false);
    }
  };

  const { data: health } = useQuery({
    queryKey: ['health'],
    queryFn: () => api.healthCheck(),
    refetchInterval: 10000,
  });

  return (
    <div className="max-w-5xl mx-auto space-y-6 pb-12">
      {/* Page Header */}
      <section>
        <h1 className="text-2xl font-bold text-slate-900 tracking-tight">Upload Judgments</h1>
        <p className="text-sm text-slate-500 mt-1">
          Secure document ingestion &amp; pipeline status
        </p>
      </section>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Upload Card */}
        <div className="lg:col-span-2 bg-white rounded-lg border border-slate-200 overflow-hidden">
          <div className="px-5 py-4 border-b border-slate-100 bg-gov-800">
            <h2 className="text-sm font-bold text-white flex items-center gap-2">
              <Upload className="w-4 h-4 text-ka-gold-400" />
              New Case Ingestion
            </h2>
          </div>
          <form onSubmit={handleUpload} className="p-5 space-y-5">
            <div>
              <label htmlFor="case-number" className="block text-sm font-semibold text-slate-700 mb-1.5">
                Official Case Number
              </label>
              <input
                id="case-number"
                type="text"
                value={caseNumber}
                onChange={(e) => setCaseNumber(e.target.value)}
                placeholder="e.g. WP/4823/2025"
                required
                className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-gov-600 focus:border-transparent transition-shadow"
              />
            </div>

            <div>
              <label className="block text-sm font-semibold text-slate-700 mb-1.5">
                Judgment PDF
              </label>
              {mounted ? (
                <div
                  {...getRootProps()}
                  className={`border-2 border-dashed rounded-lg p-8 text-center cursor-pointer transition-all duration-200
                    ${isDragActive ? 'border-gov-600 bg-gov-50' : 'border-slate-300 hover:border-gov-400 hover:bg-slate-50'}
                    ${file ? 'bg-ka-green-50/30 border-ka-green-300' : ''}`}
                >
                  <input {...getInputProps()} />
                  {file ? (
                    <div className="flex flex-col items-center">
                      <FileText className="w-10 h-10 text-ka-green-600 mb-3" />
                      <span className="text-sm font-semibold text-slate-800">{file.name}</span>
                      <span className="text-xs text-slate-500 mt-1">{(file.size / 1024 / 1024).toFixed(2)} MB</span>
                    </div>
                  ) : (
                    <div className="flex flex-col items-center">
                      <Upload className="w-10 h-10 text-slate-400 mb-3" />
                      <span className="text-sm font-medium text-slate-600">
                        Drag &amp; drop official PDF here, or click to select
                      </span>
                      <span className="text-xs text-slate-400 mt-2">Maximum file size: 50MB</span>
                    </div>
                  )}
                </div>
              ) : (
                <div className="border-2 border-dashed border-slate-200 rounded-lg p-8 h-40 bg-slate-50 animate-pulse" />
              )}
            </div>

            {uploadStatus && (
              <div
                className={`p-3 rounded-lg text-sm font-medium flex items-center gap-2 ${
                  uploadStatus.type === 'success'
                    ? 'bg-ka-green-50 text-ka-green-800 ring-1 ring-ka-green-200'
                    : 'bg-ka-crimson-50 text-ka-crimson-800 ring-1 ring-ka-crimson-200'
                }`}
                role="alert"
              >
                {uploadStatus.type === 'success' ? (
                  <CheckCircle className="w-4 h-4 shrink-0" />
                ) : (
                  <AlertCircle className="w-4 h-4 shrink-0" />
                )}
                {uploadStatus.msg}
              </div>
            )}

            <button
              type="submit"
              disabled={isUploading || !file || !caseNumber}
              className="w-full py-2.5 bg-gov-800 hover:bg-gov-700 text-white rounded-lg font-semibold text-sm transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed flex justify-center items-center gap-2"
            >
              {isUploading ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  Ingesting to Pipeline…
                </>
              ) : (
                'Commence Ingestion'
              )}
            </button>
          </form>
        </div>

        {/* System Health */}
        <div>
          <div className="bg-white rounded-lg border border-slate-200 p-5">
            <h3 className="text-xs font-bold text-slate-800 uppercase tracking-wider mb-4 flex items-center gap-2 border-b border-slate-100 pb-3">
              <Activity className="w-4 h-4 text-ka-gold-500" />
              Backend Health
            </h3>
            <div className="space-y-3">
              {[
                { label: 'Core API', status: health?.status === 'healthy' },
                { label: 'PostgreSQL', status: health?.database === 'connected' },
                { label: 'Redis / Celery', status: health?.celery === 'connected' },
              ].map((service) => (
                <div key={service.label} className="flex justify-between items-center">
                  <span className="text-sm text-slate-600 font-medium">{service.label}</span>
                  <span className={`flex items-center gap-1.5 text-xs font-bold ${service.status ? 'text-ka-green-700' : 'text-ka-crimson-600'}`}>
                    <span className={`w-2 h-2 rounded-full ${service.status ? 'bg-ka-green-500' : 'bg-ka-crimson-500'} animate-pulse`} />
                    {service.status ? 'ONLINE' : 'OFFLINE'}
                  </span>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
