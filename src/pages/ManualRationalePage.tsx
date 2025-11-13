import React, { useState } from 'react';
import { PenTool, Plus, Trash2, Calendar, Save, Download, FileSignature, Loader2, Clock } from 'lucide-react';
import { Card } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import { toast } from 'sonner@2.0.3';
import StepProgressTracker from '../components/StepProgressTracker';
import SignedFileUpload from '../components/SignedFileUpload';
import { playCompletionBell, playSuccessBell } from '../lib/sound-utils';
import { JobStep } from '../types';

interface ManualRationalePageProps {
  selectedJobId?: string;
}

interface StockDetail {
  id: string;
  stockName: string;
  time: string;
  analysis: string;
}

type WorkflowStage = 'input' | 'processing' | 'pdf-preview' | 'saved' | 'upload-signed' | 'completed';

const MANUAL_STEPS: JobStep[] = [
  { id: 'step-1', job_id: '', step_number: 1, name: 'Create Structured CSV', status: 'pending' },
  { id: 'step-2', job_id: '', step_number: 2, name: 'Map Master File', status: 'pending' },
  { id: 'step-3', job_id: '', step_number: 3, name: 'Fetch CMP', status: 'pending' },
  { id: 'step-4', job_id: '', step_number: 4, name: 'Generate Charts', status: 'pending' },
  { id: 'step-5', job_id: '', step_number: 5, name: 'Generate PDF', status: 'pending' },
  { id: 'step-6', job_id: '', step_number: 6, name: 'Save / Save & Sign & Log', status: 'pending', message: 'Save final output and update logs' },
];

