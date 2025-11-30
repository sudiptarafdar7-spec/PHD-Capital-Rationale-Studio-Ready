import { useState, useEffect, useRef } from 'react';
import { useAuth } from '@/lib/auth-context';
import { API_ENDPOINTS, getAuthHeaders } from '@/lib/api-config';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { toast } from 'sonner';
import { 
  Layers, Play, Download, Save, FileSignature, Trash2, 
  ArrowLeft, Upload, CheckCircle2, XCircle, Loader2, Clock,
  RefreshCw
} from 'lucide-react';
import SignedFileUpload from '@/components/SignedFileUpload';

interface Channel {
  id: number;
  channel_name: string;
  platform: string;
  channel_url?: string;
}

interface JobStep {
  id: string;
  job_id: string;
  step_number: number;
  name?: string;
  step_name?: string;
  status: 'pending' | 'running' | 'success' | 'failed';
  message?: string;
  started_at?: string;
  ended_at?: string;
}

type WorkflowStage = 'input' | 'processing' | 'pdf-preview' | 'saved' | 'upload-signed' | 'completed';
type SaveType = 'save' | 'save-and-sign' | null;

interface BulkRationalePageProps {
  onNavigate: (page: string, jobId?: string | null) => void;
  selectedJobId?: string | null;
}

const playCompletionBell = () => {
  try {
    const audioContext = new (window.AudioContext || (window as any).webkitAudioContext)();
    const oscillator = audioContext.createOscillator();
    const gainNode = audioContext.createGain();
    oscillator.connect(gainNode);
    gainNode.connect(audioContext.destination);
    oscillator.frequency.value = 800;
    oscillator.type = 'sine';
    gainNode.gain.setValueAtTime(0.3, audioContext.currentTime);
    gainNode.gain.exponentialRampToValueAtTime(0.01, audioContext.currentTime + 0.5);
    oscillator.start(audioContext.currentTime);
    oscillator.stop(audioContext.currentTime + 0.5);
  } catch (e) {}
};

