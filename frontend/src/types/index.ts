export interface ImageData {
  imageId: string;
  filename: string;
  size: {
    width: number;
    height: number;
  };
  mode: string;
  url?: string;
}

export interface MaskData {
  maskId: string;
  size: {
    width: number;
    height: number;
  };
}

export interface GenerationOptions {
  seed?: number;
  stage1Only: boolean;
  withMeshPostprocess: boolean;
  withTextureBaking: boolean;
  withLayoutPostprocess: boolean;
}

export interface JobStatus {
  jobId: string;
  status: 'pending' | 'processing' | 'completed' | 'failed';
  progress: number;
  message: string;
  result?: {
    jobId: string;
    files: {
      ply?: string;
      glb?: string;
    };
  };
  error?: string;
}

export interface GeneratedModel {
  jobId: string;
  plyUrl?: string;
  glbUrl?: string;
}
