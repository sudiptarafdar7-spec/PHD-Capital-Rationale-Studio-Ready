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
    <Card className="relative overflow-hidden bg-gradient-to-br from-slate-900 via-blue-900 to-indigo-900 border-2 border-transparent shadow-2xl">
      {/* Animated neon border effect */}
      <div className="absolute inset-0 bg-gradient-to-r from-cyan-500 via-blue-500 to-purple-500 opacity-50 animate-pulse"></div>
      <div className="absolute inset-[2px] bg-gradient-to-br from-slate-900 via-blue-900 to-indigo-900 rounded-lg"></div>
      
      {/* Animated grid background */}
      <div className="absolute inset-0 opacity-20">
        <div className="absolute inset-0" style={{
          backgroundImage: 'linear-gradient(rgba(96, 165, 250, 0.4) 1px, transparent 1px), linear-gradient(90deg, rgba(96, 165, 250, 0.4) 1px, transparent 1px)',
          backgroundSize: '50px 50px',
          animation: 'grid-flow 20s linear infinite'
        }}></div>
      </div>
      
      {/* Animated background shimmer */}
      <div className="absolute inset-0 bg-gradient-to-r from-transparent via-cyan-400/20 to-transparent animate-shimmer"></div>
      
      <div className="relative z-10 p-8 space-y-6">
        {/* AI Loader Icon */}
        <div className="flex justify-center">
          <div className="relative">
            {/* Pulsing background circles with vibrant colors */}
            <div className="absolute inset-0 flex items-center justify-center">
              <div className="w-32 h-32 bg-cyan-500/40 rounded-full animate-ping"></div>
            </div>
            <div className="absolute inset-0 flex items-center justify-center">
              <div className="w-24 h-24 bg-blue-500/50 rounded-full animate-pulse"></div>
            </div>
            
            {/* Main loader with enhanced gradient */}
            <div className="relative bg-gradient-to-br from-cyan-500 via-blue-500 to-purple-600 rounded-full p-6 shadow-2xl shadow-blue-500/50 flex items-center justify-center ring-4 ring-blue-400/30">
              {isCompleted ? (
                <CheckCircle2 className="w-16 h-16 text-white drop-shadow-lg" />
              ) : (
                <div className="relative w-16 h-16 flex items-center justify-center">
                  <Loader2 className="w-16 h-16 text-white animate-spin absolute drop-shadow-lg" />
                  <StepIcon className="w-8 h-8 text-white relative z-10 drop-shadow-md" />
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Job ID Header */}
        {jobId && (
          <div className="text-center space-y-1">
            <div className="inline-flex items-center gap-2 bg-blue-500/20 px-4 py-2 rounded-full border border-cyan-400/40 backdrop-blur-md shadow-lg shadow-blue-500/20">
              <div className="w-2 h-2 bg-green-400 rounded-full animate-pulse shadow-lg shadow-green-400/50"></div>
              <span className="text-xs font-mono text-cyan-100 font-semibold tracking-wider">
                JOB ID: {jobId}
              </span>
            </div>
          </div>
        )}

        {/* Progress Information */}
        <div className="space-y-5 text-center">
          {/* Step Counter */}
          <div className="inline-flex items-center gap-2 bg-gradient-to-r from-purple-600 to-pink-600 px-6 py-3 rounded-full shadow-xl shadow-purple-500/50 backdrop-blur-md border border-purple-400/50">
            <Sparkles className="w-5 h-5 text-yellow-300 animate-pulse drop-shadow-lg" />
            <span className="text-sm font-bold text-white tracking-widest drop-shadow-md">
              STEP {displayStepNumber}/{totalSteps}
            </span>
          </div>

          {/* Current Step Message */}
          <h3 className="text-3xl font-bold text-white px-4 drop-shadow-lg">
            {currentStepConfig?.publicMessage || 'Processing...'}
          </h3>

          {/* Metric Display (for steps 8, 9, 11, 13) */}
          {metricValue !== null && (
            <div className="inline-flex items-center gap-2 bg-gradient-to-r from-emerald-500 to-green-600 text-white px-6 py-3 rounded-full shadow-xl shadow-emerald-500/50 border border-emerald-400/50">
              <div className="w-2 h-2 bg-yellow-300 rounded-full animate-pulse shadow-lg shadow-yellow-300/80"></div>
              <span className="font-bold text-lg drop-shadow-md">
                {metricValue} {currentStepConfig?.showMetrics === 'charts_fetched' ? 'charts' : 'stocks'} {currentStepConfig?.showMetrics === 'stocks_extracted' ? 'extracted' : currentStepConfig?.showMetrics === 'stocks_mapped' ? 'mapped' : currentStepConfig?.showMetrics === 'stocks_cmp' ? 'fetched' : 'generated'}
              </span>
            </div>
          )}
        </div>

        {/* Progress Bar - Enhanced Visibility */}
        <div className="space-y-4 mt-8 bg-slate-800/60 backdrop-blur-md rounded-2xl p-6 border border-cyan-500/30 shadow-xl shadow-blue-500/20">
          <div className="space-y-4">
            {/* Progress Bar Container with Vibrant Colors */}
            <div className="relative h-6 bg-slate-700/80 rounded-full overflow-hidden shadow-inner border-2 border-slate-600/50">
              {/* Animated background pattern */}
              <div className="absolute inset-0 bg-gradient-to-r from-slate-700 via-slate-600 to-slate-700 animate-pulse opacity-50"></div>
              
              {/* Progress Fill with Gradient */}
              <div 
                className="absolute inset-0 bg-gradient-to-r from-cyan-500 via-blue-500 to-purple-600 transition-all duration-500 ease-out shadow-lg"
                style={{ 
                  width: `${progressPercent}%`,
                  boxShadow: '0 0 20px rgba(6, 182, 212, 0.6), 0 0 40px rgba(59, 130, 246, 0.4)'
                }}
              >
                {/* Shimmer effect on progress bar */}
                <div className="absolute inset-0 bg-gradient-to-r from-transparent via-white/30 to-transparent animate-shimmer"></div>
              </div>
              
              {/* Progress percentage text on bar */}
              <div className="absolute inset-0 flex items-center justify-center">
                <span className="text-xs font-bold text-white drop-shadow-lg z-10">
                  {Math.round(progressPercent)}%
                </span>
              </div>
            </div>
            
            {/* Progress Labels */}
            <div className="flex justify-between items-center">
              <span className="text-sm font-bold text-cyan-300 tracking-wider drop-shadow-md">PROGRESS</span>
              <span className="text-lg font-bold text-white bg-gradient-to-r from-cyan-600 to-blue-600 px-4 py-1.5 rounded-full shadow-lg shadow-cyan-500/30 border border-cyan-400/50">
                {Math.round(progressPercent)}%
              </span>
            </div>
          </div>
        </div>

        {/* Processing indicator */}
        <div className="flex items-center justify-center gap-3 text-cyan-200 bg-slate-800/40 backdrop-blur-sm px-6 py-3 rounded-full border border-cyan-500/20">
          <div className="flex gap-1.5">
            <div className="w-2.5 h-2.5 bg-cyan-400 rounded-full animate-bounce shadow-lg shadow-cyan-400/50" style={{ animationDelay: '0ms' }}></div>
            <div className="w-2.5 h-2.5 bg-blue-400 rounded-full animate-bounce shadow-lg shadow-blue-400/50" style={{ animationDelay: '150ms' }}></div>
            <div className="w-2.5 h-2.5 bg-purple-400 rounded-full animate-bounce shadow-lg shadow-purple-400/50" style={{ animationDelay: '300ms' }}></div>
          </div>
          <span className="text-sm font-medium drop-shadow-md">AI is working...</span>
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
        @keyframes grid-flow {
          0% {
            transform: translateY(0);
          }
          100% {
            transform: translateY(50px);
          }
        }
      `}</style>
    </Card>
  );
}
