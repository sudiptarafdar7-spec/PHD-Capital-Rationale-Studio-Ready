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
    <Card className="relative overflow-hidden border-none shadow-2xl bg-gradient-to-br from-slate-950 via-slate-900 to-slate-950">
      {/* Subtle animated background gradient - single accent */}
      <div className="absolute inset-0 bg-gradient-to-br from-violet-950/40 via-slate-900 to-violet-950/40 animate-slow-drift"></div>
      
      {/* Grain texture for depth */}
      <div className="absolute inset-0 opacity-[0.015]" style={{
        backgroundImage: `url("data:image/svg+xml,%3Csvg viewBox='0 0 400 400' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='noiseFilter'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='4' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23noiseFilter)'/%3E%3C/svg%3E")`
      }}></div>
      
      {/* Subtle scanlines */}
      <div className="absolute inset-0 opacity-[0.03]" style={{
        backgroundImage: 'repeating-linear-gradient(0deg, transparent, transparent 2px, rgba(139, 92, 246, 0.03) 2px, rgba(139, 92, 246, 0.03) 4px)'
      }}></div>
      
      <div className="relative z-10 p-10 space-y-8">
        {/* AI Loader Icon - Minimalist Glassmorphic */}
        <div className="flex justify-center">
          <div className="relative">
            {/* Single subtle glow */}
            {!isCompleted && (
              <div className="absolute inset-0 flex items-center justify-center">
                <div className="w-28 h-28 bg-violet-500/20 rounded-full blur-2xl animate-pulse-slow"></div>
              </div>
            )}
            
            {/* Glass panel loader */}
            <div className="relative bg-slate-900/40 backdrop-blur-xl rounded-full p-8 border border-violet-500/20 shadow-lg">
              {isCompleted ? (
                <CheckCircle2 className="w-14 h-14 text-violet-400" />
              ) : (
                <div className="relative w-14 h-14 flex items-center justify-center">
                  <Loader2 className="w-14 h-14 text-violet-400 animate-spin absolute" />
                  <StepIcon className="w-7 h-7 text-violet-300 relative z-10" />
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Job ID Header - Clean Glass Panel */}
        {jobId && (
          <div className="text-center">
            <div className="inline-flex items-center gap-2.5 bg-slate-900/60 backdrop-blur-md px-5 py-2.5 rounded-lg border border-violet-500/20">
              <div className="w-1.5 h-1.5 bg-emerald-400 rounded-full animate-pulse-slow"></div>
              <span className="text-xs font-mono text-slate-300 font-medium tracking-wider">
                {jobId}
              </span>
            </div>
          </div>
        )}

        {/* Status Information - Clean Typography */}
        <div className="space-y-6 text-center">
          {/* Step Counter - Glass Badge */}
          <div className="inline-flex items-center gap-2.5 bg-slate-900/60 backdrop-blur-md px-5 py-2.5 rounded-lg border border-violet-500/30">
            <Sparkles className="w-4 h-4 text-violet-400" />
            <span className="text-sm font-semibold text-slate-200 tracking-wide">
              STEP {displayStepNumber}/{totalSteps}
            </span>
          </div>

          {/* Current Step Message - High Contrast */}
          <h3 className="text-2xl font-semibold text-white px-4 leading-tight">
            {currentStepConfig?.publicMessage || 'Processing...'}
          </h3>

          {/* Metric Display - Subtle */}
          {metricValue !== null && (
            <div className="inline-flex items-center gap-2.5 bg-slate-900/60 backdrop-blur-md px-5 py-2.5 rounded-lg border border-violet-500/20">
              <div className="w-1.5 h-1.5 bg-violet-400 rounded-full animate-pulse-slow"></div>
              <span className="font-medium text-sm text-slate-300">
                {metricValue} {currentStepConfig?.showMetrics === 'charts_fetched' ? 'charts' : 'stocks'} {currentStepConfig?.showMetrics === 'stocks_extracted' ? 'extracted' : currentStepConfig?.showMetrics === 'stocks_mapped' ? 'mapped' : currentStepConfig?.showMetrics === 'stocks_cmp' ? 'fetched' : 'generated'}
              </span>
            </div>
          )}
        </div>

        {/* Progress Section - Clean Glass Panel */}
        <div className="bg-slate-900/40 backdrop-blur-xl rounded-xl p-6 border border-violet-500/20">
          <div className="space-y-4">
            {/* Progress Bar - Elegant Single Accent */}
            <div className="relative h-3 bg-slate-800/60 rounded-full overflow-hidden border border-slate-700/50">
              {/* Progress fill with smooth gradient */}
              <div 
                className="absolute inset-0 bg-gradient-to-r from-violet-600 to-violet-500 transition-all duration-500 ease-out"
                style={{ 
                  width: `${progressPercent}%`,
                  boxShadow: '0 0 12px rgba(139, 92, 246, 0.5)'
                }}
              >
                {/* Subtle shimmer - single direction */}
                <div className="absolute inset-0 bg-gradient-to-r from-transparent via-white/20 to-transparent animate-shimmer-subtle"></div>
              </div>
            </div>
            
            {/* Progress Labels - Clean Typography */}
            <div className="flex justify-between items-center">
              <span className="text-xs font-medium text-slate-400 tracking-wide uppercase">
                Progress
              </span>
              <span className="text-sm font-semibold text-violet-400">
                {Math.round(progressPercent)}%
              </span>
            </div>
          </div>
        </div>

        {/* AI Working Indicator - Minimal */}
        <div className="flex items-center justify-center gap-2.5 text-slate-400">
          <div className="flex gap-1">
            <div className="w-1.5 h-1.5 bg-violet-500 rounded-full animate-bounce" style={{ animationDelay: '0ms' }}></div>
            <div className="w-1.5 h-1.5 bg-violet-500 rounded-full animate-bounce" style={{ animationDelay: '150ms' }}></div>
            <div className="w-1.5 h-1.5 bg-violet-500 rounded-full animate-bounce" style={{ animationDelay: '300ms' }}></div>
          </div>
          <span className="text-sm font-medium">AI is working</span>
        </div>
      </div>

      <style>{`
        @keyframes slow-drift {
          0%, 100% { 
            background-position: 0% 50%;
            opacity: 0.4;
          }
          50% { 
            background-position: 100% 50%;
            opacity: 0.6;
          }
        }
        
        @keyframes shimmer-subtle {
          0% { transform: translateX(-100%); }
          100% { transform: translateX(100%); }
        }
        
        @keyframes pulse-slow {
          0%, 100% { opacity: 1; }
          50% { opacity: 0.5; }
        }
        
        .animate-slow-drift {
          background-size: 200% 200%;
          animation: slow-drift 25s ease-in-out infinite;
        }
        
        .animate-shimmer-subtle {
          animation: shimmer-subtle 4s ease-in-out infinite;
        }
        
        .animate-pulse-slow {
          animation: pulse-slow 3s ease-in-out infinite;
        }
      `}</style>
    </Card>
  );
}
