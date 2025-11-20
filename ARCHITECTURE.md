# SAM 3D Objects - Web Application Architecture

## System Overview

The SAM 3D Objects web application consists of three main components:

```
┌─────────────────────────────────────────────────────────────┐
│                      Web Application                         │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌──────────────────┐         ┌──────────────────┐         │
│  │                  │         │                  │         │
│  │    Frontend      │◄───────►│    Backend       │         │
│  │   (React + TS)   │   HTTP  │   (FastAPI)      │         │
│  │                  │         │                  │         │
│  └──────────────────┘         └────────┬─────────┘         │
│         │                              │                    │
│         │                              ▼                    │
│         │                     ┌──────────────────┐         │
│         │                     │   SAM 3D Model   │         │
│         │                     │   (PyTorch)      │         │
│         │                     └──────────────────┘         │
│         │                                                   │
│         ▼                                                   │
│  ┌──────────────────┐                                      │
│  │    Three.js      │                                      │
│  │  (3D Rendering)  │                                      │
│  └──────────────────┘                                      │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

## Architecture Components

### 1. Frontend (React + TypeScript + Three.js)

**Technology Stack:**
- React 18.2 with TypeScript
- Vite for build tooling
- Tailwind CSS for styling
- Three.js for 3D rendering
- Axios for HTTP requests

**Responsibilities:**
- User interface and interaction
- Image upload and preview
- Interactive mask drawing
- 3D model visualization
- Progress tracking
- File downloads

**Key Features:**
- Server-side rendering ready
- Component-based architecture
- Type-safe development
- Responsive design
- Dark theme UI

### 2. Backend (FastAPI)

**Technology Stack:**
- FastAPI for REST API
- Uvicorn ASGI server
- Pydantic for validation
- Python 3.10+

**Responsibilities:**
- REST API endpoints
- File upload handling
- Job queue management
- Model inference orchestration
- File serving

**Key Features:**
- Async/await support
- Auto-generated API docs (OpenAPI)
- CORS support for frontend
- Background task processing
- File validation

### 3. Model Layer (SAM 3D Objects)

**Technology Stack:**
- PyTorch 2.5+
- CUDA for GPU acceleration
- Custom model architectures

**Responsibilities:**
- Image preprocessing
- Mask processing
- 3D generation (2 stages)
- Post-processing
- Export to PLY/GLB

**Key Features:**
- Two-stage pipeline
- Gaussian splat generation
- Mesh generation with textures
- Layout optimization
- Depth estimation

## Data Flow

### Image Upload Flow

```
User selects image
    ↓
Frontend validates file type
    ↓
POST /api/upload-image (multipart/form-data)
    ↓
Backend saves to uploads/{image_id}.png
    ↓
Returns {image_id, filename, size}
    ↓
Frontend displays image
```

### Mask Creation Flow

```
User draws mask on canvas
    ↓
Canvas → Blob conversion
    ↓
POST /api/upload-mask (image_id + mask blob)
    ↓
Backend saves to uploads/{image_id}_mask.png
    ↓
Returns {mask_id, size}
    ↓
Frontend proceeds to generation
```

### 3D Generation Flow

```
User clicks "Generate"
    ↓
POST /api/generate (with options)
    ↓
Backend creates job {job_id, status: 'pending'}
    ↓
Background task starts:
    1. Load inference model
    2. Load image + mask → RGBA
    3. Run stage 1 (sparse structure)
    4. Run stage 2 (detailed model)
    5. Save PLY (Gaussian splat)
    6. Save GLB (mesh)
    7. Update job status → 'completed'
    ↓
Frontend polls GET /api/job/{job_id} every 2s
    ↓
When status = 'completed':
    Frontend builds download URLs
    Displays 3D viewer
```

### Download Flow

```
User clicks "Download PLY/GLB"
    ↓
GET /api/download/{job_id}/{filename}
    ↓
Backend streams file
    ↓
Browser downloads file
```

## API Endpoints

### Image Management

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/upload-image` | POST | Upload source image |
| `/api/upload-mask` | POST | Upload object mask |

### Generation

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/generate` | POST | Start 3D generation job |
| `/api/job/{job_id}` | GET | Get job status and progress |

### File Access

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/download/{job_id}/{filename}` | GET | Download generated files |
| `/api/cleanup/{job_id}` | DELETE | Clean up job files |

### Utility

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/` | GET | API info |
| `/health` | GET | Health check |
| `/docs` | GET | Interactive API documentation |

## State Management

### Frontend State

```typescript
// Application state
type AppState = 'upload' | 'mask' | 'generate' | 'result';

// Image data
interface ImageData {
  imageId: string;
  filename: string;
  size: { width: number; height: number };
  mode: string;
}

// Job status
interface JobStatus {
  jobId: string;
  status: 'pending' | 'processing' | 'completed' | 'failed';
  progress: number; // 0.0 to 1.0
  message: string;
  result?: {
    jobId: string;
    files: { ply?: string; glb?: string };
  };
  error?: string;
}
```

### Backend State

```python
# In-memory job tracking
jobs: Dict[str, Dict[str, Any]] = {
    'job-uuid': {
        'status': 'processing',
        'progress': 0.5,
        'message': 'Running inference...',
        'created_at': '2024-01-...',
        'result': {...}  # Set when completed
    }
}
```

## File Storage Structure

```
project-root/
├── backend/
│   ├── uploads/              # Uploaded files
│   │   ├── {image_id}.png       # Original images
│   │   └── {image_id}_mask.png  # Mask files
│   └── outputs/              # Generated files
│       └── {job_id}/
│           ├── gaussian_splat.ply
│           └── mesh.glb
└── frontend/
    └── dist/                 # Built frontend files
