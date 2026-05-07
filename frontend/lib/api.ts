import axios, { AxiosInstance } from 'axios';
import {
  CaseUploadResponse,
  CaseStatusResponse,
  CaseSummary,
  UpdateEntityPayload,
  ActionPlan,
  DashboardStats,
  AuditLogEntry,
  UserSummary,
  ApiError,
} from './types';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

const axiosInstance: AxiosInstance = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
});

export const api = {
  // Upload PDF case
  uploadCase: async (
    file: File,
    caseNumber: string
  ): Promise<CaseUploadResponse> => {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('case_number', caseNumber);

    const response = await axiosInstance.post('/api/v1/cases/upload', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    return response.data;
  },

  // Get case status and extracted entities
  getCaseStatus: async (caseId: string): Promise<CaseStatusResponse> => {
    const response = await axiosInstance.get(`/api/v1/cases/${caseId}/status`);
    return response.data;
  },

  // List all cases for dashboard
  listCases: async (): Promise<CaseSummary[]> => {
    const response = await axiosInstance.get('/api/v1/dashboard/cases');
    return response.data;
  },

  // Get dashboard statistics
  getDashboardStats: async (): Promise<DashboardStats> => {
    const response = await axiosInstance.get('/api/v1/dashboard/stats');
    return response.data;
  },

  // Update entity (approve/reject/edit)
  updateEntity: async (
    caseId: string,
    entityId: string,
    data: UpdateEntityPayload
  ): Promise<any> => {
    const response = await axiosInstance.patch(
      `/api/v1/cases/${caseId}/entities/${entityId}`,
      data
    );
    return response.data;
  },

  // Get generated action plan
  getActionPlan: async (caseId: string): Promise<ActionPlan | null> => {
    try {
      const response = await axiosInstance.get(
        `/api/v1/cases/${caseId}/action-plan`
      );
      return response.data;
    } catch (error: any) {
      // 202 means "still generating" — not an error, just not ready yet
      if (error?.response?.status === 202 || error?.response?.status === 404) {
        return null;
      }
      throw error;
    }
  },

  // Trigger action plan generation
  generateActionPlan: async (caseId: string) => {
    const response = await axiosInstance.post(
      `/api/v1/cases/${caseId}/generate-action-plan`
    );
    return response.data;
  },

  // Get PDF URL for a case
  getCasePdfUrl: (caseId: string): string => {
    return `${API_BASE_URL}/api/v1/cases/${caseId}/pdf`;
  },

  // Health check
  healthCheck: async () => {
    const response = await axiosInstance.get('/api/v1/health');
    return response.data;
  },

  // RAG Search
  ragSearch: async (query: string, token?: string) => {
    const response = await axiosInstance.get('/api/v1/search/rag', {
      params: { query },
      headers: token ? { Authorization: `Bearer ${token}` } : undefined,
    });
    return response.data;
  },

  // Authentication
  login: async (email: string, password: string) => {
    const response = await axiosInstance.post('/api/v1/auth/token', { email, password });
    return response.data;
  },

  getMe: async (token: string) => {
    const response = await axiosInstance.get('/api/v1/auth/me', {
      headers: { Authorization: `Bearer ${token}` }
    });
    return response.data;
  },

  // Delete a case
  deleteCase: async (caseId: string) => {
    const response = await axiosInstance.delete(`/api/v1/cases/${caseId}`);
    return response.data;
  },

  listAuditLogs: async (): Promise<AuditLogEntry[]> => {
    const response = await axiosInstance.get('/api/v1/dashboard/audit');
    return response.data;
  },

  listUsers: async (): Promise<UserSummary[]> => {
    const response = await axiosInstance.get('/api/v1/dashboard/users');
    return response.data;
  },
};

// Error handler utility
export const handleApiError = (error: any): ApiError => {
  if (axios.isAxiosError(error)) {
    let detail = error.message;

    // Handle Pydantic validation errors (422)
    if (error.response?.status === 422 && error.response?.data?.detail) {
      const details = error.response.data.detail;
      if (Array.isArray(details)) {
        detail = details.map((d: any) => `${d.loc?.[1] || 'Field'}: ${d.msg}`).join('; ');
      } else if (typeof details === 'string') {
        detail = details;
      }
    }
    // Handle standard API errors
    else if (error.response?.data?.detail) {
      if (typeof error.response.data.detail === 'string') {
        detail = error.response.data.detail;
      } else if (Array.isArray(error.response.data.detail)) {
        detail = error.response.data.detail.map((d: any) =>
          typeof d === 'string' ? d : d.msg || JSON.stringify(d)
        ).join('; ');
      }
    }

    return {
      detail: detail || 'An error occurred',
      status: error.response?.status || 500,
    };
  }
  return {
    detail: 'An unexpected error occurred',
    status: 500,
  };
};
