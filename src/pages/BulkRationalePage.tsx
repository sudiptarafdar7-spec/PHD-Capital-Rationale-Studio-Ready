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
  RefreshCw, RotateCcw
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
  const [selectedRestartStep, setSelectedRestartStep] = useState<number>(1);
  const [isRestarting, setIsRestarting] = useState(false);

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
          await fetchPdfForPreview(data.pdfPath, data.jobId);
        } else if (data.status === 'completed' || data.status === 'signed') {
          setWorkflowStage('completed');
          if (data.pdfPath) {
            await fetchPdfForPreview(data.pdfPath, data.jobId);
          }
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
              await fetchPdfForPreview(data.pdfPath, jobId);
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

  const fetchPdfForPreview = async (pdfFilePath: string, jobId?: string) => {
    const targetJobId = jobId || currentJobId;
    if (!targetJobId) {
      console.error('No job ID available for PDF fetch');
      return;
    }
    
    try {
      const response = await fetch(API_ENDPOINTS.bulkRationale.downloadPdf(targetJobId), {
        headers: { 'Authorization': `Bearer ${token}` },
      });

      if (response.ok) {
        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        setPdfBlobUrl(url);
        setPdfPath(pdfFilePath);
      } else {
        console.error('Failed to fetch PDF:', response.status, response.statusText);
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

    setIsRestarting(true);
    try {
      const response = await fetch(API_ENDPOINTS.bulkRationale.restartStep(currentJobId, stepNumber), {
        method: 'POST',
        headers: getAuthHeaders(token),
      });

      const data = await response.json();

      if (response.ok && data.success) {
        toast.info(`Restarting from Step ${stepNumber}`, {
          description: 'All subsequent steps will be re-executed',
        });
        setWorkflowStage('processing');
        startPolling(currentJobId);
      } else {
        toast.error('Failed to restart step', {
          description: data.error || 'Please try again',
        });
      }
    } catch (error: any) {
      console.error('Error restarting step:', error);
      toast.error('Failed to restart step', {
        description: error.message || 'Please try again',
      });
    } finally {
      setIsRestarting(false);
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

  const renderRightPanel = () => {
    if (workflowStage === 'processing') {
      return (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="text-lg font-semibold text-slate-800">Processing Job</h3>
          </div>
          <div className="bg-white border border-slate-200 rounded-lg p-12 text-center">
            <Loader2 className="w-16 h-16 mx-auto mb-4 text-purple-500 animate-spin" />
            <p className="text-slate-700">Processing your bulk rationale...</p>
            <p className="text-sm text-slate-500 mt-2">{jobStatus}</p>
          </div>
        </div>
      );
    }

    if (workflowStage === 'pdf-preview') {
      return (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="text-lg font-semibold text-slate-800">Generated PDF Report</h3>
          </div>

          <div className="bg-white border border-slate-200 rounded-lg overflow-hidden">
            {pdfBlobUrl ? (
              <iframe
                src={pdfBlobUrl}
                className="w-full h-[500px]"
                title="PDF Report Preview"
              />
            ) : (
              <div className="w-full h-[500px] flex items-center justify-center bg-slate-100">
                <p className="text-slate-500">Loading PDF...</p>
              </div>
            )}
          </div>

          <div className="grid grid-cols-2 gap-3">
            <Button
              onClick={() => {
                if (pdfBlobUrl) {
                  const a = document.createElement('a');
                  a.href = pdfBlobUrl;
                  a.download = `${currentJobId}_bulk_rationale.pdf`;
                  a.click();
                }
              }}
              className="bg-blue-600 hover:bg-blue-700 text-white"
            >
              <Download className="w-4 h-4 mr-2" />
              Download
            </Button>
            <Button
              onClick={handleSave}
              className="bg-purple-600 hover:bg-purple-700 text-white"
            >
              <Save className="w-4 h-4 mr-2" />
              Save
            </Button>
            <Button
              onClick={handleSaveAndSign}
              className="bg-green-600 hover:bg-green-700 text-white"
            >
              <FileSignature className="w-4 h-4 mr-2" />
              Save & Sign
            </Button>
            <Button
              onClick={handleDelete}
              variant="outline"
              className="border-red-500/50 text-red-500 hover:bg-red-600 hover:text-white hover:border-red-600"
            >
              <Trash2 className="w-4 h-4 mr-2" />
              Delete
            </Button>
          </div>
        </div>
      );
    }

    if (workflowStage === 'upload-signed') {
      return (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="text-lg font-semibold text-slate-800">Upload Signed PDF</h3>
          </div>
          
          <div className="bg-white border border-slate-200 rounded-lg p-6">
            {currentJobId && (
              <SignedFileUpload
                jobId={currentJobId}
                uploadEndpoint={API_ENDPOINTS.bulkRationale.uploadSigned(currentJobId)}
                onUploadComplete={handleSignedUploadComplete}
              />
            )}
          </div>
        </div>
      );
    }

    if (workflowStage === 'completed' || workflowStage === 'saved') {
      return (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="text-lg font-semibold text-green-600 flex items-center gap-2">
              <CheckCircle2 className="h-5 w-5" />
              Job Completed
            </h3>
          </div>

          <div className="bg-white border border-slate-200 rounded-lg overflow-hidden">
            {pdfBlobUrl ? (
              <iframe
                src={pdfBlobUrl}
                className="w-full h-[500px]"
                title="PDF Report Preview"
              />
            ) : (
              <div className="w-full h-[500px] flex items-center justify-center bg-slate-100">
                <p className="text-slate-500">PDF saved to Saved Rationale</p>
              </div>
            )}
          </div>

          <div className="grid grid-cols-2 gap-3">
            <Button onClick={() => onNavigate('saved-rationale')} className="bg-purple-600 hover:bg-purple-700 text-white">
              View Saved Rationale
            </Button>
            <Button variant="outline" onClick={handleReset}>
              Start New Analysis
            </Button>
          </div>
        </div>
      );
    }

    return null;
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

        {currentJobId && jobSteps.length > 0 && workflowStage !== 'input' && (
          <Card className="shadow-sm">
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 p-6">
              {/* Left Column: 6-Step Pipeline */}
              <div className="space-y-4">
                <div className="flex items-center justify-between mb-4">
                  <div>
                    <h3 className="text-lg font-semibold text-slate-800">6-Step Pipeline</h3>
                    <p className="text-sm text-slate-500">Job ID: {currentJobId}</p>
                  </div>
                </div>

                {/* Progress Bar with Restart Selector */}
                <div className="mb-4">
                  <div className="flex justify-between text-sm text-slate-600 mb-2">
                    <span>Progress</span>
                    <span>{progress}%</span>
                  </div>
                  <div className="flex items-center gap-3">
                    <div className="flex-1 bg-slate-200 rounded-full h-3">
                      <div 
                        className="bg-gradient-to-r from-purple-500 to-purple-600 h-3 rounded-full transition-all duration-500"
                        style={{ width: `${progress}%` }}
                      />
                    </div>
                    
                    <div className="flex items-center gap-2">
                      <Select
                        value={selectedRestartStep.toString()}
                        onValueChange={(value) => setSelectedRestartStep(parseInt(value, 10))}
                        disabled={isRestarting}
                      >
                        <SelectTrigger className="w-[100px] h-9">
                          <SelectValue placeholder="Step" />
                        </SelectTrigger>
                        <SelectContent>
                          {jobSteps.filter(s => s.status === 'success' || s.status === 'failed' || s.status === 'running').map((step) => (
                            <SelectItem key={step.step_number} value={step.step_number.toString()}>
                              Step {step.step_number}
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                      
                      <Button
                        onClick={() => handleRestartStep(selectedRestartStep)}
                        disabled={isRestarting || jobSteps.filter(s => s.status !== 'pending').length === 0}
                        variant="outline"
                        size="sm"
                        className="h-9 px-3 bg-purple-50 border-purple-300 text-purple-700 hover:bg-purple-100 hover:border-purple-400"
                        title={`Restart from step ${selectedRestartStep}`}
                      >
                        {isRestarting ? (
                          <Loader2 className="w-4 h-4 animate-spin" />
                        ) : (
                          <RotateCcw className="w-4 h-4" />
                        )}
                      </Button>
                    </div>
                  </div>
                </div>

                {/* Steps List */}
                <div className="space-y-2 max-h-[500px] overflow-y-auto pr-2">
                  {jobSteps.map((step) => (
                    <div 
                      key={step.step_number}
                      className={`flex items-center justify-between p-3 rounded-lg border ${
                        step.status === 'running' ? 'bg-blue-50 border-blue-200' :
                        step.status === 'success' ? 'bg-green-50 border-green-200' :
                        step.status === 'failed' ? 'bg-red-50 border-red-200' :
                        'bg-slate-50 border-slate-200'
                      }`}
                    >
                      <div className="flex items-center gap-3">
                        {renderStepStatus(step)}
                        <div>
                          <p className="font-medium text-sm">Step {step.step_number}: {step.name || step.step_name}</p>
                          {step.message && (
                            <p className="text-xs text-slate-600">{step.message}</p>
                          )}
                        </div>
                      </div>
                      {step.status === 'failed' && (
                        <Button 
                          variant="outline" 
                          size="sm"
                          onClick={() => handleRestartStep(step.step_number)}
                          disabled={isRestarting}
                          className="h-7 text-xs"
                        >
                          <RefreshCw className="h-3 w-3 mr-1" />
                          Retry
                        </Button>
                      )}
                      {step.status === 'success' && (
                        <Button 
                          variant="ghost" 
                          size="sm"
                          onClick={() => handleRestartStep(step.step_number)}
                          disabled={isRestarting}
                          className="h-7 text-xs text-slate-500 hover:text-purple-600"
                        >
                          <RotateCcw className="h-3 w-3 mr-1" />
                          Reload
                        </Button>
                      )}
                    </div>
                  ))}
                </div>

                {/* New Analysis Button */}
                {(workflowStage === 'pdf-preview' || workflowStage === 'completed' || workflowStage === 'saved') && (
                  <Button
                    variant="outline"
                    onClick={handleReset}
                    className="w-full mt-4 border-purple-500/50 text-purple-600 hover:bg-purple-50"
                  >
                    <RotateCcw className="w-4 h-4 mr-2" />
                    New Analysis
                  </Button>
                )}
              </div>

              {/* Right Column: Dynamic Content Based on Workflow Stage */}
              <div className="space-y-4">
                {renderRightPanel()}
              </div>
            </div>
          </Card>
        )}
      </div>
    </div>
  );
}
