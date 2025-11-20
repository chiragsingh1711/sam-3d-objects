# SAM 3D Objects - Frontend Documentation

## Overview

The SAM 3D Objects frontend is a modern, dark-themed web application built with React, TypeScript, and Three.js. It provides an intuitive interface for creating 3D models from 2D images.

## Tech Stack

### Core Framework
- **React 18.2**: UI framework
- **TypeScript**: Type-safe development
- **Vite**: Fast build tool and dev server

### 3D Visualization
- **Three.js**: 3D rendering engine
- **@react-three/fiber**: React renderer for Three.js
- **@react-three/drei**: Useful helpers for React Three Fiber

### Styling
- **Tailwind CSS**: Utility-first CSS framework
- **Custom Dark Theme**: Apple-inspired design system

### API Communication
- **Axios**: HTTP client for API requests

## Project Structure

```
frontend/
├── src/
│   ├── components/          # React components
│   │   ├── ImageUpload.tsx      # Image upload component
│   │   ├── MaskDrawer.tsx       # Interactive mask drawing
│   │   ├── ModelViewer.tsx      # 3D model viewer (Three.js)
│   │   ├── ControlPanel.tsx     # Generation settings panel
│   │   ├── ProgressTracker.tsx  # Job progress display
│   │   ├── ResultViewer.tsx     # Result display and downloads
│   │   └── index.ts             # Component exports
│   ├── utils/               # Utility functions
│   │   ├── api.ts              # API client
│   │   └── canvas.ts           # Canvas drawing utilities
│   ├── types/               # TypeScript type definitions
│   │   └── index.ts
│   ├── App.tsx              # Main application component
│   ├── main.tsx             # Application entry point
│   └── index.css            # Global styles
├── public/                  # Static assets
├── index.html              # HTML template
├── package.json            # Dependencies and scripts
├── vite.config.ts          # Vite configuration
├── tailwind.config.js      # Tailwind CSS configuration
└── tsconfig.json           # TypeScript configuration
```

## Design System

### Color Palette (Dark Theme)

```css
Background Colors:
- bg: #000000 (pure black)
- surface: #1c1c1e (elevated surface)
- elevated: #2c2c2e (more elevated)
- border: #38383a (borders and dividers)

Text Colors:
- primary: #ffffff (main text)
- secondary: #98989d (secondary text)
- tertiary: #636366 (tertiary/disabled text)

Accent Colors:
- primary: #007aff (iOS blue)
- hover: #0051d5 (darker blue on hover)
```

### Typography

- Font Family: -apple-system, BlinkMacSystemFont, SF Pro Display, Segoe UI
- Minimalist, clean typography following Apple's design language

### Components

#### Button Styles
- **Primary**: Blue background, white text
- **Secondary**: Dark elevated background, light text
- Rounded corners (10px)
- Smooth transitions

#### Cards
- Dark surface background
- Subtle borders
- Rounded corners

#### Inputs
- Dark elevated background
- Focus ring with accent color
- Clear placeholder text

## Application Flow

### State Management

The app uses React's built-in state management with hooks:

1. **AppState**: Tracks current step
   - `upload`: Initial image upload
   - `mask`: Mask drawing
   - `generate`: Settings and generation
   - `result`: View and download results

2. **Image Data**: Stores uploaded image info
3. **Job Status**: Tracks generation progress
4. **Result URLs**: Stores URLs for generated models

### User Journey

```
1. Upload Image
   ↓
2. Draw Mask (paint object to reconstruct)
   ↓
3. Configure Settings (seed, post-processing options)
   ↓
4. Generate 3D Model (progress tracking)
   ↓
5. View & Download (PLY/GLB formats)
```

## Components Reference

### ImageUpload

Handles image file upload via drag-and-drop or file picker.

**Props:**
- `onImageUploaded`: Callback when image is uploaded

**Features:**
- Drag and drop support
- File validation
- Upload progress
- Error handling

### MaskDrawer

Interactive canvas for drawing object masks.

