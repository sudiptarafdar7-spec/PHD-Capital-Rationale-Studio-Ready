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
    <Card className="relative overflow-hidden border-2 border-transparent shadow-2xl">
      {/* Animated moving gradient background */}
      <div className="absolute inset-0 bg-gradient-to-br from-purple-900 via-blue-900 to-cyan-900 animate-gradient-shift"></div>
      
      {/* Layered moving gradients for depth */}
      <div className="absolute inset-0 bg-gradient-to-tr from-pink-900/40 via-purple-900/40 to-blue-900/40 animate-gradient-shift-reverse"></div>
      <div className="absolute inset-0 bg-gradient-to-bl from-cyan-900/30 via-indigo-900/30 to-purple-900/30 animate-gradient-pulse"></div>
      
      {/* Animated glowing border */}
      <div className="absolute inset-0 bg-gradient-to-r from-cyan-500 via-purple-500 to-pink-500 opacity-60 animate-border-flow"></div>
      <div className="absolute inset-[3px] bg-gradient-to-br from-slate-900/95 via-blue-950/95 to-purple-950/95 rounded-lg backdrop-blur-xl"></div>
      
      {/* Animated orbs floating in background */}
      <div className="absolute top-10 left-10 w-64 h-64 bg-purple-500/20 rounded-full blur-3xl animate-float-slow"></div>
      <div className="absolute bottom-10 right-10 w-80 h-80 bg-cyan-500/20 rounded-full blur-3xl animate-float-slower"></div>
      <div className="absolute top-1/2 left-1/2 w-96 h-96 bg-blue-500/15 rounded-full blur-3xl animate-float-medium"></div>
      
      {/* Enhanced animated grid */}
      <div className="absolute inset-0 opacity-30">
        <div className="absolute inset-0 animate-grid-flow" style={{
          backgroundImage: 'linear-gradient(rgba(6, 182, 212, 0.5) 1px, transparent 1px), linear-gradient(90deg, rgba(6, 182, 212, 0.5) 1px, transparent 1px)',
          backgroundSize: '50px 50px'
        }}></div>
      </div>
      
      {/* Multiple shimmer effects */}
      <div className="absolute inset-0 bg-gradient-to-r from-transparent via-cyan-400/30 to-transparent animate-shimmer-fast"></div>
      <div className="absolute inset-0 bg-gradient-to-l from-transparent via-purple-400/20 to-transparent animate-shimmer-slow"></div>
      
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
            <div className="inline-flex items-center gap-2 bg-gradient-to-r from-blue-600/80 to-cyan-600/80 px-5 py-2.5 rounded-full border-2 border-cyan-300/60 backdrop-blur-xl shadow-2xl shadow-cyan-500/50 animate-glow-pulse">
              <div className="w-2.5 h-2.5 bg-green-300 rounded-full animate-pulse shadow-xl shadow-green-300/80 ring-2 ring-green-200/50"></div>
              <span className="text-xs font-mono text-white font-bold tracking-widest drop-shadow-lg">
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

        {/* Progress Bar - Ultra Vibrant Design */}
        <div className="space-y-4 mt-8 bg-gradient-to-br from-indigo-900/80 via-purple-900/80 to-pink-900/80 backdrop-blur-xl rounded-3xl p-7 border-2 border-purple-400/60 shadow-2xl shadow-purple-500/40 animate-box-glow">
          <div className="space-y-5">
            {/* Progress Bar Container with Animated Gradient */}
            <div className="relative h-8 bg-gradient-to-r from-slate-800 via-slate-700 to-slate-800 rounded-full overflow-hidden shadow-2xl border-2 border-purple-300/40">
              {/* Animated background waves */}
              <div className="absolute inset-0 bg-gradient-to-r from-purple-600/30 via-blue-600/30 to-cyan-600/30 animate-wave"></div>
              
              {/* Progress Fill with Multi-Color Gradient */}
              <div 
                className="absolute inset-0 bg-gradient-to-r from-pink-500 via-purple-500 via-blue-500 to-cyan-500 transition-all duration-700 ease-out"
                style={{ 
                  width: `${progressPercent}%`,
                  boxShadow: '0 0 30px rgba(236, 72, 153, 0.8), 0 0 50px rgba(168, 85, 247, 0.6), 0 0 70px rgba(59, 130, 246, 0.4)',
                  filter: 'brightness(1.2)'
                }}
              >
                {/* Triple shimmer effect */}
                <div className="absolute inset-0 bg-gradient-to-r from-transparent via-white/50 to-transparent animate-shimmer-ultra"></div>
                <div className="absolute inset-0 bg-gradient-to-l from-transparent via-yellow-200/30 to-transparent animate-shimmer-reverse"></div>
              </div>
              
              {/* Glowing percentage text on bar */}
              <div className="absolute inset-0 flex items-center justify-center">
                <span className="text-sm font-extrabold text-white drop-shadow-2xl z-10 tracking-wide" style={{
                  textShadow: '0 0 10px rgba(255,255,255,0.8), 0 0 20px rgba(255,255,255,0.5)'
                }}>
                  {Math.round(progressPercent)}%
                </span>
              </div>
            </div>
            
            {/* Progress Labels with Gradient */}
            <div className="flex justify-between items-center">
              <span className="text-sm font-bold bg-gradient-to-r from-cyan-300 via-purple-300 to-pink-300 bg-clip-text text-transparent tracking-widest drop-shadow-xl animate-text-glow">
                PROGRESS
              </span>
              <span className="text-xl font-extrabold text-white bg-gradient-to-r from-pink-600 via-purple-600 to-cyan-600 px-5 py-2 rounded-full shadow-2xl shadow-purple-500/60 border-2 border-purple-300/70 animate-badge-pulse">
                {Math.round(progressPercent)}%
              </span>
            </div>
          </div>
        </div>

        {/* Processing indicator with enhanced design */}
        <div className="flex items-center justify-center gap-3 bg-gradient-to-r from-blue-900/70 via-purple-900/70 to-pink-900/70 backdrop-blur-xl px-8 py-4 rounded-full border-2 border-purple-400/50 shadow-2xl shadow-purple-500/40 animate-indicator-glow">
          <div className="flex gap-2">
            <div className="w-3 h-3 bg-gradient-to-br from-cyan-400 to-cyan-600 rounded-full animate-bounce shadow-xl shadow-cyan-400/80 ring-2 ring-cyan-200/50" style={{ animationDelay: '0ms' }}></div>
            <div className="w-3 h-3 bg-gradient-to-br from-purple-400 to-purple-600 rounded-full animate-bounce shadow-xl shadow-purple-400/80 ring-2 ring-purple-200/50" style={{ animationDelay: '150ms' }}></div>
            <div className="w-3 h-3 bg-gradient-to-br from-pink-400 to-pink-600 rounded-full animate-bounce shadow-xl shadow-pink-400/80 ring-2 ring-pink-200/50" style={{ animationDelay: '300ms' }}></div>
          </div>
          <span className="text-sm font-bold text-white drop-shadow-lg tracking-wide">AI is working...</span>
        </div>
      </div>

      <style>{`
        @keyframes shimmer {
          0% { transform: translateX(-100%); }
          100% { transform: translateX(100%); }
        }
        @keyframes shimmer-ultra {
          0% { transform: translateX(-100%) skewX(-15deg); }
          100% { transform: translateX(200%) skewX(-15deg); }
        }
        @keyframes shimmer-reverse {
          0% { transform: translateX(100%); }
          100% { transform: translateX(-100%); }
        }
        @keyframes shimmer-fast {
          0% { transform: translateX(-100%); }
          100% { transform: translateX(100%); }
        }
        @keyframes shimmer-slow {
          0% { transform: translateX(-100%); }
          100% { transform: translateX(100%); }
        }
        @keyframes grid-flow {
          0% { transform: translateY(0); }
          100% { transform: translateY(50px); }
        }
        @keyframes gradient-shift {
          0% { background-position: 0% 50%; }
          50% { background-position: 100% 50%; }
          100% { background-position: 0% 50%; }
        }
        @keyframes gradient-shift-reverse {
          0% { background-position: 100% 50%; }
          50% { background-position: 0% 50%; }
          100% { background-position: 100% 50%; }
        }
        @keyframes gradient-pulse {
          0%, 100% { opacity: 0.3; }
          50% { opacity: 0.6; }
        }
        @keyframes border-flow {
          0% { transform: rotate(0deg); }
          100% { transform: rotate(360deg); }
        }
        @keyframes float-slow {
          0%, 100% { transform: translate(0, 0) scale(1); }
          33% { transform: translate(30px, -30px) scale(1.1); }
          66% { transform: translate(-20px, 20px) scale(0.9); }
        }
        @keyframes float-slower {
          0%, 100% { transform: translate(0, 0) scale(1); }
          33% { transform: translate(-40px, 30px) scale(1.15); }
          66% { transform: translate(30px, -25px) scale(0.95); }
        }
        @keyframes float-medium {
          0%, 100% { transform: translate(0, 0) rotate(0deg); }
          50% { transform: translate(20px, -20px) rotate(10deg); }
        }
        @keyframes glow-pulse {
          0%, 100% { box-shadow: 0 0 20px rgba(6, 182, 212, 0.5), 0 0 40px rgba(168, 85, 247, 0.3); }
          50% { box-shadow: 0 0 30px rgba(6, 182, 212, 0.8), 0 0 60px rgba(168, 85, 247, 0.5); }
        }
        @keyframes box-glow {
          0%, 100% { box-shadow: 0 0 30px rgba(168, 85, 247, 0.4), 0 0 60px rgba(236, 72, 153, 0.2); }
          50% { box-shadow: 0 0 50px rgba(168, 85, 247, 0.6), 0 0 90px rgba(236, 72, 153, 0.4); }
        }
        @keyframes text-glow {
          0%, 100% { filter: drop-shadow(0 0 5px rgba(34, 211, 238, 0.8)); }
          50% { filter: drop-shadow(0 0 15px rgba(168, 85, 247, 1)); }
        }
        @keyframes badge-pulse {
          0%, 100% { transform: scale(1); }
          50% { transform: scale(1.05); }
        }
        @keyframes indicator-glow {
          0%, 100% { box-shadow: 0 0 20px rgba(168, 85, 247, 0.4); }
          50% { box-shadow: 0 0 40px rgba(168, 85, 247, 0.7); }
        }
        @keyframes wave {
          0% { transform: translateX(-100%); }
          100% { transform: translateX(100%); }
        }
        
        .animate-shimmer { animation: shimmer 3s infinite; }
        .animate-shimmer-ultra { animation: shimmer-ultra 2s infinite; }
        .animate-shimmer-reverse { animation: shimmer-reverse 4s infinite; }
        .animate-shimmer-fast { animation: shimmer-fast 2s infinite; }
        .animate-shimmer-slow { animation: shimmer-slow 5s infinite; }
        .animate-grid-flow { animation: grid-flow 20s linear infinite; }
        .animate-gradient-shift { animation: gradient-shift 8s ease infinite; background-size: 200% 200%; }
        .animate-gradient-shift-reverse { animation: gradient-shift-reverse 10s ease infinite; background-size: 200% 200%; }
        .animate-gradient-pulse { animation: gradient-pulse 4s ease-in-out infinite; }
        .animate-border-flow { animation: border-flow 6s linear infinite; }
        .animate-float-slow { animation: float-slow 20s ease-in-out infinite; }
        .animate-float-slower { animation: float-slower 25s ease-in-out infinite; }
        .animate-float-medium { animation: float-medium 15s ease-in-out infinite; }
        .animate-glow-pulse { animation: glow-pulse 3s ease-in-out infinite; }
        .animate-box-glow { animation: box-glow 4s ease-in-out infinite; }
        .animate-text-glow { animation: text-glow 3s ease-in-out infinite; }
        .animate-badge-pulse { animation: badge-pulse 2s ease-in-out infinite; }
        .animate-indicator-glow { animation: indicator-glow 3s ease-in-out infinite; }
        .animate-wave { animation: wave 3s linear infinite; }
      `}</style>
    </Card>
  );
}
