import React from 'react';
import { Loader2, CheckCircle, XCircle } from 'lucide-react';
import { JobStatus } from '../types';

interface ProgressTrackerProps {
  jobStatus: JobStatus | null;
}

export const ProgressTracker: React.FC<ProgressTrackerProps> = ({ jobStatus }) => {
  if (!jobStatus) {
    return null;
  }

  const { status, progress, message } = jobStatus;

  const getStatusIcon = () => {
    switch (status) {
      case 'completed':
        return <CheckCircle className="w-6 h-6 text-green-500" />;
      case 'failed':
        return <XCircle className="w-6 h-6 text-red-500" />;
      case 'processing':
      case 'pending':
        return <Loader2 className="w-6 h-6 text-accent-primary animate-spin" />;
      default:
        return null;
    }
  };

  const getStatusColor = () => {
    switch (status) {
      case 'completed':
        return 'text-green-500';
      case 'failed':
        return 'text-red-500';
      case 'processing':
        return 'text-accent-primary';
      case 'pending':
        return 'text-dark-text-secondary';
      default:
        return 'text-dark-text-primary';
    }
  };

  return (
    <div className="card p-6 space-y-4">
      <div className="flex items-center gap-3">
        {getStatusIcon()}
        <div className="flex-1">
          <div className={`font-medium ${getStatusColor()}`}>
            {status.charAt(0).toUpperCase() + status.slice(1)}
          </div>
          <div className="text-sm text-dark-text-secondary">{message}</div>
        </div>
      </div>

      {(status === 'processing' || status === 'pending') && (
        <div className="space-y-2">
          <div className="flex justify-between text-sm">
            <span className="text-dark-text-secondary">Progress</span>
            <span className="text-dark-text-primary font-medium">
              {Math.round(progress * 100)}%
            </span>
          </div>
          <div className="w-full bg-dark-elevated rounded-full h-2 overflow-hidden">
            <div
              className="bg-accent-primary h-full rounded-full transition-all duration-300"
              style={{ width: `${progress * 100}%` }}
            />
          </div>
        </div>
      )}

      {status === 'failed' && jobStatus.error && (
        <div className="p-3 bg-red-500/10 border border-red-500/50 rounded-apple text-red-400 text-sm">
          {jobStatus.error}
        </div>
      )}
    </div>
  );
};
