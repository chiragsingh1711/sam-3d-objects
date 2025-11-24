# API Documentation: `/api/generate-direct`

## Overview

The `/api/generate-direct` endpoint provides a unified, synchronous API for 3D model generation with **multi-object support**. It combines all 4 steps (upload-image, upload-mask, generate, download) into a single POST request.

### Key Features
- **Single-object mode**: One mask → Returns single GLB file
- **Multi-object mode**: Multiple masks → Returns ZIP file with multiple GLBs + metadata
- Preserves correct spatial layout between objects
- Eliminates polling-based status checks
- Reduces API calls from 4 to 1
- Provides immediate output upon completion
- Synchronous processing

## Endpoint Details

**URL:** `/api/generate-direct`
**Method:** `POST`
**Content-Type:** `multipart/form-data`
**Response Type:**
- Single mask: `application/octet-stream` (GLB file)
- Multiple masks: `application/zip` (ZIP file containing GLBs + scene.json)

## Request Schema

### Multipart Form Fields

| Field Name | Type | Required | Description |
|------------|------|----------|-------------|
| `image` | File | **Yes** | Source image file (PNG/JPEG format) |
| `masks` | File[] | **Yes** | One or more binary mask files (PNG grayscale format) |
| `seed` | Integer | No | Random seed for reproducibility (default: random) |
| `stage1_only` | Boolean | No | Only run stage 1 - **Must be false for GLB** (default: false) |
| `with_mesh_postprocess` | Boolean | No | Apply mesh post-processing (default: true) |
| `with_texture_baking` | Boolean | No | Bake textures onto mesh (default: true) |
| `with_layout_postprocess` | Boolean | No | Optimize layout (default: false) |

### Field Details

#### `image` (Required)
- **Format:** PNG or JPEG
- **Color Mode:** RGB or RGBA (will be converted if needed)
- **Description:** The source image containing one or more objects to be reconstructed in 3D

#### `masks` (Required - Array)
- **Format:** PNG (one or more files)
- **Color Mode:** Grayscale (L mode)
- **Description:** Binary mask files, one per object. Each mask indicates which pixels belong to that specific object.
  - White/bright pixels (value > 127): Object region
  - Black/dark pixels (value ≤ 127): Background region
- **Multi-object support**: Upload multiple mask files to generate multiple 3D objects from the same image
- **Spatial layout**: Objects maintain their spatial relationships from the original image
- **Note:** Each mask will be automatically resized to match image dimensions if sizes differ

#### `seed` (Optional)
- **Type:** Integer
- **Default:** Random seed
- **Description:** Random seed for reproducible results. Use the same seed with the same inputs to get identical outputs.

#### `stage1_only` (Optional)
- **Type:** Boolean
- **Default:** `false`
- **Description:** If true, only runs stage 1 (Gaussian splatting). **Must be false for GLB output** as GLB requires stage 2 (mesh generation).
- **Error:** Returns HTTP 400 if set to true

#### `with_mesh_postprocess` (Optional)
- **Type:** Boolean
- **Default:** `true`
- **Description:** Enable mesh post-processing to improve mesh quality (smoothing, hole filling, etc.)

#### `with_texture_baking` (Optional)
- **Type:** Boolean
- **Default:** `true`
- **Description:** Bake textures onto the mesh for realistic appearance

#### `with_layout_postprocess` (Optional)
- **Type:** Boolean
- **Default:** `false`
- **Description:** Optimize mesh layout for better topology

## Response Schema

### Success Response (HTTP 200)

#### Single Mask Response

**Content-Type:** `application/octet-stream`
**Content-Disposition:** `attachment; filename="model.glb"`
**Body:** Binary GLB file data

When a single mask is provided, the response is a binary stream containing the generated 3D model in GLB format.

#### Multiple Masks Response

**Content-Type:** `application/zip`
**Content-Disposition:** `attachment; filename="scene.zip"`
**Body:** ZIP file containing:

1. **GLB files**: `object_0.glb`, `object_1.glb`, ..., `object_N.glb`
2. **Metadata**: `scene.json` with transformation data

**ZIP Contents Structure:**
```
scene.zip
├── object_0.glb          # 3D model for first mask
├── object_1.glb          # 3D model for second mask
├── object_N.glb          # 3D model for Nth mask
└── scene.json            # Scene metadata with transformations
```

