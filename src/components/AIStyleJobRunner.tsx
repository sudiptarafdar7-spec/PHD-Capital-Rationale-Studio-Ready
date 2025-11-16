import { RotateCcw, Loader2, CheckCircle2, XCircle, Sparkles } from 'lucide-react';
import { Button } from './ui/button';
import { Card } from './ui/card';
import { getStepConfig, getTotalSteps } from '../lib/ai-steps-config';

interface JobStep {
  step_number: number;
  name: string;
  status: 'pending' | 'running' | 'success' | 'failed';
  message?: string | null;
  outputFiles?: string[];
}

interface AIStyleJobRunnerProps {
  jobSteps: JobStep[];
  currentStepNumber: number;
  progressPercent: number;
  jobStatus: string;
  jobId?: string;
  onRestart?: () => void;
}

export default function AIStyleJobRunner({
  jobSteps,
  currentStepNumber,
  progressPercent,
  jobStatus,
  jobId,
  onRestart
}: AIStyleJobRunnerProps) {
  const totalSteps = getTotalSteps();
  
  // Calculate the actual display step number from jobSteps array
  // Prefer: running → failed → next pending → default to 1
  const calculateDisplayStep = (): number => {
    // Find first running step
    const runningStep = jobSteps.find(step => step.status === 'running');
    if (runningStep) return runningStep.step_number;
    
    // Find first failed step
    const failedStep = jobSteps.find(step => step.status === 'failed');
    if (failedStep) return failedStep.step_number;
    
    // Find next pending step
    const pendingStep = jobSteps.find(step => step.status === 'pending');
    if (pendingStep) return pendingStep.step_number;
    
    // Default to currentStepNumber if >= 1, otherwise step 1
    return Math.max(1, currentStepNumber);
  };
  
  const displayStepNumber = calculateDisplayStep();
  const currentStepConfig = getStepConfig(displayStepNumber);
  const currentJobStep = jobSteps.find(step => step.step_number === displayStepNumber);
  
  const isFailed = jobStatus === 'failed' || currentJobStep?.status === 'failed';
  const isCompleted = displayStepNumber >= totalSteps && jobStatus !== 'failed';

  // Extract metric from step message if available (lightweight parsing, no backend changes)
  const getMetricValue = (): number | null => {
    if (!currentJobStep || !currentStepConfig?.showMetrics) return null;

    const message = currentJobStep.message || '';
    
    // Try to extract numbers from success messages like "Extracted 25 stocks" or "Fetched 10 charts"
    const numberMatch = message.match(/(\d+)\s+(stocks?|charts?)/i);
    if (numberMatch) {
      return parseInt(numberMatch[1], 10);
    }

    return null;
  };

  const metricValue = getMetricValue();
  const StepIcon = currentStepConfig?.icon || Sparkles;

  if (isFailed) {
    return (
      <Card className="relative overflow-hidden bg-gradient-to-br from-red-50 to-red-100 dark:from-red-950/20 dark:to-red-900/20 border-red-200 dark:border-red-800">
        <div className="p-12 space-y-6">
          <div className="flex flex-col items-center justify-center text-center space-y-4">
            <div className="relative">
              <div className="absolute inset-0 bg-red-500/20 rounded-full animate-pulse"></div>
              <XCircle className="w-20 h-20 text-red-500 relative z-10" />
            </div>
            
            <div className="space-y-2">
              <h3 className="text-2xl font-semibold text-red-700 dark:text-red-300">
                Processing Failed
              </h3>
              <p className="text-red-600 dark:text-red-400 max-w-md">
                {currentJobStep?.message || 'An error occurred during processing'}
              </p>
            </div>

            <div className="pt-4">
              {onRestart && (
                <Button
                  onClick={onRestart}
                  className="bg-red-600 hover:bg-red-700 text-white"
                  size="lg"
                >
                  <RotateCcw className="w-4 h-4 mr-2" />
                  Restart Job
                </Button>
              )}
            </div>
          </div>
        </div>
      </Card>
    );
  }

  return (
    <Card className="relative overflow-hidden border border-slate-700/50 shadow-2xl bg-gradient-to-br from-slate-900 via-blue-950 to-slate-900">
      {/* Subtle grid background */}
      <div className="absolute inset-0 opacity-5">
        <div className="absolute inset-0" style={{
          backgroundImage: 'linear-gradient(rgba(100, 149, 237, 0.3) 1px, transparent 1px), linear-gradient(90deg, rgba(100, 149, 237, 0.3) 1px, transparent 1px)',
          backgroundSize: '40px 40px'
        }}></div>
      </div>
      
      <div className="relative z-10 p-8 space-y-6">
        {/* AI Loader Icon */}
        <div className="flex justify-center">
          <div className="relative">
            {/* Subtle glowing background */}
            <div className="absolute inset-0 flex items-center justify-center">
              <div className="w-28 h-28 bg-blue-500/20 rounded-full blur-2xl"></div>
            </div>
            
            {/* Main loader icon */}
            <div className="relative bg-slate-800/50 border border-blue-500/30 rounded-full p-5 shadow-lg shadow-blue-500/20 flex items-center justify-center">
              {isCompleted ? (
                <CheckCircle2 className="w-14 h-14 text-blue-400" />
              ) : (
                <div className="relative w-14 h-14 flex items-center justify-center">
                  <Loader2 className="w-14 h-14 text-blue-400 animate-spin absolute" />
                  <StepIcon className="w-7 h-7 text-blue-300 relative z-10" />
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Job ID Header */}
        {jobId && (
          <div className="text-center space-y-1">
            <div className="inline-flex items-center gap-2 bg-slate-800/60 backdrop-blur-sm px-5 py-2.5 rounded-full border border-slate-600/40">
              <span className="text-xs font-mono text-slate-300 tracking-wider">
                JOB ID: {jobId}
              </span>
            </div>
          </div>
        )}

        {/* Progress Information */}
        <div className="space-y-4 text-center">
          {/* Step Counter */}
          <div className="inline-flex items-center gap-2 bg-slate-800/60 backdrop-blur-sm px-5 py-2.5 rounded-full border border-slate-600/40">
            <Sparkles className="w-4 h-4 text-blue-400" />
            <span className="text-sm font-semibold text-slate-200 tracking-wide">
              STEP {displayStepNumber}/{totalSteps}
            </span>
          </div>

          {/* Current Step Message Box */}
          <div className="bg-slate-800/40 backdrop-blur-sm px-8 py-6 rounded-3xl border border-slate-600/30">
            <h3 className="text-3xl font-semibold text-white">
              {currentStepConfig?.publicMessage || 'Processing...'}
            </h3>
          </div>

          {/* Metric Display (for steps 8, 9, 11, 13) */}
          {metricValue !== null && (
            <div className="inline-flex items-center gap-2 bg-slate-800/60 backdrop-blur-sm text-slate-200 px-5 py-2.5 rounded-full border border-slate-600/40">
              <div className="w-2 h-2 bg-blue-400 rounded-full"></div>
              <span className="font-medium text-sm">
                {metricValue} {currentStepConfig?.showMetrics === 'charts_fetched' ? 'charts' : 'stocks'} {currentStepConfig?.showMetrics === 'stocks_extracted' ? 'extracted' : currentStepConfig?.showMetrics === 'stocks_mapped' ? 'mapped' : currentStepConfig?.showMetrics === 'stocks_cmp' ? 'fetched' : 'generated'}
              </span>
            </div>
          )}
        </div>

        {/* Progress Bar - Clean Design */}
        <div className="space-y-3 mt-6 bg-slate-800/40 backdrop-blur-sm rounded-3xl p-6 border border-slate-600/30">
          <div className="space-y-4">
            {/* Progress Bar with Percentage Badge */}
            <div className="flex items-center gap-4">
              {/* Progress Bar */}
              <div className="flex-1 relative h-3 bg-slate-700/50 rounded-full overflow-hidden border border-slate-600/30">
                {/* Progress Fill */}
                <div 
                  className="absolute inset-y-0 left-0 bg-gradient-to-r from-blue-500 to-indigo-600 rounded-full transition-all duration-500 ease-out"
                  style={{ 
                    width: `${progressPercent}%`
                  }}
                >
                  {/* Subtle shimmer */}
                  <div className="absolute inset-0 bg-gradient-to-r from-transparent via-white/20 to-transparent animate-shimmer"></div>
                </div>
              </div>
              
              {/* Percentage Badge */}
              <div className="bg-slate-700/60 backdrop-blur-sm px-4 py-1.5 rounded-full border border-slate-600/40 min-w-[70px] text-center">
                <span className="text-lg font-semibold text-slate-200">
                  {Math.round(progressPercent)}%
                </span>
              </div>
            </div>
          </div>
        </div>

        {/* Processing indicator */}
        <div className="flex items-center justify-center gap-3 text-slate-300 bg-slate-800/40 backdrop-blur-sm px-6 py-4 rounded-3xl border border-slate-600/30">
          <span className="text-sm">*AI is working hard to process your audio...</span>
        </div>
      </div>

      <style>{`
        @keyframes shimmer {
          0% {
            transform: translateX(-100%);
          }
          100% {
            transform: translateX(100%);
          }
        }
        .animate-shimmer {
          animation: shimmer 3s infinite;
        }
      `}</style>
    </Card>
  );
}