**Props:**
- `imageFile`: The uploaded image file
- `onMaskComplete`: Callback when mask is complete
- `onBack`: Callback to go back

**Features:**
- Brush/eraser tools
- Adjustable brush size
- Clear functionality
- Canvas overlay on image

### ModelViewer

Three.js-based 3D model viewer.

**Props:**
- `plyUrl`: URL to PLY file
- `glbUrl`: URL to GLB file
- `modelType`: Which format to display

**Features:**
- Orbit controls (rotate, zoom, pan)
- Environment lighting
- Support for both PLY (Gaussian splats) and GLB (meshes)
- Grid helper for reference

### ControlPanel

Settings panel for 3D generation.

**Props:**
- `onGenerate`: Callback to start generation
- `isGenerating`: Whether generation is in progress

**Features:**
- Seed input for reproducibility
- Advanced options (collapsible)
- Stage selection
- Post-processing toggles

### ProgressTracker

Displays job status and progress.

**Props:**
- `jobStatus`: Current job status object

**Features:**
- Progress bar
- Status icons
- Error messages
- Real-time updates

### ResultViewer

Displays generated models with download options.

**Props:**
- `jobId`: Job identifier
- `plyUrl`: URL to PLY file
- `glbUrl`: URL to GLB file
- `onReset`: Callback to start over

**Features:**
- View mode toggle (PLY/GLB)
- Download buttons
- 3D viewer integration

## API Integration

### Endpoints

All API calls are made through the `api` utility:

```typescript
// Upload image
api.uploadImage(file: File): Promise<ImageData>

// Upload mask
api.uploadMask(imageId: string, maskBlob: Blob): Promise<MaskData>

// Generate 3D model
api.generate3D(imageId: string, options: GenerationOptions): Promise<{job_id: string}>

// Get job status
api.getJobStatus(jobId: string): Promise<JobStatus>

// Get download URL
api.getDownloadUrl(jobId: string, filename: string): string

// Cleanup job
api.cleanupJob(jobId: string): Promise<void>
```

### Polling

The app polls the job status endpoint every 2 seconds while a job is processing to provide real-time progress updates.

## Canvas Utilities

The `canvas.ts` utility provides functions for mask drawing:

- `drawOnCanvas()`: Draw or erase on canvas
- `canvasToBlob()`: Convert canvas to blob
- `clearCanvas()`: Clear canvas contents

## Development

### Running Locally

```bash
# Install dependencies
npm install

# Start dev server
npm run dev

# Build for production
npm run build

# Preview production build
npm run preview
```

### Environment

The dev server runs on `http://localhost:5173` and proxies API requests to `http://localhost:8000`.

### Linting

```bash
npm run lint
```

## Performance Considerations

1. **Lazy Loading**: Components are loaded as needed
2. **Three.js Optimization**: Suspense boundaries for 3D models
3. **Polling Optimization**: Stops when job completes
4. **Image Optimization**: Canvas resizing for masks

## Browser Support

- Modern browsers with ES2020 support
- WebGL required for 3D visualization
- Recommended: Chrome, Firefox, Safari, Edge (latest versions)

## Future Enhancements

Potential improvements:
- WebSocket support for real-time updates (vs polling)
- Multi-object support in UI
- Camera capture for mobile
- Advanced mask editing (SAM integration)
- Export to additional formats
- Batch processing
- Model comparison view
- AR preview
- Cloud storage integration

## Troubleshooting

### Common Issues

**3D model not loading:**
- Check browser console for errors
- Ensure WebGL is enabled
- Verify file URLs are accessible

**API errors:**
- Ensure backend server is running
- Check network tab for failed requests
- Verify CORS configuration

**Canvas not working:**
- Check browser permissions
- Ensure image is loaded before drawing
- Verify canvas dimensions match image

## Contributing

When contributing to the frontend:

1. Follow TypeScript best practices
2. Maintain the dark theme design system
3. Add types for all new interfaces
4. Test on multiple browsers
5. Keep components small and focused
6. Document complex logic
7. Use the existing utility functions

## License

See main project LICENSE file.
