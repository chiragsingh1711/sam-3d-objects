import React, { useState, useCallback, useEffect } from 'react';
import { ImageUpload } from './components/ImageUpload';
import { MaskDrawer } from './components/MaskDrawer';
import { ControlPanel } from './components/ControlPanel';
import { ProgressTracker } from './components/ProgressTracker';
import { ResultViewer } from './components/ResultViewer';
import { api } from './utils/api';
import { ImageData, GenerationOptions, JobStatus } from './types';
import { Home } from 'lucide-react';

type AppState = 'upload' | 'mask' | 'generate' | 'result';

function App() {
  const [state, setState] = useState<AppState>('upload');
  const [imageData, setImageData] = useState<ImageData | null>(null);
  const [imageFile, setImageFile] = useState<File | null>(null);
  const [jobId, setJobId] = useState<string | null>(null);
  const [jobStatus, setJobStatus] = useState<JobStatus | null>(null);
  const [resultUrls, setResultUrls] = useState<{
    plyUrl?: string;
    glbUrl?: string;
  }>({});

  // Poll job status
  useEffect(() => {
    if (!jobId || jobStatus?.status === 'completed' || jobStatus?.status === 'failed') {
      return;
    }

    const pollInterval = setInterval(async () => {
      try {
        const status = await api.getJobStatus(jobId);
        setJobStatus(status);

        if (status.status === 'completed') {
          // Build result URLs
          const urls: { plyUrl?: string; glbUrl?: string } = {};

          if (status.result?.files.ply) {
            urls.plyUrl = api.getDownloadUrl(jobId, status.result.files.ply);
          }
          if (status.result?.files.glb) {
            urls.glbUrl = api.getDownloadUrl(jobId, status.result.files.glb);
          }

          setResultUrls(urls);
          setState('result');
        }
      } catch (error) {
        console.error('Failed to poll job status:', error);
      }
    }, 2000); // Poll every 2 seconds

    return () => clearInterval(pollInterval);
  }, [jobId, jobStatus?.status]);

  const handleImageUploaded = useCallback((data: ImageData, file: File) => {
    setImageData(data);
    setImageFile(file);
    setState('mask');
  }, []);

  const handleMaskComplete = useCallback(
    async (maskBlob: Blob) => {
      if (!imageData) {
        console.error('No imageData available');
        return;
      }

      console.log('Uploading mask for image ID:', imageData.imageId);
      console.log('Mask blob size:', maskBlob.size, 'bytes');
      console.log('Mask blob type:', maskBlob.type);

      try {
        await api.uploadMask(imageData.imageId, maskBlob);
        setState('generate');
      } catch (error) {
        console.error('Failed to upload mask:', error);
        alert('Failed to upload mask. Please try again.');
      }
    },
    [imageData]
  );

  const handleGenerate = useCallback(
    async (options: GenerationOptions) => {
      if (!imageData) return;

      try {
        const response = await api.generate3D(imageData.imageId, options);
        setJobId(response.job_id);
        setJobStatus({
          jobId: response.job_id,
          status: 'pending',
          progress: 0,
          message: 'Job created',
        });
      } catch (error) {
        console.error('Failed to start generation:', error);
        alert('Failed to start generation. Please try again.');
      }
    },
    [imageData]
  );

  const handleReset = useCallback(() => {
    // Clean up job if exists
    if (jobId) {
      api.cleanupJob(jobId).catch(console.error);
    }

    setImageData(null);
    setImageFile(null);
    setJobId(null);
    setJobStatus(null);
    setResultUrls({});
    setState('upload');
  }, [jobId]);

  const handleBackToGenerate = useCallback(() => {
    setState('generate');
  }, []);

  return (
    <div className="min-h-screen w-full flex flex-col bg-dark-bg">
      {/* Header */}
      <header className="border-b border-dark-border bg-dark-surface">
        <div className="px-6 py-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <button
              onClick={handleReset}
              className="p-2 hover:bg-dark-elevated rounded-apple transition-colors"
              title="Back to home"
            >
              <Home className="w-5 h-5" />
            </button>
            <div>
              <h1 className="text-2xl font-bold">SAM 3D Objects</h1>
              <p className="text-sm text-dark-text-secondary">
                Create 3D models from 2D images
              </p>
            </div>
          </div>

          {/* Progress Steps */}
          <div className="flex items-center gap-2">
            {(['upload', 'mask', 'generate', 'result'] as const).map((step, index) => (
              <React.Fragment key={step}>
                <div
                  className={`
                    w-8 h-8 rounded-full flex items-center justify-center text-sm font-medium
                    transition-all duration-200
                    ${
                      state === step
                        ? 'bg-accent-primary text-white'
                        : index < ['upload', 'mask', 'generate', 'result'].indexOf(state)
                        ? 'bg-accent-primary/30 text-accent-primary'
                        : 'bg-dark-elevated text-dark-text-tertiary'
                    }
                  `}
                >
                  {index + 1}
                </div>
                {index < 3 && (
                  <div
                    className={`
                      w-12 h-0.5 transition-colors duration-200
                      ${
                        index < ['upload', 'mask', 'generate', 'result'].indexOf(state)
                          ? 'bg-accent-primary/30'
                          : 'bg-dark-border'
                      }
                    `}
                  />
                )}
              </React.Fragment>
            ))}
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="flex-1 overflow-hidden">
        {state === 'upload' && (
          <ImageUpload onImageUploaded={handleImageUploaded} />
        )}

        {state === 'mask' && imageFile && (
          <MaskDrawer
            imageFile={imageFile}
            onMaskComplete={handleMaskComplete}
            onBack={handleReset}
          />
        )}

        {state === 'generate' && (
          <div className="h-full flex items-center justify-center p-8">
            <div className="w-full max-w-2xl space-y-6">
              {jobStatus && <ProgressTracker jobStatus={jobStatus} />}

              <ControlPanel
                onGenerate={handleGenerate}
                isGenerating={
                  jobStatus?.status === 'processing' ||
                  jobStatus?.status === 'pending'
                }
              />

              {jobStatus?.status === 'failed' && (
                <div className="flex gap-2">
                  <button
                    className="btn-secondary flex-1"
                    onClick={handleBackToGenerate}
                  >
                    Try Again
                  </button>
                  <button className="btn-secondary flex-1" onClick={handleReset}>
                    Start Over
                  </button>
                </div>
              )}
            </div>
          </div>
        )}

        {state === 'result' && jobId && (
          <ResultViewer
            jobId={jobId}
            plyUrl={resultUrls.plyUrl}
            glbUrl={resultUrls.glbUrl}
            onReset={handleReset}
          />
        )}
      </main>

      {/* Footer */}
      <footer className="border-t border-dark-border bg-dark-surface px-6 py-3 text-center text-sm text-dark-text-tertiary">
        Powered by SAM 3D Objects • Built with React, Three.js, and FastAPI
      </footer>
    </div>
  );
}

export default App;
