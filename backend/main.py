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
import math
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


def generate_blender_import_script(scene_metadata: Dict[str, Any]) -> str:
    """
    Generate a Blender Python script to import all GLB files with correct transformations.
    This script can be run directly in Blender's scripting workspace.
    """
    script = '''# Blender Import Script for SAM 3D Objects
# Instructions:
# 1. Extract the ZIP file to a folder
# 2. Open Blender
# 3. Go to Scripting workspace
# 4. Open this script file or paste the contents
# 5. Update the SCENE_FOLDER path below to point to your extracted folder
# 6. Run the script (Alt+P or click "Run Script")

import bpy
import os
import json
from mathutils import Vector, Quaternion, Euler
from math import radians

# === CONFIGURATION ===
# Update this path to point to your extracted scene folder
SCENE_FOLDER = r"C:/path/to/extracted/scene"  # Windows example
# SCENE_FOLDER = "/path/to/extracted/scene"  # Linux/Mac example

# === SCRIPT ===
def import_scene():
    """Import all GLB files with correct transformations"""

    # Load scene metadata
    metadata_path = os.path.join(SCENE_FOLDER, "scene.json")

    if not os.path.exists(metadata_path):
        print(f"ERROR: scene.json not found at {metadata_path}")
        print(f"Please update SCENE_FOLDER path in the script")
        return

    with open(metadata_path, 'r') as f:
        scene_data = json.load(f)

    print(f"Importing {scene_data['num_objects']} objects...")

    # Import each object
    for obj_data in scene_data['objects']:
        filename = obj_data['filename']
        glb_path = os.path.join(SCENE_FOLDER, filename)

        if not os.path.exists(glb_path):
            print(f"WARNING: {filename} not found, skipping")
            continue

        # Import GLB file
        bpy.ops.import_scene.gltf(filepath=glb_path)

        # Get the imported object (last selected)
        imported_obj = bpy.context.selected_objects[0] if bpy.context.selected_objects else None

        if imported_obj:
            # Apply transformations from metadata

            # Location
            if 'blender_location' in obj_data:
                loc = obj_data['blender_location']
                imported_obj.location = Vector(loc)
                print(f"  Location: {loc}")

            # Rotation (prefer Euler, fallback to Quaternion)
            if 'blender_rotation_euler' in obj_data:
                euler = obj_data['blender_rotation_euler']  # Already in radians
                imported_obj.rotation_mode = 'XYZ'
                imported_obj.rotation_euler = Euler(euler, 'XYZ')
                print(f"  Rotation (Euler XYZ): {euler}")
            elif 'blender_rotation_quaternion' in obj_data:
                quat = obj_data['blender_rotation_quaternion']  # [w, x, y, z]
                imported_obj.rotation_mode = 'QUATERNION'
                imported_obj.rotation_quaternion = Quaternion(quat)
                print(f"  Rotation (Quaternion): {quat}")

            # Scale
            if 'blender_scale' in obj_data:
                scale = obj_data['blender_scale']
                imported_obj.scale = Vector(scale)
                print(f"  Scale: {scale}")

            # Rename object for clarity
            mask_name = obj_data.get('mask_filename', f"object_{obj_data['object_id']}")
            imported_obj.name = f"SAM3D_{mask_name.replace('.png', '')}"

            print(f"✓ Imported {filename} as {imported_obj.name}")
        else:
            print(f"WARNING: Could not find imported object for {filename}")

    print(f"\\nImport complete! Imported {scene_data['num_objects']} objects.")
    print(f"All objects are positioned according to their spatial layout in the original image.")

# Run the import
if __name__ == "__main__":
    import_scene()
'''
    return script