export default function BulkRationalePage({ onNavigate, selectedJobId }: BulkRationalePageProps) {
  const { token } = useAuth();
  const pollingIntervalRef = useRef<NodeJS.Timeout | null>(null);
  const lastNotifiedPdfPathRef = useRef<string | null>(null);
  
  const [channels, setChannels] = useState<Channel[]>([]);
  const [selectedChannelId, setSelectedChannelId] = useState<string>('');
  const [youtubeUrl, setYoutubeUrl] = useState<string>('');
  const [callDate, setCallDate] = useState(new Date().toISOString().split('T')[0]);
  const [callTime, setCallTime] = useState(new Date().toTimeString().split(' ')[0].substring(0, 5));
  const [inputText, setInputText] = useState('');
  
  const [currentJobId, setCurrentJobId] = useState<string | null>(selectedJobId || null);
  const [progress, setProgress] = useState(0);
  const [workflowStage, setWorkflowStage] = useState<WorkflowStage>('input');
  const [jobStatus, setJobStatus] = useState<string>('');
  const [jobSteps, setJobSteps] = useState<JobStep[]>([]);
  const [rationaleTitle, setRationaleTitle] = useState('');
  const [saveType, setSaveType] = useState<SaveType>(null);
  
  const [pdfPath, setPdfPath] = useState<string | null>(null);
  const [pdfBlobUrl, setPdfBlobUrl] = useState<string | null>(null);

  useEffect(() => {
    loadChannels();
  }, []);

  useEffect(() => {
    if (selectedJobId) {
      loadExistingJob(selectedJobId);
    }
  }, [selectedJobId]);

  useEffect(() => {
    return () => {
      if (pollingIntervalRef.current) {
        clearInterval(pollingIntervalRef.current);
      }
    };
  }, []);

  const loadChannels = async () => {
    try {
      const response = await fetch(API_ENDPOINTS.channels.getAll, {
        headers: getAuthHeaders(token),
      });
      
      if (response.ok) {
        const data = await response.json();
        setChannels(data);
      }
    } catch (error) {
      console.error('Error loading channels:', error);
      toast.error('Failed to load platforms');
    }
  };

  const loadExistingJob = async (jobId: string) => {
    try {
      const response = await fetch(API_ENDPOINTS.bulkRationale.getJob(jobId), {
        headers: getAuthHeaders(token),
      });
      
      if (response.ok) {
        const data = await response.json();
        setCurrentJobId(data.jobId);
        setProgress(data.progress || 0);
        setJobStatus(data.status);
        setRationaleTitle(data.title || '');
        
        if (data.job_steps) {
          const mappedSteps = data.job_steps.map((step: any) => ({
            id: String(step.id),
            job_id: step.job_id,
            step_number: step.step_number,
            name: step.step_name,
            status: step.status === 'running' ? 'running' : 
                   step.status === 'success' ? 'success' : 
                   step.status,
            message: step.message || undefined,
            started_at: step.started_at || undefined,
            ended_at: step.ended_at || undefined,
          }));
          setJobSteps(mappedSteps);
        }
        
        if (data.status === 'processing') {
          setWorkflowStage('processing');
          startPolling(jobId);
        } else if (data.status === 'failed') {
          setWorkflowStage('processing');
        } else if (data.status === 'pdf_ready' && data.pdfPath) {
          setWorkflowStage('pdf-preview');
          await fetchPdfForPreview(data.pdfPath);
        } else if (data.status === 'completed' || data.status === 'signed') {
          setWorkflowStage('completed');
        }
        
        toast.info('Job loaded', { description: data.title });
      }
    } catch (error) {
      console.error('Error loading job:', error);
      toast.error('Failed to load job');
    }
  };

  const handleStartAnalysis = async () => {
    if (!selectedChannelId || !callDate || !inputText.trim()) {
      toast.error('Please fill all required fields');
      return;
    }

    try {
      const response = await fetch(API_ENDPOINTS.bulkRationale.createJob, {
        method: 'POST',
        headers: getAuthHeaders(token),
        body: JSON.stringify({
          channelId: parseInt(selectedChannelId),
          youtubeUrl: youtubeUrl,
          callDate: callDate,
          callTime: callTime + ':00',
          inputText: inputText,
        }),
      });

      if (response.ok) {
        const data = await response.json();
        setCurrentJobId(data.jobId);
        setRationaleTitle(data.title);
        setWorkflowStage('processing');
        toast.success('Bulk Rationale job started!');
        
        startPolling(data.jobId);
      } else {
        const error = await response.json();
        toast.error(error.error || 'Failed to start job');
      }
    } catch (error) {
      console.error('Error starting analysis:', error);
      toast.error('Failed to start analysis');
    }
  };

  const startPolling = (jobId: string) => {
    if (pollingIntervalRef.current) {
      clearInterval(pollingIntervalRef.current);
    }

    pollingIntervalRef.current = setInterval(async () => {
      try {
        const response = await fetch(API_ENDPOINTS.bulkRationale.getJob(jobId), {
          headers: getAuthHeaders(token),
        });

        if (response.ok) {
          const data = await response.json();
          setProgress(data.progress || 0);
          setJobStatus(data.status);
          
          if (data.job_steps) {
            const mappedSteps = data.job_steps.map((step: any) => ({
              id: String(step.id),
              job_id: step.job_id,
              step_number: step.step_number,
              name: step.step_name,
              status: step.status === 'running' ? 'running' : 
                     step.status === 'success' ? 'success' : 
                     step.status,
              message: step.message || undefined,
              started_at: step.started_at || undefined,
              ended_at: step.ended_at || undefined,
            }));
            setJobSteps(mappedSteps);
          }

          if (data.status === 'pdf_ready' && data.pdfPath) {
            if (data.pdfPath !== lastNotifiedPdfPathRef.current || workflowStage !== 'pdf-preview') {
              lastNotifiedPdfPathRef.current = data.pdfPath;
              if (pollingIntervalRef.current) {
                clearInterval(pollingIntervalRef.current);
              }
              setWorkflowStage('pdf-preview');
              await fetchPdfForPreview(data.pdfPath);
              playCompletionBell();
              toast.success('PDF generated successfully!');
            }
          } else if (data.status === 'failed') {
            if (pollingIntervalRef.current) {
              clearInterval(pollingIntervalRef.current);
            }
            toast.error('Job failed. Check the step details for errors.');
          }
        }
      } catch (error) {
        console.error('Polling error:', error);
      }
    }, 2000);
  };

  const fetchPdfForPreview = async (pdfFilePath: string) => {
    try {
      const response = await fetch(API_ENDPOINTS.bulkRationale.downloadPdf(currentJobId!), {
        headers: { 'Authorization': `Bearer ${token}` },
      });

      if (response.ok) {
        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        setPdfBlobUrl(url);
        setPdfPath(pdfFilePath);
      }
    } catch (error) {
      console.error('Error fetching PDF:', error);
    }
  };

  const handleSave = async () => {
    if (!currentJobId) return;

    setSaveType('save');

    try {
      const response = await fetch(API_ENDPOINTS.bulkRationale.save(currentJobId), {
        method: 'POST',
        headers: getAuthHeaders(token),
        body: JSON.stringify({ jobId: currentJobId }),
      });

      const data = await response.json();

      if (!response.ok || !data.success) {
        throw new Error(data.error || 'Failed to save rationale');
      }

      setProgress(100);
      toast.success('Rationale saved successfully!', {
        description: 'Job saved and logged. View in Saved Rationale.',
      });

      setWorkflowStage('completed');
    } catch (error: any) {
      console.error('Error saving rationale:', error);
      toast.error('Failed to save rationale', {
        description: error.message || 'Please try again',
      });
    }
  };

  const handleSaveAndSign = async () => {
    if (!currentJobId) return;

    setSaveType('save-and-sign');

    try {
      toast.info('Saving unsigned PDF and job data');

      const response = await fetch(API_ENDPOINTS.bulkRationale.save(currentJobId), {
        method: 'POST',
        headers: getAuthHeaders(token),
        body: JSON.stringify({ jobId: currentJobId }),
      });

      const data = await response.json();

      if (!response.ok || !data.success) {
        throw new Error(data.error || 'Failed to save rationale');
      }

      toast.success('Unsigned PDF saved successfully', {
        description: 'Please upload signed PDF.',
      });

      setWorkflowStage('upload-signed');
    } catch (error: any) {
      console.error('Error saving rationale:', error);
      toast.error('Failed to save rationale', {
        description: error.message || 'Please try again',
      });
    }
  };

  const handleSignedUploadComplete = () => {
    setWorkflowStage('completed');
    toast.success('Signed PDF uploaded successfully!');
  };

  const handleDelete = async () => {
    if (!currentJobId) return;

    if (!confirm('Are you sure you want to delete this job?')) return;

    try {
      const response = await fetch(API_ENDPOINTS.bulkRationale.deleteJob(currentJobId), {
        method: 'DELETE',
        headers: getAuthHeaders(token),
      });

      if (response.ok) {
        toast.success('Job deleted successfully');
        handleReset();
      } else {
        toast.error('Failed to delete job');
      }
    } catch (error) {
      console.error('Error deleting job:', error);
      toast.error('Failed to delete job');
    }
  };

  const handleRestartStep = async (stepNumber: number) => {
    if (!currentJobId) return;

    try {
      const response = await fetch(API_ENDPOINTS.bulkRationale.restartStep(currentJobId, stepNumber), {
        method: 'POST',
        headers: getAuthHeaders(token),
      });

      if (response.ok) {
        toast.success(`Restarting from step ${stepNumber}`);
        setWorkflowStage('processing');
        startPolling(currentJobId);
      } else {
        toast.error('Failed to restart step');
      }
    } catch (error) {
      console.error('Error restarting step:', error);
      toast.error('Failed to restart step');
    }
  };

  const handleReset = () => {
    if (pollingIntervalRef.current) {
      clearInterval(pollingIntervalRef.current);
    }
    setCurrentJobId(null);
    setProgress(0);
    setWorkflowStage('input');
    setJobStatus('');
    setJobSteps([]);
    setRationaleTitle('');
    setSaveType(null);
    setPdfPath(null);
    setPdfBlobUrl(null);
    setInputText('');
    setYoutubeUrl('');
    lastNotifiedPdfPathRef.current = null;
  };

  const renderStepStatus = (step: JobStep) => {
    const status = step.status;
    switch (status) {
      case 'success':
        return <CheckCircle2 className="h-5 w-5 text-green-500" />;
      case 'running':
        return <Loader2 className="h-5 w-5 text-blue-500 animate-spin" />;
      case 'failed':
        return <XCircle className="h-5 w-5 text-red-500" />;
      default:
        return <Clock className="h-5 w-5 text-gray-400" />;
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 to-slate-100 p-6">
      <div className="max-w-6xl mx-auto">
        <div className="flex items-center gap-4 mb-6">
          <Button
            variant="ghost"
            size="icon"
            onClick={() => onNavigate('dashboard')}
          >
            <ArrowLeft className="h-5 w-5" />
          </Button>
          <div className="flex items-center gap-3">
            <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-purple-500 to-purple-600 flex items-center justify-center shadow-lg">
              <Layers className="h-6 w-6 text-white" />
            </div>
            <div>
              <h1 className="text-2xl font-bold text-slate-800">Bulk Rationale</h1>
              <p className="text-slate-500">Generate multiple stock rationales from text input</p>
            </div>
          </div>
        </div>

        {workflowStage === 'input' && (
          <Card>
            <CardHeader>
              <CardTitle>Input Details</CardTitle>
              <CardDescription>
                Enter the channel/platform details and paste your stock calls text
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label>Channel/Platform *</Label>
                  <Select value={selectedChannelId} onValueChange={setSelectedChannelId}>
                    <SelectTrigger>
                      <SelectValue placeholder="Select platform" />
                    </SelectTrigger>
                    <SelectContent>
                      {channels.map((channel) => (
                        <SelectItem key={channel.id} value={String(channel.id)}>
                          {channel.platform} - {channel.channel_name}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>

                <div className="space-y-2">
                  <Label>YouTube URL (Optional)</Label>
                  <Input
                    placeholder="https://youtube.com/watch?v=..."
                    value={youtubeUrl}
                    onChange={(e) => setYoutubeUrl(e.target.value)}
                  />
                </div>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label>Date *</Label>
                  <Input
                    type="date"
                    value={callDate}
                    onChange={(e) => setCallDate(e.target.value)}
                  />
                </div>

                <div className="space-y-2">
                  <Label>Time *</Label>
                  <Input
                    type="time"
                    value={callTime}
                    onChange={(e) => setCallTime(e.target.value)}
                  />
                </div>
              </div>

              <div className="space-y-2">
                <Label>Input Text *</Label>
                <Textarea
                  placeholder="Paste your stock calls text here... (can be in Hindi or English)"
                  value={inputText}
                  onChange={(e) => setInputText(e.target.value)}
                  rows={10}
                  className="font-mono"
                />
                <p className="text-sm text-slate-500">
                  Paste stock calls, recommendations, or analysis text. The system will translate, 
                  extract stocks, fetch prices, generate charts, and create a PDF report.
                </p>
              </div>

              <Button 
                onClick={handleStartAnalysis}
                disabled={!selectedChannelId || !callDate || !inputText.trim()}
                className="w-full"
                size="lg"
              >
                <Play className="h-5 w-5 mr-2" />
                Generate Rationale
              </Button>
            </CardContent>
          </Card>
        )}

        {workflowStage === 'processing' && (
          <Card>
            <CardHeader>
              <CardTitle>Processing: {rationaleTitle}</CardTitle>
              <CardDescription>
                Job ID: {currentJobId} | Status: {jobStatus}
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="mb-6">
                <div className="flex justify-between text-sm text-slate-600 mb-2">
                  <span>Progress</span>
                  <span>{progress}%</span>
                </div>
                <div className="w-full bg-slate-200 rounded-full h-3">
                  <div 
                    className="bg-gradient-to-r from-purple-500 to-purple-600 h-3 rounded-full transition-all duration-500"
                    style={{ width: `${progress}%` }}
                  />
                </div>
              </div>

              <div className="space-y-3">
                {jobSteps.map((step) => (
                  <div 
                    key={step.step_number}
                    className={`flex items-center justify-between p-4 rounded-lg border ${
                      step.status === 'running' ? 'bg-blue-50 border-blue-200' :
                      step.status === 'success' ? 'bg-green-50 border-green-200' :
                      step.status === 'failed' ? 'bg-red-50 border-red-200' :
                      'bg-slate-50 border-slate-200'
                    }`}
                  >
                    <div className="flex items-center gap-3">
                      {renderStepStatus(step)}
                      <div>
                        <p className="font-medium">Step {step.step_number}: {step.name || step.step_name}</p>
                        {step.message && (
                          <p className="text-sm text-slate-600">{step.message}</p>
                        )}
                      </div>
                    </div>
                    {step.status === 'failed' && (
                      <Button 
                        variant="outline" 
                        size="sm"
                        onClick={() => handleRestartStep(step.step_number)}
                      >
                        <RefreshCw className="h-4 w-4 mr-1" />
                        Retry
                      </Button>
                    )}
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        )}

        {workflowStage === 'pdf-preview' && pdfBlobUrl && (
          <Card>
            <CardHeader>
              <CardTitle>PDF Preview: {rationaleTitle}</CardTitle>
              <CardDescription>
                Review the generated PDF and save or sign it
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="mb-6 border rounded-lg overflow-hidden bg-slate-100">
                <iframe
                  src={pdfBlobUrl}
                  className="w-full h-[600px]"
                  title="PDF Preview"
                />
              </div>

              <div className="flex flex-wrap gap-3">
                <Button onClick={() => {
                  const a = document.createElement('a');
                  a.href = pdfBlobUrl;
                  a.download = `${currentJobId}_bulk_rationale.pdf`;
                  a.click();
                }}>
                  <Download className="h-4 w-4 mr-2" />
                  Download PDF
                </Button>

                <Button onClick={handleSave} variant="default">
                  <Save className="h-4 w-4 mr-2" />
                  Save
                </Button>

                <Button onClick={handleSaveAndSign} variant="secondary">
                  <FileSignature className="h-4 w-4 mr-2" />
                  Save & Sign
                </Button>

                <Button onClick={handleDelete} variant="destructive">
                  <Trash2 className="h-4 w-4 mr-2" />
                  Delete
                </Button>
              </div>
            </CardContent>
          </Card>
        )}

        {workflowStage === 'upload-signed' && currentJobId && (
          <Card>
            <CardHeader>
              <CardTitle>Upload Signed PDF</CardTitle>
              <CardDescription>
                Upload the signed version of the PDF
              </CardDescription>
            </CardHeader>
            <CardContent>
              <SignedFileUpload
                jobId={currentJobId}
                uploadEndpoint={API_ENDPOINTS.bulkRationale.uploadSigned(currentJobId)}
                onUploadComplete={handleSignedUploadComplete}
              />
            </CardContent>
          </Card>
        )}

        {workflowStage === 'completed' && (
          <Card>
            <CardHeader>
              <CardTitle className="text-green-600 flex items-center gap-2">
                <CheckCircle2 className="h-6 w-6" />
                Job Completed
              </CardTitle>
              <CardDescription>
                {rationaleTitle}
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <p className="text-slate-600">
                Your bulk rationale has been saved successfully. You can view it in the Saved Rationale section.
              </p>

              <div className="flex gap-3">
                <Button onClick={() => onNavigate('saved-rationale')}>
                  View Saved Rationale
                </Button>
                <Button variant="outline" onClick={handleReset}>
                  Start New Analysis
                </Button>
              </div>
            </CardContent>
          </Card>
        )}
      </div>
    </div>
  );
}
