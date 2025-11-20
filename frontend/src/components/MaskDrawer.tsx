import React, { useRef, useEffect, useState, useCallback } from 'react';
import { Paintbrush, Eraser, Trash2, Check } from 'lucide-react';
import { drawOnCanvas, canvasToBlob, clearCanvas } from '../utils/canvas';

interface MaskDrawerProps {
  imageFile: File;
  onMaskComplete: (maskBlob: Blob) => void;
  onBack: () => void;
}

export const MaskDrawer: React.FC<MaskDrawerProps> = ({
  imageFile,
  onMaskComplete,
  onBack,
}) => {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const imageRef = useRef<HTMLImageElement>(null);
  const [isDrawing, setIsDrawing] = useState(false);
  const [brushSize, setBrushSize] = useState(30);
  const [isErasing, setIsErasing] = useState(false);
  const [imageDimensions, setImageDimensions] = useState({ width: 0, height: 0 });

  useEffect(() => {
    const img = new Image();
    const url = URL.createObjectURL(imageFile);

    img.onload = () => {
      setImageDimensions({ width: img.width, height: img.height });

      if (canvasRef.current) {
        const canvas = canvasRef.current;
        canvas.width = img.width;
        canvas.height = img.height;
      }

      if (imageRef.current) {
        imageRef.current.src = url;
      }
    };

    img.src = url;

    return () => URL.revokeObjectURL(url);
  }, [imageFile]);

  const getCanvasCoordinates = useCallback((e: React.MouseEvent<HTMLCanvasElement>) => {
    const canvas = canvasRef.current;
    if (!canvas) return { x: 0, y: 0 };

    const rect = canvas.getBoundingClientRect();
    const scaleX = canvas.width / rect.width;
    const scaleY = canvas.height / rect.height;

    return {
      x: (e.clientX - rect.left) * scaleX,
      y: (e.clientY - rect.top) * scaleY,
    };
  }, []);

  const handleMouseDown = useCallback((e: React.MouseEvent<HTMLCanvasElement>) => {
    setIsDrawing(true);
    const { x, y } = getCanvasCoordinates(e);
    const ctx = canvasRef.current?.getContext('2d');
    if (ctx) {
      drawOnCanvas(ctx, x, y, brushSize, isErasing);
    }
  }, [getCanvasCoordinates, brushSize, isErasing]);

  const handleMouseMove = useCallback((e: React.MouseEvent<HTMLCanvasElement>) => {
    if (!isDrawing) return;

    const { x, y } = getCanvasCoordinates(e);
    const ctx = canvasRef.current?.getContext('2d');
    if (ctx) {
      drawOnCanvas(ctx, x, y, brushSize, isErasing);
    }
  }, [isDrawing, getCanvasCoordinates, brushSize, isErasing]);

  const handleMouseUp = useCallback(() => {
    setIsDrawing(false);
  }, []);

  const handleClear = useCallback(() => {
    const canvas = canvasRef.current;
    const ctx = canvas?.getContext('2d');
    if (ctx && canvas) {
      clearCanvas(ctx, canvas.width, canvas.height);
    }
  }, []);

  const handleComplete = useCallback(async () => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    try {
      const blob = await canvasToBlob(canvas);
      onMaskComplete(blob);
    } catch (error) {
      console.error('Failed to create mask:', error);
    }
  }, [onMaskComplete]);

  return (
    <div className="w-full h-full flex flex-col">
      {/* Toolbar */}
      <div className="card m-4 p-4 flex items-center gap-4 flex-wrap">
        <div className="flex items-center gap-2">
          <button
            className={`p-2 rounded-apple transition-colors ${
              !isErasing
                ? 'bg-accent-primary text-white'
                : 'bg-dark-elevated text-dark-text-secondary hover:bg-dark-border'
            }`}
            onClick={() => setIsErasing(false)}
          >
            <Paintbrush className="w-5 h-5" />
          </button>
          <button
            className={`p-2 rounded-apple transition-colors ${
              isErasing
                ? 'bg-accent-primary text-white'
                : 'bg-dark-elevated text-dark-text-secondary hover:bg-dark-border'
            }`}
            onClick={() => setIsErasing(true)}
          >
            <Eraser className="w-5 h-5" />
          </button>
        </div>

        <div className="flex items-center gap-2 flex-1">
          <label className="text-dark-text-secondary text-sm">Brush Size:</label>
          <input
            type="range"
            min="5"
            max="100"
            value={brushSize}
            onChange={(e) => setBrushSize(Number(e.target.value))}
            className="flex-1 max-w-xs"
          />
          <span className="text-dark-text-secondary text-sm w-12">{brushSize}px</span>
        </div>

        <div className="flex items-center gap-2">
          <button className="btn-secondary" onClick={handleClear}>
            <Trash2 className="w-5 h-5 inline mr-2" />
            Clear
          </button>
          <button className="btn-secondary" onClick={onBack}>
            Back
          </button>
          <button className="btn-primary" onClick={handleComplete}>
            <Check className="w-5 h-5 inline mr-2" />
            Continue
          </button>
        </div>
      </div>

      {/* Canvas Container */}
      <div className="flex-1 flex items-center justify-center p-4 overflow-auto">
        <div className="relative inline-block">
          <img
            ref={imageRef}
            alt="Original"
            className="max-w-full max-h-[calc(100vh-200px)] block"
          />
          <canvas
            ref={canvasRef}
            className="absolute top-0 left-0 cursor-crosshair max-w-full max-h-[calc(100vh-200px)]"
            style={{ width: '100%', height: '100%' }}
            onMouseDown={handleMouseDown}
            onMouseMove={handleMouseMove}
            onMouseUp={handleMouseUp}
            onMouseLeave={handleMouseUp}
          />
        </div>
      </div>

      <div className="card m-4 p-3 text-center text-dark-text-tertiary text-sm">
        Click and drag to paint the object you want to convert to 3D. Use the eraser to remove mistakes.
      </div>
    </div>
  );
};
