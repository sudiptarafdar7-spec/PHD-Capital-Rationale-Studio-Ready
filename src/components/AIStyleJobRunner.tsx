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
    <Card className="relative overflow-hidden border-4 border-transparent shadow-2xl">
      {/* Vibrant Animated Moving Gradient Background - VISIBLE */}
      <div className="absolute inset-0 bg-gradient-to-br from-indigo-600 via-purple-600 to-pink-600 animate-gradient-move"></div>
      
      {/* Secondary Animated Layer for depth */}
      <div className="absolute inset-0 bg-gradient-to-tr from-blue-500 via-cyan-500 to-teal-500 opacity-50 animate-gradient-slow"></div>
      
      {/* Animated neon border effect */}
      <div className="absolute inset-0 bg-gradient-to-r from-cyan-400 via-purple-500 to-pink-500 opacity-70 animate-pulse rounded-lg"></div>
      
      {/* Dark overlay for contrast - LIGHTER so background shows */}
      <div className="absolute inset-[4px] bg-gradient-to-br from-slate-900/70 via-slate-800/60 to-slate-900/70 backdrop-blur-sm rounded-lg"></div>
      
      {/* Animated grid background */}
      <div className="absolute inset-0 opacity-20 z-[5]">
        <div className="absolute inset-0" style={{
          backgroundImage: 'linear-gradient(rgba(139, 92, 246, 0.3) 1px, transparent 1px), linear-gradient(90deg, rgba(139, 92, 246, 0.3) 1px, transparent 1px)',
          backgroundSize: '50px 50px',
          animation: 'grid-flow 20s linear infinite'
        }}></div>
      </div>
      
      {/* Animated background shimmer */}
      <div className="absolute inset-0 bg-gradient-to-r from-transparent via-white/15 to-transparent animate-shimmer z-[6]"></div>
      
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
            <div className="inline-flex items-center gap-3 bg-gradient-to-r from-blue-600 to-cyan-600 px-6 py-3 rounded-xl border-2 border-cyan-300 shadow-2xl shadow-cyan-500/50">
              <div className="w-3 h-3 bg-green-400 rounded-full animate-pulse shadow-lg shadow-green-400/80"></div>
              <span className="text-sm font-mono text-white font-extrabold tracking-widest drop-shadow-lg">
                JOB ID: {jobId}
              </span>
            </div>
          </div>
        )}

        {/* Progress Information */}
        <div className="space-y-5 text-center">
          {/* Step Counter */}
          <div className="inline-flex items-center gap-3 bg-gradient-to-r from-purple-600 via-fuchsia-600 to-pink-600 px-8 py-4 rounded-2xl shadow-2xl shadow-purple-500/70 border-3 border-pink-300">
            <Sparkles className="w-7 h-7 text-yellow-300 animate-pulse drop-shadow-2xl" />
            <span className="text-lg font-extrabold text-white tracking-widest drop-shadow-lg">
              STEP {displayStepNumber}/{totalSteps}
            </span>
          </div>

          {/* Current Step Message Box */}
          <div className="bg-gradient-to-br from-blue-700 to-indigo-700 px-10 py-8 rounded-3xl border-3 border-blue-300 shadow-2xl shadow-blue-500/50">
            <h3 className="text-4xl font-bold text-white drop-shadow-2xl">
              {currentStepConfig?.publicMessage || 'Processing...'}
            </h3>
          </div>

          {/* Metric Display (for steps 8, 9, 11, 13) */}
          {metricValue !== null && (
            <div className="inline-flex items-center gap-3 bg-gradient-to-r from-emerald-600 to-teal-600 text-white px-8 py-4 rounded-2xl shadow-2xl shadow-emerald-500/70 border-3 border-emerald-300">
              <div className="w-3 h-3 bg-yellow-300 rounded-full animate-pulse shadow-xl shadow-yellow-300/90"></div>
              <span className="font-extrabold text-xl drop-shadow-lg">
                {metricValue} {currentStepConfig?.showMetrics === 'charts_fetched' ? 'charts' : 'stocks'} {currentStepConfig?.showMetrics === 'stocks_extracted' ? 'extracted' : currentStepConfig?.showMetrics === 'stocks_mapped' ? 'mapped' : currentStepConfig?.showMetrics === 'stocks_cmp' ? 'fetched' : 'generated'}
              </span>
            </div>
          )}
        </div>

        {/* Progress Bar - Enhanced Visibility */}
        <div className="space-y-4 mt-8 bg-gradient-to-br from-slate-700 to-slate-800 rounded-3xl p-8 border-3 border-cyan-400 shadow-2xl shadow-cyan-500/50">
          <div className="space-y-5">
            {/* Progress Bar Container with Vibrant Colors */}
            <div className="relative h-8 bg-gradient-to-r from-slate-900 via-slate-800 to-slate-900 rounded-full overflow-hidden shadow-2xl border-2 border-slate-500">
              {/* Animated background pattern */}
              <div className="absolute inset-0 bg-gradient-to-r from-slate-800 via-slate-700 to-slate-800 animate-pulse"></div>
              
              {/* Progress Fill with Vibrant Gradient */}
              <div 
                className="absolute inset-0 bg-gradient-to-r from-cyan-400 via-blue-500 to-purple-600 transition-all duration-500 ease-out"
                style={{ 
                  width: `${progressPercent}%`,
                  boxShadow: '0 0 30px rgba(6, 182, 212, 1), 0 0 60px rgba(59, 130, 246, 0.7), 0 0 90px rgba(168, 85, 247, 0.5)'
                }}
              >
                {/* Shimmer effect on progress bar */}
                <div className="absolute inset-0 bg-gradient-to-r from-transparent via-white/50 to-transparent animate-shimmer"></div>
                
                {/* Glow effect */}
                <div className="absolute inset-0 bg-gradient-to-t from-white/30 to-transparent"></div>
              </div>
              
              {/* Progress percentage text on bar */}
              <div className="absolute inset-0 flex items-center justify-center">
                <span className="text-base font-extrabold text-white drop-shadow-2xl z-10">
                  {Math.round(progressPercent)}%
                </span>
              </div>
            </div>
            
            {/* Progress Labels */}
            <div className="flex justify-between items-center">
              <span className="text-lg font-extrabold text-cyan-200 tracking-widest drop-shadow-lg">PROGRESS</span>
              <span className="text-2xl font-extrabold text-white bg-gradient-to-r from-cyan-600 via-blue-600 to-purple-600 px-6 py-2.5 rounded-xl shadow-2xl shadow-cyan-500/50 border-2 border-cyan-300">
                {Math.round(progressPercent)}%
              </span>
            </div>
          </div>
        </div>

        {/* Processing indicator */}
        <div className="flex items-center justify-center gap-4 text-white bg-gradient-to-r from-indigo-600 to-purple-600 px-8 py-5 rounded-2xl border-3 border-purple-300 shadow-2xl shadow-purple-500/50">
          <div className="flex gap-2.5">
            <div className="w-3.5 h-3.5 bg-cyan-300 rounded-full animate-bounce shadow-xl shadow-cyan-400/80" style={{ animationDelay: '0ms' }}></div>
            <div className="w-3.5 h-3.5 bg-blue-300 rounded-full animate-bounce shadow-xl shadow-blue-400/80" style={{ animationDelay: '150ms' }}></div>
            <div className="w-3.5 h-3.5 bg-purple-300 rounded-full animate-bounce shadow-xl shadow-purple-400/80" style={{ animationDelay: '300ms' }}></div>
          </div>
          <span className="text-lg font-extrabold drop-shadow-lg">AI is working...</span>
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
        @keyframes gradient-move {
          0% {
            background-position: 0% 50%;
          }
          50% {
            background-position: 100% 50%;
          }
          100% {
            background-position: 0% 50%;
          }
        }
        .animate-gradient-move {
          background-size: 200% 200%;
          animation: gradient-move 8s ease infinite;
        }
        @keyframes gradient-slow {
          0% {
            background-position: 0% 0%;
          }
          50% {
            background-position: 100% 100%;
          }
          100% {
            background-position: 0% 0%;
          }
        }
        .animate-gradient-slow {
          background-size: 300% 300%;
          animation: gradient-slow 15s ease infinite;
        }
      `}</style>
    </Card>
  );
}
