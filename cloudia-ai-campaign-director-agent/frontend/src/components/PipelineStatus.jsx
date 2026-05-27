import { CheckCircle, Circle, Clock, AlertCircle, Loader } from 'lucide-react';

const STEPS = [
  { key: 'director', label: 'Director' },
  { key: 'planner', label: 'Planner' },
  { key: 'content', label: 'Content' },
  { key: 'edit', label: 'Edit' },
  { key: 'approve', label: 'Approve' },
  { key: 'publish', label: 'Publish' },
];

function StepIcon({ state }) {
  if (state === 'complete') return <CheckCircle className="w-5 h-5 text-green-500" />;
  if (state === 'active') return <Loader className="w-5 h-5 text-blue-500 animate-spin" />;
  if (state === 'error') return <AlertCircle className="w-5 h-5 text-red-500" />;
  if (state === 'waiting') return <Clock className="w-5 h-5 text-yellow-500" />;
  return <Circle className="w-5 h-5 text-gray-300" />;
}

function getStepState(step, pipelineData, campaignStatus) {
  if (!pipelineData) {
    if (campaignStatus === 'active' && step.key === 'director') return 'active';
    return 'pending';
  }
  return pipelineData[step.key] || 'pending';
}

export default function PipelineStatus({ pipelineData, campaignStatus, className = '' }) {
  return (
    <div className={`flex items-center gap-0 ${className}`}>
      {STEPS.map((step, idx) => {
        const state = getStepState(step, pipelineData, campaignStatus);
        return (
          <div key={step.key} className="flex items-center">
            <div className="flex flex-col items-center gap-1 min-w-[72px]">
              <StepIcon state={state} />
              <span
                className={`text-xs font-medium ${
                  state === 'active'
                    ? 'text-blue-600'
                    : state === 'complete'
                    ? 'text-green-600'
                    : state === 'error'
                    ? 'text-red-600'
                    : 'text-gray-400'
                }`}
              >
                {step.label}
              </span>
            </div>
            {idx < STEPS.length - 1 && (
              <div
                className={`h-0.5 w-8 mx-1 ${
                  state === 'complete' ? 'bg-green-400' : 'bg-gray-200'
                }`}
              />
            )}
          </div>
        );
      })}
    </div>
  );
}
