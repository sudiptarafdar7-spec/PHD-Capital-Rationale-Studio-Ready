const API_BASE_URL = '';

export const API_ENDPOINTS = {
  auth: {
    login: `${API_BASE_URL}/api/v1/auth/login`,
    logout: `${API_BASE_URL}/api/v1/auth/logout`,
    me: `${API_BASE_URL}/api/v1/auth/me`,
  },
  users: {
    getAll: `${API_BASE_URL}/api/v1/users`,
    getOne: (id: string) => `${API_BASE_URL}/api/v1/users/${id}`,
    create: `${API_BASE_URL}/api/v1/users`,
    update: (id: string) => `${API_BASE_URL}/api/v1/users/${id}`,
    delete: (id: string) => `${API_BASE_URL}/api/v1/users/${id}`,
    changePassword: (id: string) => `${API_BASE_URL}/api/v1/users/${id}/password`,
  },
  apiKeys: {
    base: `${API_BASE_URL}/api/v1/api-keys`,
    get: `${API_BASE_URL}/api/v1/api-keys`,
    update: `${API_BASE_URL}/api/v1/api-keys`,
    delete: (provider: string) => `${API_BASE_URL}/api/v1/api-keys/${provider}`,
  },
  pdfTemplate: {
    get: `${API_BASE_URL}/api/v1/pdf-template`,
    update: `${API_BASE_URL}/api/v1/pdf-template`,
  },
  uploadedFiles: {
    getAll: `${API_BASE_URL}/api/v1/uploaded-files`,
    upload: `${API_BASE_URL}/api/v1/uploaded-files/upload`,
    delete: (id: number) => `${API_BASE_URL}/api/v1/uploaded-files/${id}`,
    download: (id: number) => `${API_BASE_URL}/api/v1/uploaded-files/download/${id}`,
    masterStocks: (query: string) => `${API_BASE_URL}/api/v1/uploaded-files/master-stocks?q=${encodeURIComponent(query)}`,
  },
  channels: {
    getAll: `${API_BASE_URL}/api/v1/channels`,
    create: `${API_BASE_URL}/api/v1/channels`,
    update: (id: number) => `${API_BASE_URL}/api/v1/channels/${id}`,
    delete: (id: number) => `${API_BASE_URL}/api/v1/channels/${id}`,
  },
  mediaRationale: {
    fetchVideo: `${API_BASE_URL}/api/v1/media-rationale/fetch-video`,
    startAnalysis: `${API_BASE_URL}/api/v1/media-rationale/start-analysis`,
    getJob: (jobId: string) => `${API_BASE_URL}/api/v1/media-rationale/job/${jobId}`,
    restartStep: (jobId: string, stepNumber: number) => `${API_BASE_URL}/api/v1/media-rationale/restart-step/${jobId}/${stepNumber}`,
    getCsv: (jobId: string) => `${API_BASE_URL}/api/v1/media-rationale/job/${jobId}/csv`,
    updateCsv: (jobId: string) => `${API_BASE_URL}/api/v1/media-rationale/job/${jobId}/csv`,
    generatePdf: (jobId: string) => `${API_BASE_URL}/api/v1/media-rationale/job/${jobId}/generate-pdf`,
    save: (jobId: string) => `${API_BASE_URL}/api/v1/saved-rationale/save`,
    uploadSigned: (jobId: string) => `${API_BASE_URL}/api/v1/saved-rationale/upload-signed`,
    downloadPdf: (filePath: string) => `${API_BASE_URL}/api/v1/saved-rationale/download/${encodeURIComponent(filePath)}`,
    deleteJob: (jobId: string) => `${API_BASE_URL}/api/v1/media-rationale/job/${jobId}`,
    csvPreview: (jobId: string) => `${API_BASE_URL}/api/v1/media-rationale/job/${jobId}/csv-preview`,
    downloadCsv: (jobId: string) => `${API_BASE_URL}/api/v1/media-rationale/job/${jobId}/download-csv`,
    uploadCsv: (jobId: string) => `${API_BASE_URL}/api/v1/media-rationale/job/${jobId}/upload-csv`,
    continuePipeline: (jobId: string) => `${API_BASE_URL}/api/v1/media-rationale/job/${jobId}/continue-pipeline`,
  },
  premiumRationale: {
    createJob: `${API_BASE_URL}/api/v1/premium-rationale/create-job`,
    getJob: (jobId: string) => `${API_BASE_URL}/api/v1/premium-rationale/jobs/${jobId}`,
    downloadCsv: (jobId: string) => `${API_BASE_URL}/api/v1/premium-rationale/jobs/${jobId}/csv`,
    uploadCsv: (jobId: string) => `${API_BASE_URL}/api/v1/premium-rationale/jobs/${jobId}/upload-csv`,
    continueToPdf: (jobId: string) => `${API_BASE_URL}/api/v1/premium-rationale/jobs/${jobId}/continue-to-pdf`,
    save: (jobId: string) => `${API_BASE_URL}/api/v1/premium-rationale/job/${jobId}/save`,
    uploadSigned: (jobId: string) => `${API_BASE_URL}/api/v1/saved-rationale/upload-signed`,
    downloadPdf: (filePath: string) => `${API_BASE_URL}/api/v1/saved-rationale/download/${encodeURIComponent(filePath)}`,
    deleteJob: (jobId: string) => `${API_BASE_URL}/api/v1/premium-rationale/jobs/${jobId}`,
    restartStep: (jobId: string, stepNumber: number) => `${API_BASE_URL}/api/v1/premium-rationale/restart-step/${jobId}/${stepNumber}`,
  },
  manualRationale: {
    createJob: `${API_BASE_URL}/api/v1/manual-rationale/create-job`,
    getJob: (jobId: string) => `${API_BASE_URL}/api/v1/manual-rationale/jobs/${jobId}`,
    save: (jobId: string) => `${API_BASE_URL}/api/v1/manual-rationale/job/${jobId}/save`,
    uploadSigned: (jobId: string) => `${API_BASE_URL}/api/v1/saved-rationale/upload-signed`,
    downloadPdf: (filePath: string) => `${API_BASE_URL}/api/v1/saved-rationale/download/${encodeURIComponent(filePath)}`,
    deleteJob: (jobId: string) => `${API_BASE_URL}/api/v1/manual-rationale/jobs/${jobId}`,
    restartStep: (jobId: string, stepNumber: number) => `${API_BASE_URL}/api/v1/manual-rationale/restart-step/${jobId}/${stepNumber}`,
  },
  manualV2: {
    stocks: (query: string) => `${API_BASE_URL}/api/v1/manual-v2/stocks?q=${encodeURIComponent(query)}`,
    createJob: `${API_BASE_URL}/api/v1/manual-v2/jobs`,
    getJob: (jobId: string) => `${API_BASE_URL}/api/v1/manual-v2/jobs/${jobId}`,
    runPipeline: (jobId: string) => `${API_BASE_URL}/api/v1/manual-v2/jobs/${jobId}/run`,
    getSteps: (jobId: string) => `${API_BASE_URL}/api/v1/manual-v2/jobs/${jobId}/steps`,
    save: (jobId: string) => `${API_BASE_URL}/api/v1/manual-v2/jobs/${jobId}/save`,
    uploadSigned: (jobId: string) => `${API_BASE_URL}/api/v1/manual-v2/jobs/${jobId}/upload-signed`,
    downloadPdf: (jobId: string) => `${API_BASE_URL}/api/v1/manual-v2/jobs/${jobId}/download`,
  },
  savedRationale: {
    getAll: `${API_BASE_URL}/api/v1/saved-rationale`,
    getOne: (id: number) => `${API_BASE_URL}/api/v1/saved-rationale/${id}`,
    save: `${API_BASE_URL}/api/v1/saved-rationale/save`,
    uploadSigned: `${API_BASE_URL}/api/v1/saved-rationale/upload-signed`,
    downloadPdf: (filePath: string) => `${API_BASE_URL}/api/v1/saved-rationale/download/${encodeURIComponent(filePath)}`,
  },
  activityLogs: {
    getAll: `${API_BASE_URL}/api/v1/activity-logs`,
    create: `${API_BASE_URL}/api/v1/activity-logs`,
  },
};

export const getAuthHeaders = (token?: string) => {
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
  };
  
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }
  
  return headers;
};
