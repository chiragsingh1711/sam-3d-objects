import axios from 'axios';
import { ImageData, MaskData, GenerationOptions, JobStatus } from '../types';

// Use environment variable for API URL, fallback to relative path for proxy
const API_BASE_URL = import.meta.env.VITE_API_URL
  ? `${import.meta.env.VITE_API_URL}/api`
  : '/api';

export const api = {
  // Upload image
  async uploadImage(file: File): Promise<ImageData> {
    const formData = new FormData();
    formData.append('file', file);

    const response = await axios.post<ImageData>(
      `${API_BASE_URL}/upload-image`,
      formData,
      {
        headers: { 'Content-Type': 'multipart/form-data' },
      }
    );

    return response.data;
  },

  // Upload mask
  async uploadMask(imageId: string, maskBlob: Blob): Promise<MaskData> {
    console.log('API uploadMask called with:');
    console.log('  - imageId:', imageId);
    console.log('  - maskBlob size:', maskBlob.size);
    console.log('  - API_BASE_URL:', API_BASE_URL);
    console.log('  - Full URL:', `${API_BASE_URL}/upload-mask`);

    const formData = new FormData();
    formData.append('image_id', imageId);
    formData.append('file', maskBlob, 'mask.png');

    console.log('FormData entries:');
    for (const [key, value] of formData.entries()) {
      console.log(`  - ${key}:`, value);
    }

    const response = await axios.post<MaskData>(
      `${API_BASE_URL}/upload-mask`,
      formData,
      {
        headers: { 'Content-Type': 'multipart/form-data' },
      }
    );

    return response.data;
  },

  // Generate 3D model
  async generate3D(
    imageId: string,
    options: GenerationOptions
  ): Promise<{ job_id: string }> {
    const formData = new FormData();
    formData.append('image_id', imageId);

    if (options.seed !== undefined) {
      formData.append('seed', options.seed.toString());
    }
    formData.append('stage1_only', options.stage1Only.toString());
    formData.append('with_mesh_postprocess', options.withMeshPostprocess.toString());
    formData.append('with_texture_baking', options.withTextureBaking.toString());
    formData.append('with_layout_postprocess', options.withLayoutPostprocess.toString());

    const response = await axios.post<{ job_id: string }>(
      `${API_BASE_URL}/generate`,
      formData,
      {
        headers: { 'Content-Type': 'multipart/form-data' },
      }
    );

    return response.data;
  },

  // Get job status
  async getJobStatus(jobId: string): Promise<JobStatus> {
    const response = await axios.get<JobStatus>(`${API_BASE_URL}/job/${jobId}`);
    return response.data;
  },

  // Get download URL
  getDownloadUrl(jobId: string, filename: string): string {
    return `${API_BASE_URL}/download/${jobId}/${filename}`;
  },

  // Cleanup job
  async cleanupJob(jobId: string): Promise<void> {
    await axios.delete(`${API_BASE_URL}/cleanup/${jobId}`);
  },
};
