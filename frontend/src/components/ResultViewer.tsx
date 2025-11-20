import React, { useState } from 'react';
import { Download, Eye } from 'lucide-react';
import { ModelViewer } from './ModelViewer';
import { api } from '../utils/api';

interface ResultViewerProps {
  jobId: string;
  plyUrl?: string;
  glbUrl?: string;
  onReset: () => void;
}

export const ResultViewer: React.FC<ResultViewerProps> = ({
  jobId,
  plyUrl,
  glbUrl,
  onReset,
}) => {
  const [viewMode, setViewMode] = useState<'ply' | 'glb'>(glbUrl ? 'glb' : 'ply');

  const handleDownload = (type: 'ply' | 'glb') => {
    const filename = type === 'ply' ? 'gaussian_splat.ply' : 'mesh.glb';
    const url = api.getDownloadUrl(jobId, filename);

    // Create a temporary link and click it
    const link = document.createElement('a');
    link.href = url;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  return (
    <div className="w-full h-full flex flex-col">
      {/* Toolbar */}
      <div className="card m-4 p-4 flex items-center justify-between flex-wrap gap-4">
        <div className="flex items-center gap-2">
          <Eye className="w-5 h-5 text-dark-text-secondary" />
          <span className="font-medium">3D Model Result</span>
        </div>

        <div className="flex items-center gap-2">
          {/* View Mode Toggle */}
          {plyUrl && glbUrl && (
            <div className="flex items-center gap-1 bg-dark-elevated rounded-apple p-1">
              <button
                className={`px-3 py-1 rounded-lg text-sm transition-colors ${
                  viewMode === 'ply'
                    ? 'bg-accent-primary text-white'
                    : 'text-dark-text-secondary hover:text-dark-text-primary'
                }`}
                onClick={() => setViewMode('ply')}
              >
                Gaussian Splat
              </button>
              <button
                className={`px-3 py-1 rounded-lg text-sm transition-colors ${
                  viewMode === 'glb'
                    ? 'bg-accent-primary text-white'
                    : 'text-dark-text-secondary hover:text-dark-text-primary'
                }`}
                onClick={() => setViewMode('glb')}
              >
                Mesh
              </button>
            </div>
          )}

          {/* Download Buttons */}
          {plyUrl && (
            <button
              className="btn-secondary"
              onClick={() => handleDownload('ply')}
            >
              <Download className="w-4 h-4 inline mr-2" />
              Download PLY
            </button>
          )}
          {glbUrl && (
            <button
              className="btn-secondary"
              onClick={() => handleDownload('glb')}
            >
              <Download className="w-4 h-4 inline mr-2" />
              Download GLB
            </button>
          )}

          <button className="btn-primary" onClick={onReset}>
            New Model
          </button>
        </div>
      </div>

      {/* 3D Viewer */}
      <div className="flex-1 px-4 pb-4">
        <ModelViewer
          plyUrl={plyUrl}
          glbUrl={glbUrl}
          modelType={viewMode}
        />
      </div>

      {/* Instructions */}
      <div className="card m-4 p-3 text-center text-dark-text-tertiary text-sm">
        Click and drag to rotate • Scroll to zoom • Right-click and drag to pan
      </div>
    </div>
  );
};
