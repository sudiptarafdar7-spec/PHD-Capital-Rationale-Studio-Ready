import { RotateCcw, Loader2, CheckCircle2, XCircle, Sparkles } from 'lucide-react';
import { Button } from './ui/button';
import { Progress } from './ui/progress';
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
  onRestart?: () => void;
}

export default function AIStyleJobRunner({
  jobSteps,
  currentStepNumber,
  progressPercent,
  jobStatus,
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
    <Card className="relative overflow-hidden bg-gradient-to-br from-blue-50 via-purple-50 to-pink-50 dark:from-blue-950/20 dark:via-purple-950/20 dark:to-pink-950/20 border-blue-200 dark:border-blue-800">
      {/* Animated background shimmer */}
      <div className="absolute inset-0 bg-gradient-to-r from-transparent via-white/30 to-transparent dark:via-white/10 animate-shimmer"></div>
      
      <div className="relative z-10 p-12 space-y-8">
        {/* AI Loader Icon */}
        <div className="flex justify-center">
          <div className="relative">
            {/* Pulsing background circles */}
            <div className="absolute inset-0 flex items-center justify-center">
              <div className="w-32 h-32 bg-blue-400/30 rounded-full animate-ping"></div>
            </div>
            <div className="absolute inset-0 flex items-center justify-center">
              <div className="w-24 h-24 bg-purple-400/40 rounded-full animate-pulse"></div>
            </div>
            
            {/* Main loader */}
            <div className="relative bg-gradient-to-br from-blue-500 to-purple-600 rounded-full p-6 shadow-2xl">
              {isCompleted ? (
                <CheckCircle2 className="w-16 h-16 text-white" />
              ) : (
                <div className="relative">
                  <Loader2 className="w-16 h-16 text-white animate-spin" />
                  <StepIcon className="w-8 h-8 text-white/90 absolute top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2" />
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Progress Information */}
        <div className="space-y-4 text-center">
          {/* Step Counter */}
          <div className="inline-flex items-center gap-2 bg-white/80 dark:bg-gray-800/80 px-4 py-2 rounded-full shadow-sm backdrop-blur-sm">
            <Sparkles className="w-4 h-4 text-purple-500" />
            <span className="text-sm font-semibold text-gray-700 dark:text-gray-300">
              Step {displayStepNumber}/{totalSteps}
            </span>
          </div>

          {/* Current Step Message */}
          <h3 className="text-2xl font-semibold text-gray-800 dark:text-gray-100">
            {currentStepConfig?.publicMessage || 'Processing...'}
          </h3>

          {/* Metric Display (for steps 8, 9, 11, 13) */}
          {metricValue !== null && (
            <div className="inline-flex items-center gap-2 bg-gradient-to-r from-green-500 to-emerald-500 text-white px-6 py-3 rounded-full shadow-lg">
              <div className="w-2 h-2 bg-white rounded-full animate-pulse"></div>
              <span className="font-bold text-lg">
                {metricValue} {currentStepConfig?.showMetrics === 'charts_fetched' ? 'charts' : 'stocks'} {currentStepConfig?.showMetrics === 'stocks_extracted' ? 'extracted' : currentStepConfig?.showMetrics === 'stocks_mapped' ? 'mapped' : currentStepConfig?.showMetrics === 'stocks_cmp' ? 'fetched' : 'generated'}
              </span>
            </div>
          )}
        </div>

        {/* Progress Bar */}
        <div className="space-y-3">
          <Progress 
            value={progressPercent} 
            className="h-3 bg-white/50 dark:bg-gray-700/50 backdrop-blur-sm"
          />
          <div className="flex justify-between items-center text-sm">
            <span className="text-gray-600 dark:text-gray-400">Progress</span>
            <span className="font-semibold text-gray-700 dark:text-gray-300 bg-white/80 dark:bg-gray-800/80 px-3 py-1 rounded-full backdrop-blur-sm">
              {Math.round(progressPercent)}%
            </span>
          </div>
        </div>

        {/* Processing indicator */}
        <div className="flex items-center justify-center gap-2 text-gray-600 dark:text-gray-400">
          <div className="flex gap-1">
            <div className="w-2 h-2 bg-blue-500 rounded-full animate-bounce" style={{ animationDelay: '0ms' }}></div>
            <div className="w-2 h-2 bg-purple-500 rounded-full animate-bounce" style={{ animationDelay: '150ms' }}></div>
            <div className="w-2 h-2 bg-pink-500 rounded-full animate-bounce" style={{ animationDelay: '300ms' }}></div>
          </div>
          <span className="text-sm">AI is working...</span>
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