export default function ManualRationalePage({ selectedJobId }: ManualRationalePageProps) {
  const [platformName, setPlatformName] = useState('YouTube');
  const [platformId, setPlatformId] = useState('');
  const [url, setUrl] = useState('');
  const [date, setDate] = useState(new Date().toISOString().split('T')[0]);
  const [stockDetails, setStockDetails] = useState<StockDetail[]>([
    { id: '1', stockName: '', time: '', analysis: '' }
  ]);
  
  const [currentJobId, setCurrentJobId] = useState<string | null>(null);
  const [jobSteps, setJobSteps] = useState<JobStep[]>([]);
  const [workflowStage, setWorkflowStage] = useState<WorkflowStage>('input');
  const [isProcessing, setIsProcessing] = useState(false);
  const [uploadedSignedFile, setUploadedSignedFile] = useState<{ fileName: string; uploadedAt: string } | null>(null);
  const [saveType, setSaveType] = useState<'save' | 'save-and-sign' | null>(null);

  const loadSavedJob = React.useCallback(async (jobId: string) => {
    // Import mock data functions
    const { mockSavedRationale, getMockManualRationaleSteps } = await import('../lib/mock-data');
    
    // Find the saved rationale
    const savedRationale = mockSavedRationale.find(r => r.job_id === jobId);
    
    if (!savedRationale) {
      toast.error('Job not found', {
        description: `Could not find job with ID: ${jobId}`,
      });
      return;
    }

    // Set the job ID
    setCurrentJobId(jobId);

    // Load completed steps
    const steps = getMockManualRationaleSteps(jobId, true);
    setJobSteps(steps);

    // Determine workflow stage based on signed file
    if (savedRationale.signed_path) {
      setWorkflowStage('completed');
      setSaveType('save-and-sign');
      setUploadedSignedFile({
        fileName: 'final_rationale_report_signed.pdf',
        uploadedAt: savedRationale.signed_uploaded_at || new Date().toISOString(),
      });
    } else {
      setWorkflowStage('saved');
      setSaveType('save');
    }

    // Load form data from saved rationale (mock data for now)
    setPlatformName('YouTube');
    setPlatformId(savedRationale.youtube_video_name);
    setUrl(savedRationale.youtube_url);
    setDate(savedRationale.video_upload_date);
    
    // Parse stock names into stock details
    const stockNames = savedRationale.stock_name.split(',').map(s => s.trim());
    const loadedStocks = stockNames.map((name, index) => ({
      id: `loaded-${index}`,
      stockName: name,
      time: '10:00 AM', // Mock time
      analysis: 'Detailed analysis from saved rationale', // Mock analysis
    }));
    setStockDetails(loadedStocks.length > 0 ? loadedStocks : [{ id: '1', stockName: '', time: '', analysis: '' }]);

    toast.success('Loaded saved job', {
      description: `Job ID: ${jobId}`,
    });
  }, []);

  React.useEffect(() => {
    if (selectedJobId) {
      // Load the saved job data
      loadSavedJob(selectedJobId);
    }
  }, [selectedJobId, loadSavedJob]);

  const addStockDetail = () => {
    const newStock: StockDetail = {
      id: Date.now().toString(),
      stockName: '',
      time: '',
      analysis: ''
    };
    setStockDetails([...stockDetails, newStock]);
  };

  const removeStockDetail = (id: string) => {
    if (stockDetails.length === 1) {
      toast.error('Error', {
        description: 'At least one stock detail is required',
      });
      return;
    }
    setStockDetails(stockDetails.filter(stock => stock.id !== id));
  };

  const updateStockDetail = (id: string, field: keyof StockDetail, value: string) => {
    setStockDetails(stockDetails.map(stock => 
      stock.id === id ? { ...stock, [field]: value } : stock
    ));
  };

  const validateForm = () => {
    if (!platformName) {
      toast.error('Validation Error', { description: 'Platform Name is required' });
      return false;
    }
    if (!platformId) {
      toast.error('Validation Error', { description: 'Platform ID is required' });
      return false;
    }
    if (!date) {
      toast.error('Validation Error', { description: 'Date is required' });
      return false;
    }
    
    for (const stock of stockDetails) {
      if (!stock.stockName || !stock.time || !stock.analysis) {
        toast.error('Validation Error', { description: 'All stock fields are required' });
        return false;
      }
    }
    
    return true;
  };

  const runStepsFromTo = async (fromStep: number, toStep: number, jobId: string) => {
    for (let stepNum = fromStep; stepNum <= toStep; stepNum++) {
      // Update step to running
      setJobSteps(prev => {
        const updated = [...prev];
        const stepIndex = updated.findIndex(s => s.step_number === stepNum);
        if (stepIndex !== -1) {
          updated[stepIndex] = {
            ...updated[stepIndex],
            status: 'running',
            started_at: new Date().toISOString(),
          };
        }
        return updated;
      });

      // Simulate step execution
      await new Promise(resolve => setTimeout(resolve, 2000));

      // Update step to success
      setJobSteps(prev => {
        const updated = [...prev];
        const stepIndex = updated.findIndex(s => s.step_number === stepNum);
        if (stepIndex !== -1) {
          updated[stepIndex] = {
            ...updated[stepIndex],
            status: 'success',
            ended_at: new Date().toISOString(),
            message: `Completed ${updated[stepIndex].name}`,
          };
        }
        return updated;
      });

      toast.success(`Step ${stepNum} Complete`, {
        description: MANUAL_STEPS[stepNum - 1].name,
      });

      // Play bell sound for step 5 (Generate PDF)
      if (stepNum === 5) {
        playCompletionBell();
        toast.success('PDF Generated! 📄', {
          description: 'Rationale report is ready',
        });
      }
    }
  };

  const generateRationale = async () => {
    if (!validateForm()) return;

    setIsProcessing(true);
    const jobId = `MANUAL-${Date.now()}`;
    setCurrentJobId(jobId);
    setWorkflowStage('processing');
    
    // Initialize job steps
    const initialSteps = MANUAL_STEPS.map(step => ({
      ...step,
      job_id: jobId,
    }));
    setJobSteps(initialSteps);

    toast.info('Job Created', {
      description: `Job ID: ${jobId}`,
    });

    // Run steps 1-5
    await runStepsFromTo(1, 5, jobId);

    setIsProcessing(false);
    setWorkflowStage('pdf-preview');
    
    toast.success('PDF Generated Successfully', {
      description: 'Your rationale report is ready',
    });
  };

  const handleDownloadPDF = () => {
    toast.success('Downloading PDF', {
      description: 'final_rationale_report.pdf',
    });
  };

  const handleSave = async () => {
    if (!currentJobId) return;

    setSaveType('save');

    toast.info('Saving rationale...', {
      description: 'Saving PDF and job data',
    });

    // Update step 6 to running
    setJobSteps(prev => {
      const updated = [...prev];
      const stepIndex = updated.findIndex(s => s.step_number === 6);
      if (stepIndex !== -1) {
        updated[stepIndex] = {
          ...updated[stepIndex],
          status: 'running',
          started_at: new Date().toISOString(),
        };
      }
      return updated;
    });

    // Simulate saving
    await new Promise(resolve => setTimeout(resolve, 1500));

    // Update step 6 to success
    setJobSteps(prev => {
      const updated = [...prev];
      const stepIndex = updated.findIndex(s => s.step_number === 6);
      if (stepIndex !== -1) {
        updated[stepIndex] = {
          ...updated[stepIndex],
          status: 'success',
          ended_at: new Date().toISOString(),
          message: 'Rationale saved successfully',
        };
      }
      return updated;
    });

    toast.success('Rationale saved successfully!', {
      description: 'Job saved and logged. View in Saved Rationale.',
    });

    setWorkflowStage('saved');
  };

  const handleSaveAndSign = async () => {
    if (!currentJobId) return;

    setSaveType('save-and-sign');

    toast.info('Saving unsigned PDF and job data', {
      description: 'Preparing for signed file upload',
    });

    // Simulate saving
    await new Promise(resolve => setTimeout(resolve, 1500));

    toast.success('Unsigned PDF saved successfully', {
      description: 'Job and rationale log created. Please upload signed PDF.',
    });

    setWorkflowStage('upload-signed');
  };

  const handleSignedFileUpload = async (uploadInfo: { fileName: string; uploadedAt: string }) => {
    if (!currentJobId) return;

    // Store the uploaded file info
    setUploadedSignedFile(uploadInfo);

    // Update step 6 to running
    setJobSteps(prev => {
      const updated = [...prev];
      const stepIndex = updated.findIndex(s => s.step_number === 6);
      if (stepIndex !== -1) {
        updated[stepIndex] = {
          ...updated[stepIndex],
          status: 'running',
          started_at: new Date().toISOString(),
        };
      }
      return updated;
    });

    // Simulate final processing
    await new Promise(resolve => setTimeout(resolve, 1500));

    // Update step 6 to success
    setJobSteps(prev => {
      const updated = [...prev];
      const stepIndex = updated.findIndex(s => s.step_number === 6);
      if (stepIndex !== -1) {
        updated[stepIndex] = {
          ...updated[stepIndex],
          status: 'success',
          ended_at: new Date().toISOString(),
          message: `Signed PDF uploaded: ${uploadInfo.fileName}`,
        };
      }
      return updated;
    });

    setWorkflowStage('completed');

    // Play success bell for signed file upload
    playSuccessBell();

    toast.success('Workflow completed! 🎉', {
      description: 'All steps finished successfully with signed PDF',
    });
  };

  const handleDeleteJob = () => {
    toast.success('Job deleted successfully', {
      description: 'Starting a new analysis',
    });
    handleRestart();
  };

  const handleRestart = () => {
    setPlatformName('YouTube');
    setPlatformId('');
    setUrl('');
    setDate(new Date().toISOString().split('T')[0]);
    setStockDetails([{ id: '1', stockName: '', time: '', analysis: '' }]);
    setCurrentJobId(null);
    setJobSteps([]);
    setWorkflowStage('input');
    setIsProcessing(false);
    setUploadedSignedFile(null);
    setSaveType(null);
  };

  const handleRestartFromStep = async (stepNumber: number) => {
    if (!currentJobId) return;

    const stepName = MANUAL_STEPS[stepNumber - 1]?.name || `Step ${stepNumber}`;
    toast.info('Restarting Pipeline', {
      description: `Restarting from ${stepName} - All steps from ${stepNumber} to 6 will be re-executed`,
    });

    // Reset all steps from stepNumber onwards to pending
    setJobSteps(prev => {
      const updated = [...prev];
      for (let i = stepNumber - 1; i < updated.length; i++) {
        updated[i] = {
          ...updated[i],
          status: 'pending',
          started_at: undefined,
          ended_at: undefined,
          message: undefined,
        };
      }
      return updated;
    });

    // If restarting from steps 1-5, run pipeline through step 5, then continue with step 6
    if (stepNumber <= 5) {
      setWorkflowStage('processing');
      setIsProcessing(true);
      
      // Run from the selected step to step 5
      await runStepsFromTo(stepNumber, 5, currentJobId);
      
      setIsProcessing(false);
      setWorkflowStage('pdf-preview');
      
      toast.success('Steps 1-5 Completed', {
        description: 'PDF generated successfully. Now executing Step 6...',
      });

      // Auto-execute Step 6 based on previous save type
      if (saveType === 'save') {
        await handleSave();
      } else if (saveType === 'save-and-sign') {
        await handleSaveAndSign();
      } else {
        // If no save type was set before, just show PDF preview
        toast.info('PDF Ready for Review', {
          description: 'Choose Save or Save & Sign to complete Step 6',
        });
      }
    } else if (stepNumber === 6) {
      // If restarting step 6 only
      if (saveType === 'save-and-sign') {
        setWorkflowStage('upload-signed');
        setUploadedSignedFile(null);
        toast.info('Ready for Signed PDF Upload', {
          description: 'Please upload the signed PDF to complete Step 6',
        });
      } else if (saveType === 'save') {
        // Re-run save
        await handleSave();
      } else {
        setWorkflowStage('pdf-preview');
        toast.info('Back to PDF Preview', {
          description: 'Choose Save or Save & Sign to complete Step 6',
        });
      }
    }
  };

  const renderRightPanel = () => {
    if (workflowStage === 'processing') {
      return (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="text-lg text-foreground">Generating Rationale Report</h3>
          </div>
          <div className="bg-background border border-border rounded-lg p-12 text-center">
            <Loader2 className="w-16 h-16 mx-auto mb-4 text-blue-500 animate-spin" />
            <p className="text-foreground">Processing manual rationale data...</p>
            <p className="text-sm text-muted-foreground mt-2">Running pipeline steps</p>
          </div>
        </div>
      );
    }

    if (workflowStage === 'pdf-preview') {
      return (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="text-lg text-foreground">Generated PDF Report</h3>
          </div>

          {/* PDF Viewer */}
          <div className="bg-background border border-border rounded-lg overflow-hidden">
            <iframe
              src="https://www.w3.org/WAI/ER/tests/xhtml/testfiles/resources/pdf/dummy.pdf"
              className="w-full h-[500px]"
              title="PDF Report Preview"
            />
          </div>

          {/* Action Buttons - 4 buttons in 2x2 grid */}
          <div className="grid grid-cols-2 gap-3">
            <Button
              onClick={handleDownloadPDF}
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
              onClick={handleDeleteJob}
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

    if (workflowStage === 'saved') {
      return (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="text-lg text-foreground">Rationale Saved Successfully</h3>
          </div>

          <Card className="bg-card border-border p-6">
            <div className="flex items-center gap-3 mb-4">
              <div className="p-3 bg-green-500/20 rounded-lg">
                <Save className="w-6 h-6 text-green-500" />
              </div>
              <div>
                <h4 className="text-foreground">Saved to Rationale Database</h4>
                <p className="text-sm text-muted-foreground">
                  Job ID: {currentJobId}
                </p>
              </div>
            </div>
            <div className="bg-background border border-border rounded-lg p-4">
              <p className="text-sm text-muted-foreground">
                Your rationale report has been saved successfully. You can view it in the Saved Rationale section.
              </p>
            </div>
          </Card>

          {/* PDF Viewer */}
          <div className="bg-background border border-border rounded-lg overflow-hidden">
            <iframe
              src="https://www.w3.org/WAI/ER/tests/xhtml/testfiles/resources/pdf/dummy.pdf"
              className="w-full h-[500px]"
              title="PDF Report Preview"
            />
          </div>

          {/* Download and Sign Now Buttons */}
          <div className="grid grid-cols-2 gap-3">
            <Button
              onClick={handleDownloadPDF}
              className="bg-blue-600 hover:bg-blue-700 text-white"
            >
              <Download className="w-4 h-4 mr-2" />
              Download PDF
            </Button>
            <Button
              onClick={() => {
                setSaveType('save-and-sign');
                setWorkflowStage('upload-signed');
                toast.info('Upload signed PDF', {
                  description: 'Please upload the signed version of your PDF',
                });
              }}
              className="bg-green-600 hover:bg-green-700 text-white"
            >
              <FileSignature className="w-4 h-4 mr-2" />
              Sign Now
            </Button>
          </div>
        </div>
      );
    }

    if (workflowStage === 'completed') {
      return (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="text-lg text-foreground">Workflow Completed</h3>
          </div>

          {/* Show the SignedFileUpload component which will display the signed PDF */}
          <SignedFileUpload
            jobId={currentJobId || ''}
            uploadedFile={uploadedSignedFile}
            onUploadComplete={handleSignedFileUpload}
          />
        </div>
      );
    }

    if (workflowStage === 'upload-signed') {
      return (
        <SignedFileUpload
          jobId={currentJobId || ''}
          uploadedFile={uploadedSignedFile}
          onUploadComplete={handleSignedFileUpload}
        />
      );
    }

    return null;
  };

  return (
    <div className="p-6 space-y-6">
      {/* Page Header */}
      <div>
        <h1 className="text-2xl text-foreground mb-1">Manual Rationale</h1>
        <p className="text-muted-foreground">Create rationale reports with manual data entry</p>
      </div>

      {/* Main Content - Two Column Layout */}
      <Card className="bg-card border-border p-6 shadow-sm">
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Left Column: Form or Progress */}
          <div className="flex flex-col">
            {workflowStage === 'input' ? (
              <>
                <div className="flex items-center gap-3 mb-4">
                  <div className="p-2.5 bg-purple-500/20 rounded-lg">
                    <PenTool className="w-5 h-5 text-purple-500" />
                  </div>
                  <div>
                    <h2 className="text-foreground">Manual Data Entry</h2>
                    <p className="text-xs text-muted-foreground">Enter rationale details manually</p>
                  </div>
                </div>

                <div className="space-y-4">
                  {/* Platform Details */}
                  <div className="space-y-4">
                    <div className="space-y-2">
                      <Label htmlFor="platform-name">Platform Name *</Label>
                      <Select value={platformName} onValueChange={setPlatformName}>
                        <SelectTrigger className="bg-background border-input">
                          <SelectValue placeholder="Select platform" />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="YouTube">YouTube</SelectItem>
                          <SelectItem value="Facebook">Facebook</SelectItem>
                          <SelectItem value="Telegram">Telegram</SelectItem>
                          <SelectItem value="Instagram">Instagram</SelectItem>
                          <SelectItem value="Twitter">Twitter</SelectItem>
                          <SelectItem value="LinkedIn">LinkedIn</SelectItem>
                          <SelectItem value="WhatsApp">WhatsApp</SelectItem>
                          <SelectItem value="Other">Other</SelectItem>
                        </SelectContent>
                      </Select>
                    </div>

                    <div className="space-y-2">
                      <Label htmlFor="platform-id">Platform ID *</Label>
                      <Input
                        id="platform-id"
                        value={platformId}
                        onChange={(e) => setPlatformId(e.target.value)}
                        placeholder="e.g., @channelname, group ID"
                        className="bg-background border-input"
                      />
                    </div>

                    <div className="space-y-2">
                      <Label htmlFor="url">URL (Optional)</Label>
                      <Input
                        id="url"
                        type="url"
                        value={url}
                        onChange={(e) => setUrl(e.target.value)}
                        placeholder="https://..."
                        className="bg-background border-input"
                      />
                    </div>

                    <div className="space-y-2">
                      <Label htmlFor="date">Date *</Label>
                      <div className="relative">
                        <Input
                          id="date"
                          type="date"
                          value={date}
                          onChange={(e) => setDate(e.target.value)}
                          className="bg-background border-input"
                        />
                        <Calendar className="absolute right-3 top-1/2 -translate-y-1/2 w-4 h-4 text-foreground/50 pointer-events-none" />
                      </div>
                    </div>
                  </div>
                </div>
              </>
            ) : (
              <>
                <div className="flex items-center justify-between mb-4">
                  <div>
                    <h2 className="text-foreground">5-Step Pipeline</h2>
                    <p className="text-xs text-muted-foreground">Job ID: {currentJobId}</p>
                  </div>
                  <Button
                    onClick={handleRestart}
                    size="sm"
                    variant="outline"
                    className="border-border hover:bg-accent h-8"
                  >
                    New Analysis
                  </Button>
                </div>

                <div className="flex-1 overflow-y-auto pr-2">
                  <StepProgressTracker
                    steps={jobSteps}
                    onRestartFromStep={handleRestartFromStep}
                  />
                </div>
              </>
            )}
          </div>

          {/* Right Column: Output or Stock Details */}
          <div className="flex flex-col">
            {workflowStage === 'input' ? (
              <>
                <div className="flex items-center justify-between mb-4">
                  <h3 className="text-foreground">Stock Details</h3>
                  <Button
                    onClick={addStockDetail}
                    size="sm"
                    className="bg-primary hover:bg-primary-hover text-primary-foreground h-8"
                  >
                    <Plus className="w-3.5 h-3.5 mr-1.5" />
                    Add Stock
                  </Button>
                </div>

                <div className="space-y-3 flex-1 overflow-y-auto pr-1">
                  {stockDetails.map((stock, index) => (
                    <Card key={stock.id} className="bg-muted border-border p-3 space-y-3">
                      <div className="flex items-center justify-between">
                        <span className="text-xs text-muted-foreground">Stock #{index + 1}</span>
                        {stockDetails.length > 1 && (
                          <Button
                            onClick={() => removeStockDetail(stock.id)}
                            size="sm"
                            variant="ghost"
                            className="text-red-500 hover:text-red-600 hover:bg-red-500/10 h-6 w-6 p-0"
                          >
                            <Trash2 className="w-3.5 h-3.5" />
                          </Button>
                        )}
                      </div>

                      <div className="space-y-2">
                        <div className="space-y-1.5">
                          <Label className="text-xs">Stock Name *</Label>
                          <Input
                            value={stock.stockName}
                            onChange={(e) => updateStockDetail(stock.id, 'stockName', e.target.value)}
                            placeholder="e.g., Reliance"
                            className="bg-background border-input h-9 text-sm"
                          />
                        </div>

                        <div className="grid grid-cols-2 gap-2">
                          <div className="space-y-1.5">
                            <Label className="text-xs">Time *</Label>
                            <div className="relative">
                              <Input
                                type="time"
                                value={stock.time}
                                onChange={(e) => updateStockDetail(stock.id, 'time', e.target.value)}
                                className="bg-background border-input h-9 text-sm"
                              />
                              <Clock className="absolute right-2 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-foreground/50 pointer-events-none" />
                            </div>
                          </div>

                          <div className="space-y-1.5">
                            <Label className="text-xs">Analysis *</Label>
                            <Input
                              value={stock.analysis}
                              onChange={(e) => updateStockDetail(stock.id, 'analysis', e.target.value)}
                              placeholder="Detailed Analysis"
                              className="bg-background border-input h-9 text-sm"
                            />
                          </div>
                        </div>
                      </div>
                    </Card>
                  ))}
                </div>

                {/* Generate Button */}
                <Button
                  onClick={generateRationale}
                  disabled={isProcessing}
                  className="gradient-primary w-full h-11 mt-4"
                >
                  {isProcessing ? (
                    <>
                      <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                      Processing...
                    </>
                  ) : (
                    <>
                      <FileSignature className="w-4 h-4 mr-2" />
                      Generate Rationale
                    </>
                  )}
                </Button>
              </>
            ) : (
              renderRightPanel()
            )}
          </div>
        </div>
      </Card>
    </div>
  );
}
