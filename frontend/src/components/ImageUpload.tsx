import React, { useCallback, useState } from 'react';
import { Upload, Image as ImageIcon } from 'lucide-react';
import { api } from '../utils/api';
import { ImageData } from '../types';

interface ImageUploadProps {
  onImageUploaded: (imageData: ImageData, file: File) => void;
}

export const ImageUpload: React.FC<ImageUploadProps> = ({ onImageUploaded }) => {
  const [isDragging, setIsDragging] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleFile = useCallback(async (file: File) => {
    if (!file.type.startsWith('image/')) {
      setError('Please upload an image file');
      return;
    }

    setIsUploading(true);
    setError(null);

    try {
      const imageData = await api.uploadImage(file);
      onImageUploaded(imageData, file);
    } catch (err) {
      setError('Failed to upload image. Please try again.');
      console.error(err);
    } finally {
      setIsUploading(false);
    }
  }, [onImageUploaded]);

  const handleDrop = useCallback((e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setIsDragging(false);

    const file = e.dataTransfer.files[0];
    if (file) {
      handleFile(file);
    }
  }, [handleFile]);

  const handleDragOver = useCallback((e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setIsDragging(true);
  }, []);

  const handleDragLeave = useCallback(() => {
    setIsDragging(false);
  }, []);

  const handleFileInput = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      handleFile(file);
    }
  }, [handleFile]);

  return (
    <div className="w-full h-full flex items-center justify-center p-8">
      <div
        className={`
          card w-full max-w-2xl p-12
          border-2 border-dashed
          transition-all duration-200
          ${isDragging ? 'border-accent-primary bg-dark-elevated' : 'border-dark-border'}
          ${isUploading ? 'opacity-50 pointer-events-none' : 'cursor-pointer hover:border-dark-text-tertiary'}
        `}
        onDrop={handleDrop}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onClick={() => document.getElementById('file-input')?.click()}
      >
        <input
          id="file-input"
          type="file"
          accept="image/*"
          className="hidden"
          onChange={handleFileInput}
          disabled={isUploading}
        />

        <div className="flex flex-col items-center gap-4 text-center">
          {isUploading ? (
            <>
              <div className="animate-spin rounded-full h-16 w-16 border-4 border-dark-border border-t-accent-primary" />
              <p className="text-dark-text-secondary">Uploading image...</p>
            </>
          ) : (
            <>
              <div className="p-4 bg-dark-elevated rounded-full">
                <Upload className="w-12 h-12 text-dark-text-secondary" />
              </div>
              <div>
                <h3 className="text-xl font-semibold mb-2">Upload an Image</h3>
                <p className="text-dark-text-secondary">
                  Drag and drop an image here, or click to browse
                </p>
                <p className="text-dark-text-tertiary text-sm mt-2">
                  Supports PNG and JPEG files
                </p>
              </div>
            </>
          )}

          {error && (
            <div className="mt-4 p-3 bg-red-500/10 border border-red-500/50 rounded-apple text-red-400 text-sm">
              {error}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