**scene.json Format:**
```json
{
  "image_size": {
    "width": 1024,
    "height": 768
  },
  "num_objects": 3,
  "objects": [
    {
      "object_id": 0,
      "filename": "object_0.glb",
      "mask_filename": "mask_chair.png",
      "translation": [0.1, 0.0, -0.5],
      "rotation": [0.0, 0.0, 0.0, 1.0],
      "scale": [1.0, 1.0, 1.0]
    },
    {
      "object_id": 1,
      "filename": "object_1.glb",
      "mask_filename": "mask_table.png",
      "translation": [-0.3, 0.2, 0.1],
      "rotation": [0.0, 0.0, 0.0, 1.0],
      "scale": [1.2, 1.2, 1.2]
    }
  ]
}
```

**Metadata Fields:**
- `translation`: [x, y, z] - 3D position offset
- `rotation`: [x, y, z, w] - Quaternion rotation
- `scale`: [x, y, z] - Scale factors

These transformation matrices encode each object's position/orientation in the scene, allowing you to reconstruct the correct spatial layout in your 3D viewer.

**Usage:**
The GLB files and metadata can be:
- Downloaded and extracted locally
- Loaded into Three.js, Babylon.js with correct positioning
- Imported into Blender, Unity, Unreal Engine
- Each GLB can be positioned using the transformation data from scene.json

### Error Responses

#### HTTP 400 - Bad Request

**Scenario 1: Invalid file type**
```json
{
  "detail": "Image must be an image file"
}
```
or
```json
{
  "detail": "Mask must be an image file"
}
```

**Scenario 2: stage1_only is true**
```json
{
  "detail": "stage1_only=true is not supported for direct generation. GLB requires stage 2."
}
```

#### HTTP 500 - Internal Server Error

**Scenario 1: GLB generation failed**
```json
{
  "detail": "GLB generation failed - model did not produce GLB output"
}
```

**Scenario 2: Inference error**
```json
{
  "detail": "3D generation failed: <error message>"
}
```

## Example Usage

### Single Object (One Mask)

#### cURL Example

```bash
curl -X POST http://localhost:8000/api/generate-direct \
  -F "image=@/path/to/image.png" \
  -F "masks=@/path/to/mask.png" \
  -F "seed=42" \
  -F "with_mesh_postprocess=true" \
  -F "with_texture_baking=true" \
  -o output.glb
```

#### JavaScript/Fetch Example

```javascript
const formData = new FormData();
formData.append('image', imageFile);     // File object from <input type="file">
formData.append('masks', maskFile);       // Single mask file
formData.append('seed', '42');
formData.append('with_mesh_postprocess', 'true');
formData.append('with_texture_baking', 'true');

const response = await fetch('http://localhost:8000/api/generate-direct', {
  method: 'POST',
  body: formData,
});

if (response.ok) {
  const blob = await response.blob();
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = 'model.glb';
  a.click();
  URL.revokeObjectURL(url);
} else {
  const error = await response.json();
  console.error('Error:', error.detail);
}
```

#### Python/Requests Example

```python
import requests

with open('image.png', 'rb') as img, open('mask.png', 'rb') as msk:
    files = {
        'image': ('image.png', img, 'image/png'),
        'masks': ('mask.png', msk, 'image/png'),
    }
    data = {
        'seed': 42,
        'with_mesh_postprocess': True,
        'with_texture_baking': True,
    }

    response = requests.post(
        'http://localhost:8000/api/generate-direct',
        files=files,
        data=data
    )

    if response.status_code == 200:
        with open('output.glb', 'wb') as f:
            f.write(response.content)
        print('GLB file saved successfully')
    else:
        print('Error:', response.json())
```

### Multiple Objects (Multiple Masks)

#### cURL Example

```bash
# Upload same image with 3 different masks for 3 objects
curl -X POST http://localhost:8000/api/generate-direct \
  -F "image=@/path/to/room.png" \
  -F "masks=@/path/to/mask_chair.png" \
  -F "masks=@/path/to/mask_table.png" \
  -F "masks=@/path/to/mask_lamp.png" \
  -F "seed=42" \
  -F "with_mesh_postprocess=true" \
  -F "with_texture_baking=true" \
  -o scene.zip
```

#### JavaScript/Fetch Example

```javascript
// Upload one image + multiple masks
const formData = new FormData();
formData.append('image', imageFile);           // Single image file

// Append multiple mask files
const maskFiles = [maskFile1, maskFile2, maskFile3]; // From <input type="file" multiple>
maskFiles.forEach(maskFile => {
  formData.append('masks', maskFile);          // Append each mask with same key 'masks'
});

formData.append('seed', '42');
formData.append('with_mesh_postprocess', 'true');
formData.append('with_texture_baking', 'true');

const response = await fetch('http://localhost:8000/api/generate-direct', {
  method: 'POST',
  body: formData,
});

if (response.ok) {
  // Response will be a ZIP file
  const blob = await response.blob();
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = 'scene.zip';
  a.click();
  URL.revokeObjectURL(url);

  // To extract and use the files:
  // 1. Unzip on client side using JSZip library
  // 2. Read scene.json for transformation data
  // 3. Load each GLB file into Three.js with correct positioning
} else {
  const error = await response.json();
  console.error('Error:', error.detail);
}
```

