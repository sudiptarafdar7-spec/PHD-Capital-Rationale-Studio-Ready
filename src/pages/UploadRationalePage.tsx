import React, { useState, useEffect, useRef } from 'react';
import { Upload, FileAudio, FileText, Calendar, Clock, Building2, Download, Save, CheckCircle2, Trash2 } from 'lucide-react';
import { Button } from '../components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { toast } from 'sonner';
import { API_ENDPOINTS, getAuthHeaders } from '../lib/api-config';
import { useAuth } from '../lib/auth-context';
import AIStyleJobRunner from '../components/AIStyleJobRunner';
import { getUploadStepConfig, getUploadTotalSteps } from '../lib/ai-steps-config';

interface UploadRationalePageProps {
  onNavigate: (page: string, jobId?: string) => void;
  selectedJobId?: string;
}

type WorkflowStage = 'input' | 'processing' | 'csv-review' | 'pdf-preview' | 'completed' | 'saved';

interface JobStep {
  step_number: number;
  step_name: string;
  status: 'pending' | 'running' | 'success' | 'failed';
  message?: string;
  outputFiles?: string[];
  startedAt?: string;
  endedAt?: string;
}

export default function UploadRationalePage({ onNavigate, selectedJobId }: UploadRationalePageProps) {
  const { token } = useAuth();
  
  // Form state
  const [title, setTitle] = useState('');
  const [channelName, setChannelName] = useState('');
  const [uploadDate, setUploadDate] = useState('');
  const [uploadTime, setUploadTime] = useState('');
  const [audioFile, setAudioFile] = useState<File | null>(null);
  const [captionFile, setCaptionFile] = useState<File | null>(null);
  
  // Workflow state
  const [workflowStage, setWorkflowStage] = useState<WorkflowStage>('input');
  const [currentJobId, setCurrentJobId] = useState<string | null>(null);
  const [jobStatus, setJobStatus] = useState<string>('');
  const [jobSteps, setJobSteps] = useState<JobStep[]>([]);
  const [currentStepNumber, setCurrentStepNumber] = useState(0);
  const [progressPercent, setProgressPercent] = useState(0);
  const [pdfPath, setPdfPath] = useState<string | null>(null);
  const [pdfBlobUrl, setPdfBlobUrl] = useState<string | null>(null);
  const [csvData, setCsvData] = useState<any[]>([]);
  
  // Refs
  const pollingIntervalRef = useRef<NodeJS.Timeout | null>(null);
  const currentJobIdRef = useRef<string | null>(null);
  const workflowStageRef = useRef<WorkflowStage>('input');
  const lastNotifiedPdfPathRef = useRef<string | null>(null);
  
  // Update refs when state changes
  useEffect(() => {
    currentJobIdRef.current = currentJobId;
  }, [currentJobId]);
  
  useEffect(() => {
    workflowStageRef.current = workflowStage;
  }, [workflowStage]);
  
  // Audio file upload handler
  const handleAudioFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      const validExtensions = ['.wav', '.mp3', '.m4a', '.ogg', '.flac', '.aac'];
      const fileExt = '.' + file.name.split('.').pop()?.toLowerCase();
      
      if (!validExtensions.includes(fileExt)) {
        toast.error('Invalid audio file type', {
          description: `Please upload one of: ${validExtensions.join(', ')}`
        });
        return;
      }
      
      setAudioFile(file);
      toast.success('Audio file selected', {
        description: file.name
      });
    }
  };
  
  // Caption file upload handler
  const handleCaptionFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      const validExtensions = ['.txt', '.json'];
      const fileExt = '.' + file.name.split('.').pop()?.toLowerCase();
      
      if (!validExtensions.includes(fileExt)) {
        toast.error('Invalid caption file type', {
          description: 'Please upload .txt or .json file'
        });
        return;
      }
      
      setCaptionFile(file);
      toast.success('Caption file selected', {
        description: file.name
      });
    }
  };
  
  // Start analysis
  const handleStartAnalysis = async () => {
    if (!audioFile || !captionFile) {
      toast.error('Both audio and caption files are required');
      return;
    }
    
    if (!title.trim()) {
      toast.error('Title is required');
      return;
    }
    
    try {
      const formData = new FormData();
      formData.append('audioFile', audioFile);
      formData.append('captionFile', captionFile);
      formData.append('title', title);
      formData.append('channelName', channelName || '');
      formData.append('uploadDate', uploadDate || new Date().toISOString().split('T')[0]);
      formData.append('uploadTime', uploadTime || '00:00:00');
      formData.append('toolUsed', 'Upload Rationale');
      
      // IMPORTANT: Don't set Content-Type header for FormData - browser will set it automatically with boundary
      const response = await fetch(API_ENDPOINTS.uploadRationale.startAnalysis, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          // No Content-Type header - let browser set multipart/form-data with boundary
        },
        body: formData,
      });
      
      const data = await response.json();
      
      if (!response.ok) {
        throw new Error(data.error || 'Failed to start analysis');
      }
      
      setCurrentJobId(data.jobId);
      setWorkflowStage('processing');
      startPolling(data.jobId);
      
      toast.success('Analysis started!', {
        description: `Job ID: ${data.jobId}`,
      });
      
    } catch (error: any) {
      console.error('Error starting analysis:', error);
      toast.error('Failed to start analysis', {
        description: error.message,
      });
    }
  };
  
  // Fetch job status
  const fetchJobStatus = async (jobId?: string) => {
    const targetJobId = jobId || currentJobIdRef.current;
    if (!targetJobId) return;
    
    try {
      const response = await fetch(API_ENDPOINTS.uploadRationale.getJob(targetJobId), {
        headers: getAuthHeaders(token),
      });
      
      const data = await response.json();
      
      if (data.success && data.job) {
        setJobStatus(data.job.status);
        setJobSteps(data.job.steps || []);
        setCurrentStepNumber(data.job.currentStep || 0);
        setProgressPercent(data.job.progress || 0);
        
        // Check if awaiting CSV review (after step 10)
        if (data.job.status === 'awaiting_csv_review') {
          if (workflowStageRef.current !== 'csv-review') {
            stopPolling();
            setWorkflowStage('csv-review');
            fetchCsvData(targetJobId);
            toast.success('Step 10 Complete - Review CSV', {
              description: 'Please review the stocks analysis before continuing',
            });
          }
          return;
        }
        
        // Check if PDF ready
        const step12 = data.job.steps.find((s: any) => s.step_number === 12);
        if (step12?.status === 'success' && (data.job.status === 'pdf_ready' || data.job.status === 'signed' || data.job.status === 'completed')) {
          let pdfFile = null;
          
          if (data.job.status === 'signed' || data.job.status === 'completed') {
            pdfFile = data.job.signedPdfPath || data.job.unsignedPdfPath || null;
          } else {
            const outputFiles = step12.output_files || step12.outputFiles || [];
            pdfFile = outputFiles.find((f: string) => f.endsWith('.pdf')) || null;
          }
          
          if (pdfFile && pdfFile !== lastNotifiedPdfPathRef.current) {
            setPdfPath(pdfFile);
            lastNotifiedPdfPathRef.current = pdfFile;
            stopPolling();
            setWorkflowStage('pdf-preview');
            toast.success('PDF Generated Successfully!', {
              description: 'Your analysis report is ready',
            });
          }
        }
        
        // Check if job failed
        if (data.job.status === 'failed') {
          stopPolling();
          toast.error('Job failed', {
            description: 'An error occurred during processing',
          });
        }
      }
    } catch (error) {
      console.error('Error fetching job status:', error);
    }
  };
  
  // Fetch CSV data for review
  const fetchCsvData = async (jobId: string) => {
    try {
      const response = await fetch(API_ENDPOINTS.uploadRationale.getCsv(jobId), {
        headers: getAuthHeaders(token),
      });
      
      if (response.ok) {
        const blob = await response.blob();
        const text = await blob.text();
        
        // Simple CSV parser
        const lines = text.split('\n').filter(line => line.trim());
        const headers = lines[0].split(',');
        const rows = lines.slice(1).map(line => {
          const values = line.split(',');
          const row: any = {};
          headers.forEach((header, index) => {
            row[header] = values[index] || '';
          });
          return row;
        });
        
        setCsvData(rows);
      }
    } catch (error) {
      console.error('Error fetching CSV:', error);
    }
  };
  
  // Polling
  const startPolling = (jobId?: string) => {
    stopPolling();
    if (jobId) {
      currentJobIdRef.current = jobId;
    }
    
    pollingIntervalRef.current = setInterval(() => {
      fetchJobStatus();
    }, 2000);
    
    if (currentJobIdRef.current) {
      fetchJobStatus(currentJobIdRef.current);
    }
  };
  
  const stopPolling = () => {
    if (pollingIntervalRef.current) {
      clearInterval(pollingIntervalRef.current);
      pollingIntervalRef.current = null;
    }
  };
  
  // Cleanup polling on unmount
  useEffect(() => {
    return () => stopPolling();
  }, []);
  
  // Load existing job if selectedJobId is provided
  useEffect(() => {
    if (selectedJobId) {
      setCurrentJobId(selectedJobId);
      setWorkflowStage('processing');
      fetchJobStatus(selectedJobId);
      
      toast.info('Loading job...', {
        description: `Job ID: ${selectedJobId}`,
      });
    }
  }, [selectedJobId]);
  
  // Fetch PDF as blob for iframe preview
  useEffect(() => {
    if (!pdfPath || !token) {
      setPdfBlobUrl(null);
      return;
    }
    
    let blobUrl: string | null = null;
    
    const fetchPdfBlob = async () => {
      try {
        const response = await fetch(API_ENDPOINTS.uploadRationale.downloadPdf(pdfPath), {
          headers: getAuthHeaders(token),
        });
        
        if (!response.ok) {
          console.error('Failed to fetch PDF:', response.status);
          return;
        }
        
        const blob = await response.blob();
        blobUrl = URL.createObjectURL(blob);
        setPdfBlobUrl(blobUrl);
      } catch (error) {
        console.error('Error fetching PDF:', error);
      }
    };
    
    fetchPdfBlob();
    
    return () => {
      if (blobUrl) {
        URL.revokeObjectURL(blobUrl);
      }
    };
  }, [pdfPath, token]);
  
  // Download CSV
  const handleDownloadCsv = async () => {
    if (!currentJobId) return;
    
    try {
      const response = await fetch(API_ENDPOINTS.uploadRationale.getCsv(currentJobId), {
        headers: getAuthHeaders(token),
      });
      
      if (!response.ok) throw new Error('Failed to download CSV');
      
      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `${currentJobId}_analysis.csv`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
      
      toast.success('CSV downloaded successfully');
    } catch (error: any) {
      toast.error('Failed to download CSV', {
        description: error.message,
      });
    }
  };
  
  // Continue pipeline after CSV review
  const handleContinuePipeline = async () => {
    if (!currentJobId) return;
    
    try {
      // Note: CSV upload is handled via FormData, similar to start analysis
      setWorkflowStage('processing');
      startPolling();
      
      toast.info('Continuing analysis...', {
        description: 'Generating charts and PDF',
      });
      
    } catch (error: any) {
      toast.error('Failed to continue pipeline', {
        description: error.message,
      });
    }
  };
  
  // Download PDF
  const handleDownloadPdf = async () => {
    if (!pdfBlobUrl) return;
    
    try {
      const a = document.createElement('a');
      a.href = pdfBlobUrl;
      a.download = `rationale_${currentJobId}.pdf`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      
      toast.success('PDF downloaded successfully');
    } catch (error: any) {
      toast.error('Failed to download PDF');
    }
  };
  
  return (
    <div className="flex-1 p-8 overflow-y-auto">
      <div className="max-w-7xl mx-auto space-y-6">
        {/* Header */}
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Upload Rationale</h1>
          <p className="text-muted-foreground mt-2">
            Upload your audio file and captions to generate professional financial analysis reports
          </p>
        </div>
        
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Left Panel: Input Form */}
          <Card className={workflowStage !== 'input' ? 'opacity-60' : ''}>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Upload className="w-5 h-5" />
                Upload Files & Details
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              {/* Audio File Upload */}
              <div className="space-y-2">
                <Label htmlFor="audioFile">Audio File *</Label>
                <div className="border-2 border-dashed rounded-lg p-6 text-center hover:border-primary/50 transition-colors">
                  <FileAudio className="w-8 h-8 mx-auto mb-2 text-muted-foreground" />
                  <input
                    id="audioFile"
                    type="file"
                    accept=".wav,.mp3,.m4a,.ogg,.flac,.aac"
                    onChange={handleAudioFileChange}
                    className="hidden"
                    disabled={workflowStage !== 'input'}
                  />
                  <label htmlFor="audioFile" className="cursor-pointer">
                    {audioFile ? (
                      <div className="text-sm">
                        <p className="font-medium text-primary">{audioFile.name}</p>
                        <p className="text-muted-foreground mt-1">
                          {(audioFile.size / 1024 / 1024).toFixed(2)} MB
                        </p>
                      </div>
                    ) : (
                      <div className="text-sm text-muted-foreground">
                        <p>Click to upload audio file</p>
                        <p className="text-xs mt-1">WAV, MP3, M4A, OGG, FLAC, AAC</p>
                      </div>
                    )}
                  </label>
                </div>
              </div>
              
              {/* Caption File Upload */}
              <div className="space-y-2">
                <Label htmlFor="captionFile">Caption File *</Label>
                <div className="border-2 border-dashed rounded-lg p-6 text-center hover:border-primary/50 transition-colors">
                  <FileText className="w-8 h-8 mx-auto mb-2 text-muted-foreground" />
                  <input
                    id="captionFile"
                    type="file"
                    accept=".txt,.json"
                    onChange={handleCaptionFileChange}
                    className="hidden"
                    disabled={workflowStage !== 'input'}
                  />
                  <label htmlFor="captionFile" className="cursor-pointer">
                    {captionFile ? (
                      <div className="text-sm">
                        <p className="font-medium text-primary">{captionFile.name}</p>
                        <p className="text-muted-foreground mt-1">
                          {(captionFile.size / 1024).toFixed(2)} KB
                        </p>
                      </div>
                    ) : (
                      <div className="text-sm text-muted-foreground">
                        <p>Click to upload caption file</p>
                        <p className="text-xs mt-1">TXT or JSON format</p>
                      </div>
                    )}
                  </label>
                </div>
              </div>
              
              {/* Title */}
              <div className="space-y-2">
                <Label htmlFor="title">Title *</Label>
                <Input
                  id="title"
                  placeholder="e.g., Market Analysis - January 2025"
                  value={title}
                  onChange={(e) => setTitle(e.target.value)}
                  disabled={workflowStage !== 'input'}
                />
              </div>
              
              {/* Channel Name */}
              <div className="space-y-2">
                <Label htmlFor="channelName">
                  <Building2 className="w-4 h-4 inline mr-1" />
                  Channel Name (Optional)
                </Label>
                <Input
                  id="channelName"
                  placeholder="e.g., PHD Capital"
                  value={channelName}
                  onChange={(e) => setChannelName(e.target.value)}
                  disabled={workflowStage !== 'input'}
                />
              </div>
              
              {/* Date and Time */}
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="uploadDate">
                    <Calendar className="w-4 h-4 inline mr-1" />
                    Date
                  </Label>
                  <Input
                    id="uploadDate"
                    type="date"
                    value={uploadDate}
                    onChange={(e) => setUploadDate(e.target.value)}
                    disabled={workflowStage !== 'input'}
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="uploadTime">
                    <Clock className="w-4 h-4 inline mr-1" />
                    Time
                  </Label>
                  <Input
                    id="uploadTime"
                    type="time"
                    value={uploadTime}
                    onChange={(e) => setUploadTime(e.target.value)}
                    disabled={workflowStage !== 'input'}
                  />
                </div>
              </div>
              
              {/* Start Analysis Button */}
              <Button
                onClick={handleStartAnalysis}
                disabled={!audioFile || !captionFile || !title.trim() || workflowStage !== 'input'}
                className="w-full"
                size="lg"
              >
                <Upload className="w-4 h-4 mr-2" />
                Start Analysis
              </Button>
            </CardContent>
          </Card>
          
          {/* Right Panel: Dynamic Content */}
          <div className="space-y-4">
            {workflowStage === 'input' && (
              <Card>
                <CardContent className="pt-6">
                  <div className="text-center text-muted-foreground">
                    <Upload className="w-16 h-16 mx-auto mb-4 opacity-20" />
                    <p className="text-lg font-medium mb-2">Ready to Start</p>
                    <p className="text-sm">
                      Upload your audio and caption files to begin the analysis
                    </p>
                  </div>
                </CardContent>
              </Card>
            )}
            
            {workflowStage === 'processing' && (
              <AIStyleJobRunner
                jobSteps={jobSteps}
                currentStepNumber={currentStepNumber}
                progressPercent={progressPercent}
                jobStatus={jobStatus}
                jobId={currentJobId || undefined}
                getStepConfig={getUploadStepConfig}
                getTotalSteps={getUploadTotalSteps}
              />
            )}
            
            {workflowStage === 'csv-review' && (
              <Card>
                <CardHeader>
                  <CardTitle>Review Stocks Analysis</CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
                  <p className="text-sm text-muted-foreground">
                    {csvData.length} stocks extracted. Download CSV to review and edit if needed.
                  </p>
                  <div className="flex gap-2">
                    <Button onClick={handleDownloadCsv} variant="outline">
                      <Download className="w-4 h-4 mr-2" />
                      Download CSV
                    </Button>
                    <Button onClick={handleContinuePipeline} className="flex-1">
                      Continue to Charts & PDF
                    </Button>
                  </div>
                </CardContent>
              </Card>
            )}
            
            {workflowStage === 'pdf-preview' && pdfBlobUrl && (
              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center justify-between">
                    <span>PDF Preview</span>
                    <Button onClick={handleDownloadPdf} variant="outline" size="sm">
                      <Download className="w-4 h-4 mr-2" />
                      Download
                    </Button>
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <iframe
                    src={pdfBlobUrl}
                    className="w-full h-[600px] border rounded"
                    title="PDF Preview"
                  />
                </CardContent>
              </Card>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
