"""
SAM 3D Objects - FastAPI Backend Server
Provides REST API for 3D object generation from images
"""

import os
import sys
import asyncio
import uuid
import shutil
import argparse
import json
import zipfile
from pathlib import Path
from typing import Optional, Dict, Any, List
from datetime import datetime

from fastapi import FastAPI, File, UploadFile, HTTPException, BackgroundTasks, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel, Field
import numpy as np
from PIL import Image
import io

# Add parent directory to path to import sam3d_objects
sys.path.insert(0, str(Path(__file__).parent.parent))

# Import inference module (lazy loading to avoid CUDA initialization on import)
inference_module = None
Inference = None

app = FastAPI(
    title="SAM 3D Objects API",
    description="Generate 3D models from 2D images using Segment Anything Model",
    version="1.0.0"
)

# CORS middleware for React frontend
# For production, replace "*" with specific domains
# Example: ["https://your-domain.com", "http://your-gcp-ip:5173"]
allowed_origins = os.environ.get("ALLOWED_ORIGINS", "*")
if allowed_origins == "*":
    origins = ["*"]
else:
    origins = [origin.strip() for origin in allowed_origins.split(",")]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Storage directories
UPLOAD_DIR = Path("backend/uploads")
OUTPUT_DIR = Path("backend/outputs")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Job tracking
jobs: Dict[str, Dict[str, Any]] = {}

# Global inference instance (lazy loaded)
inference_instance = None


class GenerationRequest(BaseModel):
    """Request model for 3D generation"""
    seed: Optional[int] = Field(None, description="Random seed for reproducibility")
    stage1_only: bool = Field(False, description="Only run stage 1 (sparse structure)")
    with_mesh_postprocess: bool = Field(True, description="Apply mesh post-processing")
    with_texture_baking: bool = Field(True, description="Bake textures onto mesh")
    with_layout_postprocess: bool = Field(False, description="Optimize layout/pose")


class JobStatus(BaseModel):
    """Job status response"""
    jobId: str = Field(..., alias="job_id")  # Use camelCase for frontend
    status: str  # pending, processing, completed, failed
    progress: float  # 0.0 to 1.0
    message: str
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None

    class Config:
        populate_by_name = True


def get_inference_instance():
    """Lazy load inference instance"""
    global inference_instance, Inference, inference_module

    if inference_instance is None:
        print(f"[DEBUG] Initializing inference instance for the first time")

        # Import inference module
        notebook_path = Path(__file__).parent.parent / "notebook"
        print(f"[DEBUG] Adding notebook path to sys.path: {notebook_path}")
        sys.path.insert(0, str(notebook_path))

        print(f"[DEBUG] Importing inference module...")
        try:
            import inference as inference_module
            Inference = inference_module.Inference
            print(f"[DEBUG] Inference module imported successfully")
        except Exception as e:
            print(f"[ERROR] Failed to import inference module: {e}")
            import traceback
            traceback.print_exc()
            raise

        # Load model
        config_path = Path(__file__).parent.parent / "checkpoints" / "hf" / "pipeline.yaml"
        print(f"[DEBUG] Config path: {config_path}")
        print(f"[DEBUG] Config exists: {config_path.exists()}")

        if not config_path.exists():
            raise FileNotFoundError(
                f"Config file not found at {config_path}. "
                "Please download model weights from HuggingFace first."
            )

        print(f"[DEBUG] Creating Inference instance with config: {config_path}")
        try:
            inference_instance = Inference(str(config_path), compile=False)
            print(f"[DEBUG] Inference instance created successfully")
        except Exception as e:
            print(f"[ERROR] Failed to create Inference instance: {e}")
            import traceback
            traceback.print_exc()
            raise
    else:
        print(f"[DEBUG] Reusing existing inference instance")

    return inference_instance


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "SAM 3D Objects API",
        "version": "1.0.0",
        "docs": "/docs"
    }


@app.get("/health")
async def health():
    """Health check endpoint"""
    return {"status": "healthy"}