#### Python/Requests Example

```python
import requests
import zipfile
import json
from io import BytesIO

# Open image and multiple mask files
with open('room.png', 'rb') as img:
    # Prepare files list with multiple masks
    files = [
        ('image', ('room.png', img, 'image/png')),
        ('masks', ('mask_chair.png', open('mask_chair.png', 'rb'), 'image/png')),
        ('masks', ('mask_table.png', open('mask_table.png', 'rb'), 'image/png')),
        ('masks', ('mask_lamp.png', open('mask_lamp.png', 'rb'), 'image/png')),
    ]

    data = {
        'seed': 42,
        'with_mesh_postprocess': True,
        'with_texture_baking': True,
    }

    response = requests.post(
        'http://localhost:8000/api/generate-direct',
        files=files,
        data=data
    )

    if response.status_code == 200:
        # Save ZIP file
        with open('scene.zip', 'wb') as f:
            f.write(response.content)
        print('Scene ZIP saved successfully')

        # Extract and read metadata
        with zipfile.ZipFile(BytesIO(response.content)) as z:
            # Read scene metadata
            with z.open('scene.json') as f:
                scene_metadata = json.load(f)
                print(f"Generated {scene_metadata['num_objects']} objects")

            # Extract each GLB file
            for obj in scene_metadata['objects']:
                filename = obj['filename']
                z.extract(filename, 'output/')
                print(f"Extracted {filename}")
                print(f"  Position: {obj.get('translation', 'N/A')}")
                print(f"  Rotation: {obj.get('rotation', 'N/A')}")
                print(f"  Scale: {obj.get('scale', 'N/A')}")
    else:
        print('Error:', response.json())
```

#### Three.js Integration Example

```javascript
import * as THREE from 'three';
import { GLTFLoader } from 'three/examples/jsm/loaders/GLTFLoader';
import JSZip from 'jszip';

// After receiving the ZIP response
const blob = await response.blob();
const zip = await JSZip.loadAsync(blob);

// Load scene metadata
const sceneJsonContent = await zip.file('scene.json').async('string');
const sceneData = JSON.parse(sceneJsonContent);

const loader = new GLTFLoader();
const scene = new THREE.Scene();

// Load each GLB with correct transformations
for (const obj of sceneData.objects) {
  // Get GLB file from ZIP
  const glbBlob = await zip.file(obj.filename).async('blob');
  const glbUrl = URL.createObjectURL(glbBlob);

  // Load GLB
  loader.load(glbUrl, (gltf) => {
    const model = gltf.scene;

    // Apply transformations from metadata
    if (obj.translation) {
      model.position.set(...obj.translation);
    }
    if (obj.rotation) {
      const [x, y, z, w] = obj.rotation;
      model.quaternion.set(x, y, z, w);
    }
    if (obj.scale) {
      model.scale.set(...obj.scale);
    }

    scene.add(model);
    console.log(`Loaded ${obj.filename} at position`, obj.translation);
  });

  URL.revokeObjectURL(glbUrl);
}
```

## Processing Time

**Note:** Processing time scales linearly with the number of masks. Each mask is processed sequentially.

The endpoint processes synchronously, so response time depends on:
- **Number of masks**: More masks = proportionally longer processing time
- **Image resolution**: Higher resolution = slower processing
- **GPU availability**: GPU = much faster (2-5x speedup)
- **Generation options**: More post-processing = slower

**Typical processing times per object:**
- 512x512 image with GPU: ~10-30 seconds
- 1024x1024 image with GPU: ~30-60 seconds
- Without GPU: 2-5x slower

**Multi-object examples:**
- 3 objects @ 512x512 with GPU: ~30-90 seconds (3× single object time)
- 5 objects @ 1024x1024 with GPU: ~150-300 seconds (5× single object time)

## Technical Details

### Image Processing Flow

1. **Validation:** Validate that both image and mask are valid image files
2. **Format Conversion:** Convert image to RGB/RGBA if needed
3. **Mask Processing:** Convert mask to grayscale (L mode) and resize to match image
4. **RGBA Combination:** Combine RGB image with mask as alpha channel
5. **Alpha Extraction:** Extract alpha channel as binary mask (threshold at 127)
6. **Normalization:** Normalize mask to float32 with values 0.0 or 1.0
7. **Inference:** Run SAM 3D model inference
8. **GLB Export:** Export generated mesh as GLB file
9. **Response:** Return GLB file as binary stream

