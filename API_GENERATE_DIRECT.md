# API Documentation: `/api/generate-direct`

## Overview

The `/api/generate-direct` endpoint provides a unified, synchronous API for 3D model generation. It combines all 4 steps (upload-image, upload-mask, generate, download) into a single POST request that returns the GLB file directly as a binary blob.

This endpoint simplifies client integration by:
- Eliminating the need for polling-based status checks
- Reducing API calls from 4 to 1
- Providing immediate GLB output upon completion
- Handling all processing synchronously

## Endpoint Details

**URL:** `/api/generate-direct`
**Method:** `POST`
**Content-Type:** `multipart/form-data`
**Response Type:** `application/octet-stream` (binary GLB file)

## Request Schema

### Multipart Form Fields

| Field Name | Type | Required | Description |
|------------|------|----------|-------------|
| `image` | File | **Yes** | Source image file (PNG/JPEG format) |
| `mask` | File | **Yes** | Binary mask file (PNG grayscale format) |
| `seed` | Integer | No | Random seed for reproducibility (default: random) |
| `stage1_only` | Boolean | No | Only run stage 1 - **Must be false for GLB** (default: false) |
| `with_mesh_postprocess` | Boolean | No | Apply mesh post-processing (default: true) |
| `with_texture_baking` | Boolean | No | Bake textures onto mesh (default: true) |
| `with_layout_postprocess` | Boolean | No | Optimize layout (default: false) |

### Field Details

#### `image` (Required)
- **Format:** PNG or JPEG
- **Color Mode:** RGB or RGBA (will be converted if needed)
- **Description:** The source image containing the object to be reconstructed in 3D

#### `mask` (Required)
- **Format:** PNG
- **Color Mode:** Grayscale (L mode)
- **Description:** Binary mask indicating which pixels belong to the object
  - White/bright pixels (value > 127): Object region
  - Black/dark pixels (value ≤ 127): Background region
- **Note:** Mask will be automatically resized to match image dimensions if sizes differ

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

**Content-Type:** `application/octet-stream`
**Content-Disposition:** `attachment; filename="model.glb"`
**Body:** Binary GLB file data

The response is a binary stream containing the generated 3D model in GLB format. The file can be:
- Downloaded and saved locally
- Loaded directly into Three.js, Babylon.js, or other 3D libraries
- Imported into Blender, Unity, Unreal Engine, etc.

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

### cURL Example

```bash
curl -X POST http://localhost:8000/api/generate-direct \
  -F "image=@/path/to/image.png" \
  -F "mask=@/path/to/mask.png" \
  -F "seed=42" \
  -F "with_mesh_postprocess=true" \
  -F "with_texture_baking=true" \
  -F "with_layout_postprocess=false" \
  -o output.glb
```

### JavaScript/Fetch Example

```javascript
const formData = new FormData();
formData.append('image', imageFile); // File object from <input type="file">
formData.append('mask', maskFile);   // File object from <input type="file">
formData.append('seed', '42');
formData.append('with_mesh_postprocess', 'true');
formData.append('with_texture_baking', 'true');
formData.append('with_layout_postprocess', 'false');

const response = await fetch('http://localhost:8000/api/generate-direct', {
  method: 'POST',
  body: formData,
});

if (response.ok) {
  // Download the GLB file
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

### Python/Requests Example

```python
import requests

with open('image.png', 'rb') as img, open('mask.png', 'rb') as msk:
    files = {
        'image': ('image.png', img, 'image/png'),
        'mask': ('mask.png', msk, 'image/png'),
    }
    data = {
        'seed': 42,
        'with_mesh_postprocess': True,
        'with_texture_baking': True,
        'with_layout_postprocess': False,
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

## Processing Time

The endpoint processes synchronously, so response time depends on:
- Image resolution (higher = slower)
- GPU availability (GPU = faster)
- Generation options (more processing = slower)

**Typical processing times:**
- 512x512 image with GPU: ~10-30 seconds
- 1024x1024 image with GPU: ~30-60 seconds
- Without GPU: 2-5x slower

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