@app.post("/api/upload-image")
async def upload_image(file: UploadFile = File(...)):
    """
    Upload an image for 3D generation

    Returns:
        - image_id: Unique identifier for the uploaded image
        - filename: Original filename
        - size: Image dimensions
    """
    # Validate file type
    if not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="File must be an image")

    # Read image
    contents = await file.read()
    try:
        image = Image.open(io.BytesIO(contents))

        # Convert to RGB if necessary
        if image.mode not in ("RGB", "RGBA"):
            image = image.convert("RGB")

        # Generate unique ID
        image_id = str(uuid.uuid4())

        # Save image
        image_path = UPLOAD_DIR / f"{image_id}.png"
        image.save(image_path, "PNG")

        return {
            "imageId": image_id,  # Use camelCase for frontend compatibility
            "filename": file.filename,
            "size": {"width": image.width, "height": image.height},
            "mode": image.mode
        }

    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid image file: {str(e)}")


@app.post("/api/upload-mask")
async def upload_mask(
    image_id: str = Form(...),
    file: UploadFile = File(...)
):
    """
    Upload a mask for an image

    Args:
        image_id: ID of the uploaded image
        file: Binary mask image

    Returns:
        - mask_id: Unique identifier for the mask
    """
    print(f"[DEBUG] upload_mask called with image_id: {image_id}")
    print(f"[DEBUG] Uploaded file: {file.filename}, content_type: {file.content_type}")
    print(f"[DEBUG] UPLOAD_DIR: {UPLOAD_DIR}")
    print(f"[DEBUG] UPLOAD_DIR absolute: {UPLOAD_DIR.absolute()}")

    # Check if image exists
    image_path = UPLOAD_DIR / f"{image_id}.png"
    print(f"[DEBUG] Looking for image at: {image_path}")
    print(f"[DEBUG] Image exists: {image_path.exists()}")

    if not image_path.exists():
        print(f"[DEBUG] Listing files in UPLOAD_DIR:")
        if UPLOAD_DIR.exists():
            for f in UPLOAD_DIR.iterdir():
                print(f"[DEBUG]   - {f.name}")
        else:
            print(f"[DEBUG] UPLOAD_DIR does not exist!")
        raise HTTPException(status_code=404, detail=f"Image not found: {image_id}")

    # Read mask
    contents = await file.read()
    try:
        mask = Image.open(io.BytesIO(contents))

        # Convert to L (grayscale)
        if mask.mode != "L":
            mask = mask.convert("L")

        # Ensure mask matches image size
        image = Image.open(image_path)
        if mask.size != image.size:
            mask = mask.resize(image.size, Image.Resampling.NEAREST)

        # Save mask
        mask_path = UPLOAD_DIR / f"{image_id}_mask.png"
        mask.save(mask_path, "PNG")

        return {
            "maskId": image_id,  # Use camelCase for frontend compatibility
            "size": {"width": mask.width, "height": mask.height}
        }

    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid mask file: {str(e)}")


@app.post("/api/generate")
async def generate_3d(
    background_tasks: BackgroundTasks,
    image_id: str = Form(...),
    seed: Optional[int] = Form(None),
    stage1_only: bool = Form(False),
    with_mesh_postprocess: bool = Form(True),
    with_texture_baking: bool = Form(True),
    with_layout_postprocess: bool = Form(False)
):
    """
    Generate 3D model from image and mask

    Args:
        image_id: ID of uploaded image
        seed: Random seed for reproducibility
        stage1_only: Only run stage 1
        with_mesh_postprocess: Apply mesh post-processing
        with_texture_baking: Bake textures
        with_layout_postprocess: Optimize layout

    Returns:
        - job_id: Unique job identifier
    """
    # Check if image and mask exist
    image_path = UPLOAD_DIR / f"{image_id}.png"
    mask_path = UPLOAD_DIR / f"{image_id}_mask.png"

    if not image_path.exists():
        raise HTTPException(status_code=404, detail="Image not found")
    if not mask_path.exists():
        raise HTTPException(status_code=404, detail="Mask not found")

    # Create job
    job_id = str(uuid.uuid4())
    jobs[job_id] = {
        "status": "pending",
        "progress": 0.0,
        "message": "Job created",
        "created_at": datetime.now().isoformat()
    }

    # Start background task
    background_tasks.add_task(
        process_generation,
        job_id=job_id,
        image_path=image_path,
        mask_path=mask_path,
        seed=seed,
        stage1_only=stage1_only,
        with_mesh_postprocess=with_mesh_postprocess,
        with_texture_baking=with_texture_baking,
        with_layout_postprocess=with_layout_postprocess
    )

    return {"jobId": job_id}  # Use camelCase for frontend compatibility