### Mask Format

The mask should be a **grayscale PNG** where:
- **White pixels (255)** = Object (will be reconstructed)
- **Black pixels (0)** = Background (will be ignored)
- **Gray pixels** = Thresholded at 127 (>127 = object, ≤127 = background)

The mask is automatically:
- Converted to grayscale if not already
- Resized to match image dimensions using nearest-neighbor interpolation
- Combined with the image as the alpha channel
- Extracted and normalized to binary (0.0 or 1.0)

### Temporary Files

The endpoint creates temporary files during processing:
- Temporary directory: `uploads/temp/<uuid>/`
- Files: `image.png`, `mask.png`, `model.glb`
- **Note:** Temporary files are currently not automatically cleaned up due to FileResponse limitations. Consider implementing periodic cleanup or manual cleanup after download.

## Comparison with Multi-Step API

### Old Flow (4 API calls):
```
1. POST /api/upload-image    → Get imageId
2. POST /api/upload-mask     → Link mask to imageId
3. POST /api/generate        → Get jobId, poll status
4. GET  /api/download        → Download GLB when complete
```

### New Flow (1 API call):
```
1. POST /api/generate-direct → Get GLB immediately
```

**Benefits:**
- ✅ Simpler client code
- ✅ No polling required
- ✅ Faster overall (no round-trip delays)
- ✅ No job tracking needed

**Trade-offs:**
- ⚠️ Synchronous (client must wait for completion)
- ⚠️ No progress updates during generation
- ⚠️ Connection must remain open during processing

## Security Considerations

1. **File Size Limits:** Consider adding file size limits to prevent abuse
2. **Rate Limiting:** Implement rate limiting to prevent overload
3. **Timeout:** Consider adding request timeout for long-running requests
4. **CORS:** Ensure CORS is properly configured for your frontend domain
5. **Authentication:** Add authentication for production use

## Production Recommendations

1. **Add file size validation:**
   ```python
   MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
   if len(image_contents) > MAX_FILE_SIZE:
       raise HTTPException(400, "Image too large")
   ```

2. **Add timeout handling:**
   ```python
   import asyncio
   try:
       output = await asyncio.wait_for(
           asyncio.to_thread(inference, image=image_np, mask=mask_np, seed=seed),
           timeout=120  # 2 minutes
       )
   except asyncio.TimeoutError:
       raise HTTPException(500, "Generation timeout")
   ```

3. **Implement cleanup task:**
   - Use a background cron job to clean up old temp files
   - Or implement a cleanup queue

4. **Add monitoring:**
   - Track processing times
   - Monitor GPU usage
   - Log errors and failures

## Troubleshooting

### Issue: Request timeout
**Solution:** Increase server timeout or reduce image resolution

### Issue: Out of memory
**Solution:** Reduce image size or add memory limits

### Issue: GLB not generated
**Solution:** Ensure `stage1_only=false` and check backend logs

### Issue: Mask not working
**Solution:** Verify mask is grayscale PNG with white=object, black=background

### Issue: Temp files accumulating
**Solution:** Implement periodic cleanup script:
```bash
find uploads/temp -type d -mtime +1 -exec rm -rf {} +
```

## Backend Logs

Enable debug logging to see detailed processing information:
```
[DEBUG] generate-direct called
[DEBUG] Temp dir: uploads/temp/<uuid>
[DEBUG] Image saved: (1024, 1024)
[DEBUG] Mask saved: (1024, 1024)
[DEBUG] Loading inference model...
[DEBUG] Model loaded
[DEBUG] Converting RGB to RGBA with mask
[DEBUG] Extracted mask from alpha channel
[DEBUG] Image shape=(1024, 1024, 4), Mask shape=(1024, 1024)
[DEBUG] Mask unique values: [0. 1.]
[DEBUG] Mask pixels == 1: 262144
[DEBUG] Starting inference with seed=42
[DEBUG] Inference completed
[DEBUG] GLB saved: uploads/temp/<uuid>/model.glb
```

## Summary

The `/api/generate-direct` endpoint provides a streamlined, synchronous API for 3D model generation from image and mask inputs. It returns a GLB file directly, eliminating the need for complex polling logic and multiple API calls.

**Key Points:**
- Single POST request with multipart/form-data
- Returns binary GLB file directly
- Synchronous processing (no polling)
- Comprehensive error handling
- Suitable for both prototyping and production use (with added security measures)
