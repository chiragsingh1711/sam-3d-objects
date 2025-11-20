import React, { useState } from 'react';
import { Settings, Sparkles } from 'lucide-react';
import { GenerationOptions } from '../types';

interface ControlPanelProps {
  onGenerate: (options: GenerationOptions) => void;
  isGenerating: boolean;
}

export const ControlPanel: React.FC<ControlPanelProps> = ({
  onGenerate,
  isGenerating,
}) => {
  const [seed, setSeed] = useState<string>('');
  const [stage1Only, setStage1Only] = useState(false);
  const [withMeshPostprocess, setWithMeshPostprocess] = useState(true);
  const [withTextureBaking, setWithTextureBaking] = useState(true);
  const [withLayoutPostprocess, setWithLayoutPostprocess] = useState(false);
  const [showAdvanced, setShowAdvanced] = useState(false);

  const handleGenerate = () => {
    const options: GenerationOptions = {
      seed: seed ? parseInt(seed) : undefined,
      stage1Only,
      withMeshPostprocess,
      withTextureBaking,
      withLayoutPostprocess,
    };
    onGenerate(options);
  };

  return (
    <div className="card p-6 space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-xl font-semibold flex items-center gap-2">
          <Settings className="w-5 h-5" />
          Generation Settings
        </h2>
        <button
          className="text-sm text-dark-text-secondary hover:text-dark-text-primary transition-colors"
          onClick={() => setShowAdvanced(!showAdvanced)}
        >
          {showAdvanced ? 'Hide' : 'Show'} Advanced
        </button>
      </div>

      {/* Seed Input */}
      <div>
        <label className="block text-sm font-medium mb-2 text-dark-text-secondary">
          Random Seed (optional)
        </label>
        <input
          type="number"
          value={seed}
          onChange={(e) => setSeed(e.target.value)}
          placeholder="Leave empty for random"
          className="input w-full"
          disabled={isGenerating}
        />
        <p className="text-xs text-dark-text-tertiary mt-1">
          Use the same seed to reproduce results
        </p>
      </div>

      {/* Advanced Options */}
      {showAdvanced && (
        <div className="space-y-4 pt-4 border-t border-dark-border">
          <h3 className="text-sm font-semibold text-dark-text-secondary uppercase">
            Advanced Options
          </h3>

          <label className="flex items-center gap-3 cursor-pointer">
            <input
              type="checkbox"
              checked={stage1Only}
              onChange={(e) => setStage1Only(e.target.checked)}
              className="w-5 h-5 rounded accent-accent-primary"
              disabled={isGenerating}
            />
            <div className="flex-1">
              <div className="text-sm font-medium">Stage 1 Only</div>
              <div className="text-xs text-dark-text-tertiary">
                Generate sparse structure only (faster)
              </div>
            </div>
          </label>

          <label className="flex items-center gap-3 cursor-pointer">
            <input
              type="checkbox"
              checked={withMeshPostprocess}
              onChange={(e) => setWithMeshPostprocess(e.target.checked)}
              className="w-5 h-5 rounded accent-accent-primary"
              disabled={isGenerating || stage1Only}
            />
            <div className="flex-1">
              <div className="text-sm font-medium">Mesh Post-processing</div>
              <div className="text-xs text-dark-text-tertiary">
                Apply mesh simplification and hole filling
              </div>
            </div>
          </label>

          <label className="flex items-center gap-3 cursor-pointer">
            <input
              type="checkbox"
              checked={withTextureBaking}
              onChange={(e) => setWithTextureBaking(e.target.checked)}
              className="w-5 h-5 rounded accent-accent-primary"
              disabled={isGenerating || stage1Only}
            />
            <div className="flex-1">
              <div className="text-sm font-medium">Texture Baking</div>
              <div className="text-xs text-dark-text-tertiary">
                Bake textures onto mesh (better quality)
              </div>
            </div>
          </label>

          <label className="flex items-center gap-3 cursor-pointer">
            <input
              type="checkbox"
              checked={withLayoutPostprocess}
              onChange={(e) => setWithLayoutPostprocess(e.target.checked)}
              className="w-5 h-5 rounded accent-accent-primary"
              disabled={isGenerating}
            />
            <div className="flex-1">
              <div className="text-sm font-medium">Layout Optimization</div>
              <div className="text-xs text-dark-text-tertiary">
                Optimize object pose and placement
              </div>
            </div>
          </label>
        </div>
      )}

      {/* Generate Button */}
      <button
        className="btn-primary w-full py-3 text-base font-semibold flex items-center justify-center gap-2"
        onClick={handleGenerate}
        disabled={isGenerating}
      >
        {isGenerating ? (
          <>
            <div className="animate-spin rounded-full h-5 w-5 border-2 border-white border-t-transparent" />
            Generating...
          </>
        ) : (
          <>
            <Sparkles className="w-5 h-5" />
            Generate 3D Model
          </>
        )}
      </button>
    </div>
  );
};