@app.post("/api/generate-direct")
async def generate_direct(
    image: UploadFile = File(...),
    masks: List[UploadFile] = File(...),
    seed: Optional[int] = Form(None),
    stage1_only: bool = Form(False),
    with_mesh_postprocess: bool = Form(True),
    with_texture_baking: bool = Form(True),
    with_layout_postprocess: bool = Form(False)
):
    """
    Generate 3D models directly from image and multiple mask files.

    This endpoint supports multi-object 3D generation. Upload one image and multiple masks
    (one per object). Returns a ZIP file containing multiple GLB files with correct spatial layout.

    Args:
        image: Source image file (PNG/JPEG)
        masks: List of binary mask files (PNG grayscale), one per object
        seed: Random seed for reproducibility (optional)
        stage1_only: Only run stage 1 (returns error, GLB needs stage 2)
        with_mesh_postprocess: Apply mesh post-processing
        with_texture_baking: Bake textures
        with_layout_postprocess: Optimize layout

    Returns:
        If single mask: GLB file as binary stream
        If multiple masks: ZIP file containing multiple GLBs + scene.json metadata
    """
    temp_dir = None

    try:
        print(f"[DEBUG] generate-direct called with {len(masks)} mask(s)")

        # Validate files
        if not image.content_type.startswith("image/"):
            raise HTTPException(status_code=400, detail="Image must be an image file")

        for idx, mask in enumerate(masks):
            if not mask.content_type.startswith("image/"):
                raise HTTPException(status_code=400, detail=f"Mask {idx} must be an image file")

        if len(masks) == 0:
            raise HTTPException(status_code=400, detail="At least one mask is required")

        if stage1_only:
            raise HTTPException(
                status_code=400,
                detail="stage1_only=true is not supported for direct generation. GLB requires stage 2."
            )

        # Create temporary directory for this request
        temp_id = str(uuid.uuid4())
        temp_dir = UPLOAD_DIR / "temp" / temp_id
        temp_dir.mkdir(parents=True, exist_ok=True)

        print(f"[DEBUG] Temp dir: {temp_dir}")

        # Save uploaded image
        temp_image_path = temp_dir / "image.png"
        image_contents = await image.read()
        image_pil = Image.open(io.BytesIO(image_contents))
        if image_pil.mode not in ("RGB", "RGBA"):
            image_pil = image_pil.convert("RGB")
        image_pil.save(temp_image_path, "PNG")
        print(f"[DEBUG] Image saved: {image_pil.size}")

        # Load inference model once
        print(f"[DEBUG] Loading inference model...")
        inference = get_inference_instance()
        print(f"[DEBUG] Model loaded")

        # Process each mask and run inference
        outputs = []
        scene_metadata = {
            "image_size": {"width": image_pil.size[0], "height": image_pil.size[1]},
            "num_objects": len(masks),
            "objects": []
        }

        for idx, mask_file in enumerate(masks):
            print(f"[DEBUG] Processing mask {idx + 1}/{len(masks)}")

            # Save mask
            temp_mask_path = temp_dir / f"mask_{idx}.png"
            mask_contents = await mask_file.read()
            mask_pil = Image.open(io.BytesIO(mask_contents))
            if mask_pil.mode != "L":
                mask_pil = mask_pil.convert("L")
            if mask_pil.size != image_pil.size:
                mask_pil = mask_pil.resize(image_pil.size, Image.Resampling.NEAREST)
            mask_pil.save(temp_mask_path, "PNG")
            print(f"[DEBUG] Mask {idx} saved: {mask_pil.size}")

            # Load images
            image_loaded = Image.open(temp_image_path)
            mask_loaded = Image.open(temp_mask_path)

            # Combine image and mask into RGBA
            if image_loaded.mode == "RGB":
                print(f"[DEBUG] Converting RGB to RGBA with mask {idx}")
                image_array = np.array(image_loaded)
                mask_array = np.array(mask_loaded)

                # Create RGBA image
                rgba = np.zeros((image_array.shape[0], image_array.shape[1], 4), dtype=np.uint8)
                rgba[:, :, :3] = image_array
                rgba[:, :, 3] = mask_array

                combined_image = Image.fromarray(rgba, "RGBA")
            else:
                combined_image = image_loaded

            # Convert to numpy arrays
            image_np = np.array(combined_image)

            # Extract mask from alpha channel
            if image_np.shape[2] == 4:  # RGBA
                mask_np = image_np[:, :, 3]
                print(f"[DEBUG] Extracted mask {idx} from alpha channel")
            else:
                mask_np = np.array(mask_loaded)
                print(f"[DEBUG] Using separate mask file {idx}")

            print(f"[DEBUG] Mask {idx}: shape={mask_np.shape}, unique values={np.unique(mask_np)}")

            # Normalize mask to binary (0 or 1)
            mask_np = (mask_np > 127).astype(np.float32)
            print(f"[DEBUG] Mask {idx}: pixels == 1: {np.sum(mask_np == 1)}")

            if np.sum(mask_np == 1) == 0:
                print(f"[WARNING] Mask {idx} has no valid pixels, skipping")
                continue

            # Run inference
            print(f"[DEBUG] Starting inference for mask {idx} with seed={seed}")
            output = inference(
                image=image_np,
                mask=mask_np,
                seed=seed
            )
            print(f"[DEBUG] Inference completed for mask {idx}")

            # Check GLB generation
            if "glb" not in output or output["glb"] is None:
                print(f"[WARNING] GLB generation failed for mask {idx}, skipping")
                continue

            # Save GLB
            temp_glb_path = temp_dir / f"object_{idx}.glb"
            output["glb"].export(str(temp_glb_path))
            print(f"[DEBUG] GLB {idx} saved: {temp_glb_path}")

            # Extract transformation metadata if available
            metadata = {
                "object_id": idx,
                "filename": f"object_{idx}.glb",
                "mask_filename": mask_file.filename
            }

            # Add transformation data if available in output
            if "translation" in output:
                translation = output["translation"]
                if hasattr(translation, "cpu"):
                    translation = translation.cpu().numpy()
                metadata["translation"] = translation.tolist()

            if "rotation" in output:
                rotation = output["rotation"]
                if hasattr(rotation, "cpu"):
                    rotation = rotation.cpu().numpy()
                metadata["rotation"] = rotation.tolist()

            if "scale" in output:
                scale = output["scale"]
                if hasattr(scale, "cpu"):
                    scale = scale.cpu().numpy()
                metadata["scale"] = scale.tolist()

            outputs.append({
                "glb_path": temp_glb_path,
                "metadata": metadata
            })
            scene_metadata["objects"].append(metadata)

        if len(outputs) == 0:
            raise HTTPException(
                status_code=500,
                detail="No valid 3D models generated from provided masks"
            )

        # If single object, return just the GLB file
        if len(outputs) == 1:
            print(f"[DEBUG] Returning single GLB file")
            return FileResponse(
                path=outputs[0]["glb_path"],
                media_type="application/octet-stream",
                filename="model.glb"
            )

        # Multiple objects: Create ZIP file
        print(f"[DEBUG] Creating ZIP with {len(outputs)} objects")
        zip_path = temp_dir / "scene.zip"

        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            # Add all GLB files
            for output in outputs:
                glb_path = output["glb_path"]
                zipf.write(glb_path, glb_path.name)

            # Add scene metadata JSON
            metadata_json = json.dumps(scene_metadata, indent=2)
            zipf.writestr("scene.json", metadata_json)

        print(f"[DEBUG] ZIP file created: {zip_path}")

        # Return ZIP file
        return FileResponse(
            path=zip_path,
            media_type="application/zip",
            filename="scene.zip"
        )

    except HTTPException:
        # Re-raise HTTP exceptions
        if temp_dir and temp_dir.exists():
            shutil.rmtree(temp_dir)
        raise
    except Exception as e:
        # Cleanup on error
        if temp_dir and temp_dir.exists():
            shutil.rmtree(temp_dir)

        print(f"[ERROR] generate-direct failed")
        print(f"[ERROR] Exception type: {type(e).__name__}")
        print(f"[ERROR] Exception message: {str(e)}")
        import traceback
        traceback.print_exc()

        raise HTTPException(
            status_code=500,
            detail=f"3D generation failed: {str(e)}"
        )