```

## Security Considerations

### Current Implementation

1. **File Validation**: Only image files accepted
2. **CORS**: Restricted to specific origins
3. **File Size**: Implicit limits from web server
4. **Path Traversal**: UUID-based filenames prevent attacks

### Production Recommendations

1. **Authentication**: Add JWT or session-based auth
2. **Rate Limiting**: Prevent abuse
3. **File Size Limits**: Explicit max file size
4. **Input Sanitization**: Validate all user inputs
5. **HTTPS**: Use TLS in production
6. **Storage Quotas**: Limit per-user storage
7. **Temporary Files**: Auto-cleanup old jobs
8. **API Keys**: For programmatic access

## Performance Considerations

### Frontend Optimizations

1. **Code Splitting**: Vite automatically splits chunks
2. **Lazy Loading**: Components loaded on demand
3. **Image Optimization**: Canvas resizing for masks
4. **Polling**: Efficient 2s interval, stops when done
5. **Three.js**: Uses WebGL hardware acceleration

### Backend Optimizations

1. **Async I/O**: FastAPI async handlers
2. **Background Tasks**: Non-blocking job processing
3. **Model Caching**: Single inference instance
4. **GPU Acceleration**: CUDA for model inference
5. **File Streaming**: Efficient file downloads

### Scalability Considerations

For production scale:

1. **Job Queue**: Use Redis/Celery instead of in-memory
2. **Object Storage**: S3/GCS for files instead of local disk
3. **Load Balancing**: Multiple backend instances
4. **Database**: PostgreSQL for job metadata
5. **Caching**: Redis for frequently accessed data
6. **CDN**: CloudFront/CloudFlare for static assets
7. **WebSockets**: Replace polling with real-time updates

## Deployment Architecture

### Development

```
Frontend (Vite dev server): localhost:5173
Backend (Uvicorn): localhost:8000
```

### Production (Recommended)

```
┌─────────────────────────────────────────────┐
│              Load Balancer / CDN             │
│                  (CloudFlare)                │
└──────────────┬──────────────────────────────┘
               │
       ┌───────┴───────┐
       │               │
       ▼               ▼
┌─────────────┐ ┌─────────────┐
│   Nginx     │ │  API Server │
│  (Static)   │ │  (Gunicorn  │
│             │ │  + Uvicorn) │
└─────────────┘ └──────┬──────┘
                       │
                ┌──────┴──────┐
                │             │
                ▼             ▼
         ┌───────────┐ ┌───────────┐
         │  Worker 1 │ │  Worker N │
         │  (GPU)    │ │  (GPU)    │
         └───────────┘ └───────────┘
                │
                ▼
         ┌───────────┐
         │   Redis   │
         │ (Queue)   │
         └───────────┘
                │
                ▼
         ┌───────────┐
         │     S3    │
         │ (Storage) │
         └───────────┘
```

## Error Handling

### Frontend Error Handling

1. **Network Errors**: Retry with exponential backoff
2. **Validation Errors**: Show user-friendly messages
3. **API Errors**: Display error details from backend
4. **3D Loading Errors**: Fallback to error state
5. **Canvas Errors**: Graceful degradation

### Backend Error Handling

1. **File Upload Errors**: Validate and return 400
2. **Model Errors**: Catch and return 500 with details
3. **Job Not Found**: Return 404
4. **Invalid Input**: Return 400 with validation errors
5. **Server Errors**: Log and return 500

## Monitoring and Logging

### Recommended Monitoring

1. **Application Metrics**: Request rates, errors, latency
2. **GPU Metrics**: Utilization, memory, temperature
3. **Job Metrics**: Queue length, processing time, success rate
4. **Storage Metrics**: Disk usage, file counts
5. **User Metrics**: Active users, conversions, retention

### Logging Strategy

1. **Structured Logs**: JSON format
2. **Log Levels**: DEBUG, INFO, WARNING, ERROR
3. **Request Tracing**: Correlation IDs
4. **Error Tracking**: Sentry or similar
5. **Performance Profiling**: cProfile for bottlenecks

## Testing Strategy

### Frontend Testing

1. **Unit Tests**: Component logic (Jest)
2. **Integration Tests**: Component interactions
3. **E2E Tests**: Full user flows (Playwright)
4. **Visual Tests**: Screenshot comparison

### Backend Testing

1. **Unit Tests**: Endpoint logic (pytest)
2. **Integration Tests**: API + model integration
3. **Load Tests**: Stress testing (Locust)
4. **Model Tests**: Output validation

## Conclusion

This architecture provides:

- ✅ **Separation of Concerns**: Clear boundaries between layers
- ✅ **Scalability**: Can scale horizontally
- ✅ **Maintainability**: Modular, well-documented code
- ✅ **User Experience**: Fast, responsive, intuitive UI
- ✅ **Developer Experience**: Type-safe, well-tooled, documented

The current implementation is suitable for development and small-scale production. For large-scale production, implement the recommended scalability enhancements.