@app.post("/api/generate-direct")
async def generate_direct(
    image: UploadFile = File(...),
    masks: List[UploadFile] = File(...),
    seed: Optional[int] = Form(None),

    # Quality parameters
    simplify_ratio: float = Form(0.95),
    texture_size: int = Form(1024),
    fill_holes_max_size: float = Form(0.04),
    texture_baking_views: int = Form(100),
    texture_baking_resolution: int = Form(1024),
    lambda_tv: float = Form(0.01),

    # Existing parameters
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

        Quality parameters:
        simplify_ratio: Ratio of triangles to keep (0.0-1.0, default 0.95)
        texture_size: Size of the output texture (default 1024)
        fill_holes_max_size: Maximum hole size to fill in mesh (default 0.04)
        texture_baking_views: Number of views for texture baking (default 100)
        texture_baking_resolution: Resolution for texture baking rendering (default 1024)
        lambda_tv: Total variation weight for texture optimization (default 0.01)

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
            image_loaded = Image.open(temp_image_path).convert("RGB")  # Ensure RGB
            mask_loaded = Image.open(temp_mask_path).convert("L")      # Ensure grayscale

            # Convert to numpy arrays - let the Inference class handle RGBA merging
            image_np = np.array(image_loaded)  # RGB: shape (H, W, 3)
            mask_np = np.array(mask_loaded)    # Grayscale: shape (H, W)

            print(f"[DEBUG] Image {idx}: shape={image_np.shape}, dtype={image_np.dtype}")
            print(f"[DEBUG] Mask {idx}: shape={mask_np.shape}, dtype={mask_np.dtype}, unique values={np.unique(mask_np)}")

            # Check if mask has valid pixels
            mask_pixels = np.sum(mask_np > 127)
            print(f"[DEBUG] Mask {idx}: pixels > 127: {mask_pixels}")

            if mask_pixels == 0:
                print(f"[WARNING] Mask {idx} has no valid pixels (all black), skipping")
                continue

            # Run inference - pass RGB image and grayscale mask separately
            # The Inference class will handle RGBA merging internally
            print(f"[DEBUG] Starting inference for mask {idx} with seed={seed}")
            output = inference(
                image=image_np,  # RGB numpy array (H, W, 3)
                mask=mask_np,    # Grayscale numpy array (H, W)
                seed=seed,
                # Postprocessing parameters
                with_mesh_postprocess=with_mesh_postprocess,
                with_texture_baking=with_texture_baking,
                with_layout_postprocess=with_layout_postprocess,
                # Quality parameters
                simplify_ratio=simplify_ratio,
                texture_size=texture_size,
                fill_holes_max_size=fill_holes_max_size,
                texture_baking_views=texture_baking_views,
                texture_baking_resolution=texture_baking_resolution,
                lambda_tv=lambda_tv
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

            # Debug: Log what transformation keys are in output
            transform_keys = [k for k in output.keys() if k in ["translation", "rotation", "scale"]]
            print(f"[DEBUG] Transformation keys in output: {transform_keys}")
            for key in transform_keys:
                value = output[key]
                print(f"[DEBUG] {key}: type={type(value)}, shape={getattr(value, 'shape', 'N/A')}")

            # Add transformation data if available in output
            #
            # CRITICAL COORDINATE SYSTEM CONVERSION:
            # 1. Model outputs transformations in Z-up coordinate system
            # 2. Mesh is converted from Z-up to Y-up during GLB export (postprocessing_utils.py:672)
            #    Transformation: [X, Y, Z] -> [X, -Z, Y]
            # 3. For Blender (Z-up), we must apply the SAME transformation to position/rotation
            #    to match the rotated mesh coordinates

            if "translation" in output:
                translation = output["translation"]
                if hasattr(translation, "cpu"):
                    translation = translation.cpu().numpy()

                # Flatten to 1D array if needed (handle shape (1,3) -> (3,))
                translation = translation.flatten()
                x, y, z = translation

                print(f"[DEBUG] Translation (Z-up model space): [{x}, {y}, {z}]")

                # Apply same rotation as mesh: Z-up to Y-up
                # [X, Y, Z] -> [X, -Z, Y]
                x_transformed = x
                y_transformed = -z
                z_transformed = y

                print(f"[DEBUG] Translation (Y-up mesh space): [{x_transformed}, {y_transformed}, {z_transformed}]")

                # For Blender import: Blender will treat the Y-up mesh as-is
                # So we need Y-up coordinates
                metadata["blender_location"] = [x_transformed, y_transformed, z_transformed]

            if "rotation" in output:
                rotation = output["rotation"]
                if hasattr(rotation, "cpu"):
                    rotation = rotation.cpu().numpy()

                # Flatten to 1D array if needed (handle shape (1,4) -> (4,))
                rotation = rotation.flatten()
                rotation_list = rotation.tolist()

                print(f"[DEBUG] Rotation quaternion (Z-up model space): {rotation_list}")

                # Quaternion format check and conversion
                if len(rotation_list) == 4:
                    # Model outputs quaternion in format [x,y,z,w] (from inference_utils.py:322)
                    qx, qy, qz, qw = rotation_list

                    # Convert quaternion from Z-up to Y-up coordinate system
                    # The mesh rotation is: [X, Y, Z] -> [X, -Z, Y]
                    # For quaternions, this rotation is represented as:
                    # Rotation of -90 degrees around X-axis
                    # Q_rotation = [sin(-45°), 0, 0, cos(-45°)] = [-0.707, 0, 0, 0.707]
                    #
                    # Actually, the rotation matrix [[1,0,0],[0,0,-1],[0,1,0]]
                    # corresponds to a 90° rotation around X-axis
                    # As quaternion: [sin(45°), 0, 0, cos(45°)] = [0.707, 0, 0, 0.707]

                    # Quaternion for 90° rotation around X-axis (Z-up to Y-up)
                    rot_x_90 = np.array([0.7071068, 0.0, 0.0, 0.7071068])  # [x, y, z, w]

                    # Multiply quaternions: Q_result = Q_rotation * Q_original
                    # Using Hamilton product
                    q_orig = np.array([qx, qy, qz, qw])

                    def quaternion_multiply(q1, q2):
                        x1, y1, z1, w1 = q1
                        x2, y2, z2, w2 = q2
                        return np.array([
                            w1*x2 + x1*w2 + y1*z2 - z1*y2,
                            w1*y2 - x1*z2 + y1*w2 + z1*x2,
                            w1*z2 + x1*y2 - y1*x2 + z1*w2,
                            w1*w2 - x1*x2 - y1*y2 - z1*z2
                        ])

                    q_transformed = quaternion_multiply(rot_x_90, q_orig)
                    qx_t, qy_t, qz_t, qw_t = q_transformed

                    print(f"[DEBUG] Rotation quaternion (Y-up mesh space): [{qx_t}, {qy_t}, {qz_t}, {qw_t}]")

                    # Blender format: [w, x, y, z] (w first)
                    metadata["blender_rotation_quaternion"] = [qw_t, qx_t, qy_t, qz_t]

                    # Also convert to Euler angles (XYZ) for easier manual editing in Blender
                    # Using the TRANSFORMED quaternion
                    # Quaternion to Euler (XYZ order) - Blender default
                    # From: https://en.wikipedia.org/wiki/Conversion_between_quaternions_and_Euler_angles
                    # Using transformed quaternion values

                    # Roll (x-axis rotation)
                    sinr_cosp = 2 * (qw_t * qx_t + qy_t * qz_t)
                    cosr_cosp = 1 - 2 * (qx_t * qx_t + qy_t * qy_t)
                    roll = math.atan2(sinr_cosp, cosr_cosp)

                    # Pitch (y-axis rotation)
                    sinp = 2 * (qw_t * qy_t - qz_t * qx_t)
                    if abs(sinp) >= 1:
                        pitch = math.copysign(math.pi / 2, sinp)
                    else:
                        pitch = math.asin(sinp)

                    # Yaw (z-axis rotation)
                    siny_cosp = 2 * (qw_t * qz_t + qx_t * qy_t)
                    cosy_cosp = 1 - 2 * (qy_t * qy_t + qz_t * qz_t)
                    yaw = math.atan2(siny_cosp, cosy_cosp)

                    # Blender uses radians for rotation
                    metadata["blender_rotation_euler"] = [roll, pitch, yaw]  # radians, XYZ order

            if "scale" in output:
                scale = output["scale"]
                if hasattr(scale, "cpu"):
                    scale = scale.cpu().numpy()

                # Flatten to 1D array if needed (handle shape (1,3) -> (3,))
                scale = scale.flatten()
                scale_list = scale.tolist()

                print(f"[DEBUG] Scale after flatten: {scale_list}")

                metadata["blender_scale"] = scale_list  # [x, y, z]

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

            # Generate Blender Python import script
            blender_script = generate_blender_import_script(scene_metadata)
            zipf.writestr("import_to_blender.py", blender_script)

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