def cleanup_temp_dir(temp_dir: Path):
    """Background cleanup task for temporary directories"""
    try:
        if temp_dir.exists():
            shutil.rmtree(temp_dir)
            print(f"[DEBUG] Cleaned up temp dir: {temp_dir}")
    except Exception as e:
        print(f"[ERROR] Failed to cleanup temp dir {temp_dir}: {e}")


async def process_generation(
    job_id: str,
    image_path: Path,
    mask_path: Path,
    seed: Optional[int],
    stage1_only: bool,
    with_mesh_postprocess: bool,
    with_texture_baking: bool,
    with_layout_postprocess: bool
):
    """Background task for 3D generation"""
    try:
        print(f"[DEBUG] Starting generation for job {job_id}")

        # Update status
        jobs[job_id]["status"] = "processing"
        jobs[job_id]["progress"] = 0.1
        jobs[job_id]["message"] = "Loading models..."
        print(f"[DEBUG] Status updated to processing")

        # Get inference instance
        print(f"[DEBUG] About to call get_inference_instance()")
        inference = get_inference_instance()
        print(f"[DEBUG] Inference instance loaded successfully")

        jobs[job_id]["progress"] = 0.2
        jobs[job_id]["message"] = "Loading image and mask..."
        print(f"[DEBUG] Loading images from:")
        print(f"[DEBUG]   - image_path: {image_path}")
        print(f"[DEBUG]   - mask_path: {mask_path}")

        # Load image and mask
        image = Image.open(image_path)
        mask = Image.open(mask_path)
        print(f"[DEBUG] Images loaded: image={image.size}, mask={mask.size}")

        # Combine image and mask into RGBA
        if image.mode == "RGB":
            print(f"[DEBUG] Converting RGB to RGBA with mask")
            image_array = np.array(image)
            mask_array = np.array(mask)

            # Create RGBA image
            rgba = np.zeros((image_array.shape[0], image_array.shape[1], 4), dtype=np.uint8)
            rgba[:, :, :3] = image_array
            rgba[:, :, 3] = mask_array

            combined_image = Image.fromarray(rgba, "RGBA")
        else:
            combined_image = image
            print(f"[DEBUG] Using image as-is (mode: {image.mode})")

        jobs[job_id]["progress"] = 0.3
        jobs[job_id]["message"] = "Running inference (Stage 1)..."
        print(f"[DEBUG] Starting inference with seed={seed}")

        # Convert to numpy arrays (inference expects numpy, not PIL)
        image_np = np.array(combined_image)

        # Extract mask from alpha channel of RGBA image (like demo.py does)
        # This is the correct format: mask is derived from alpha channel
        if image_np.shape[2] == 4:  # RGBA
            mask_np = image_np[:, :, 3]  # Extract alpha channel
            print(f"[DEBUG] Extracted mask from alpha channel")
        else:
            # Fallback: use separate mask file
            mask_np = np.array(mask)
            print(f"[DEBUG] Using separate mask file (fallback)")

        print(f"[DEBUG] Image shape={image_np.shape}, Mask shape={mask_np.shape}")
        print(f"[DEBUG] Image dtype={image_np.dtype}, min={image_np.min()}, max={image_np.max()}")
        print(f"[DEBUG] Mask dtype={mask_np.dtype}, min={mask_np.min()}, max={mask_np.max()}")
        print(f"[DEBUG] Mask unique values: {np.unique(mask_np)}")
        print(f"[DEBUG] Mask non-zero pixels: {np.count_nonzero(mask_np)}/{mask_np.size}")

        # Normalize mask to binary (0 or 1) - inference expects this
        mask_np = (mask_np > 127).astype(np.float32)
        print(f"[DEBUG] After normalization - Mask unique values: {np.unique(mask_np)}")
        print(f"[DEBUG] After normalization - Mask pixels == 1: {np.sum(mask_np == 1)}")

        # Run inference
        output = inference(
            image=image_np,
            mask=mask_np,
            seed=seed
        )
        print(f"[DEBUG] Inference completed successfully")

        jobs[job_id]["progress"] = 0.7
        jobs[job_id]["message"] = "Saving outputs..."

        # Create output directory for this job
        job_output_dir = OUTPUT_DIR / job_id
        job_output_dir.mkdir(exist_ok=True)

        # Save outputs
        result = {
            "jobId": job_id,  # Use camelCase for frontend
            "files": {}
        }

        # Save Gaussian splat (PLY)
        if "gs" in output and output["gs"] is not None:
            ply_path = job_output_dir / "gaussian_splat.ply"
            output["gs"].save_ply(str(ply_path))
            result["files"]["ply"] = str(ply_path.name)

        # Save mesh (GLB)
        if not stage1_only and "glb" in output and output["glb"] is not None:
            glb_path = job_output_dir / "mesh.glb"
            output["glb"].export(str(glb_path))
            result["files"]["glb"] = str(glb_path.name)

        jobs[job_id]["progress"] = 1.0
        jobs[job_id]["status"] = "completed"
        jobs[job_id]["message"] = "Generation completed"
        jobs[job_id]["result"] = result

    except Exception as e:
        print(f"[ERROR] Generation failed for job {job_id}")
        print(f"[ERROR] Exception type: {type(e).__name__}")
        print(f"[ERROR] Exception message: {str(e)}")
        import traceback
        print(f"[ERROR] Full traceback:")
        traceback.print_exc()

        jobs[job_id]["status"] = "failed"
        jobs[job_id]["error"] = str(e)
        jobs[job_id]["message"] = f"Generation failed: {str(e)}"


@app.get("/api/job/{job_id}")
async def get_job_status(job_id: str):
    """
    Get job status

    Args:
        job_id: Job identifier

    Returns:
        JobStatus object
    """
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job not found")

    job_data = jobs[job_id]
    return JobStatus(
        job_id=job_id,
        status=job_data["status"],
        progress=job_data["progress"],
        message=job_data["message"],
        result=job_data.get("result"),
        error=job_data.get("error")
    )


@app.get("/api/download/{job_id}/{filename}")
async def download_file(job_id: str, filename: str):
    """
    Download generated file

    Args:
        job_id: Job identifier
        filename: File to download (e.g., 'gaussian_splat.ply' or 'mesh.glb')

    Returns:
        File download
    """
    file_path = OUTPUT_DIR / job_id / filename

    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")

    return FileResponse(
        path=file_path,
        filename=filename,
        media_type="application/octet-stream"
    )


@app.delete("/api/cleanup/{job_id}")
async def cleanup_job(job_id: str):
    """
    Clean up job files

    Args:
        job_id: Job identifier
    """
    # Remove output directory
    job_output_dir = OUTPUT_DIR / job_id
    if job_output_dir.exists():
        shutil.rmtree(job_output_dir)

    # Remove from jobs dict
    if job_id in jobs:
        del jobs[job_id]

    return {"message": "Job cleaned up successfully"}


if __name__ == "__main__":
    import uvicorn

    # Parse command line arguments
    parser = argparse.ArgumentParser(description='SAM 3D Objects Backend Server')
    parser.add_argument(
        '--port', '-p',
        type=int,
        default=8000,
        help='Port to run the server on (default: 8000)'
    )
    parser.add_argument(
        '--host',
        type=str,
        default='0.0.0.0',
        help='Host to bind to (default: 0.0.0.0 for all interfaces)'
    )
    parser.add_argument(
        '--reload',
        action='store_true',
        help='Enable auto-reload on code changes (development mode)'
    )

    args = parser.parse_args()

    print(f"Starting SAM 3D Objects Backend Server")
    print(f"Host: {args.host}")
    print(f"Port: {args.port}")
    print(f"API URL: http://{args.host if args.host != '0.0.0.0' else 'localhost'}:{args.port}")
    print(f"API Docs: http://{args.host if args.host != '0.0.0.0' else 'localhost'}:{args.port}/docs")
    print(f"Reload: {args.reload}")
    print("-" * 60)

    uvicorn.run(
        app,
        host=args.host,
        port=args.port,
        reload=args.reload
    )
