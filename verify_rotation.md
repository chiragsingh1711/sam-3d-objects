# Rotation Conversion Verification

## Coordinate Transformation

**Z-up to Y-up:** `[X, Y, Z] -> [X, -Z, Y]`

**Rotation Matrix:**
```
R = [1   0   0]
    [0   0  -1]
    [0   1   0]
```

**As Quaternion:** 90° around X-axis = `[0.7071, 0, 0, 0.7071]` in `[x,y,z,w]` format

## Test Case: Identity Rotation

**Scenario:** Object with NO rotation (identity) in Z-up coordinate system

**Model Output:**
- Rotation: `Q_identity = [0, 0, 0, 1]` (no rotation)

**Mesh Export:**
- Vertices transformed by R (Z-up to Y-up)
- Mesh is now physically rotated 90° around X

**Current Implementation:** `Q_blender = R * Q_identity = R`
- Result: `[0.7071, 0, 0, 0.7071]`
- This is a 90° rotation around X in Blender

**Physical Meaning:**
- Blender loads Y-up mesh (already rotated by R)
- We tell Blender to rotate it by R again
- Total rotation: R applied to R-rotated mesh

**Question:** Is this correct?

## Alternative: Similarity Transformation

**Formula:** `Q_blender = R^(-1) * Q_orig * R`

For identity:
- `Q_blender = R^(-1) * I * R = R^(-1) * R = I` (identity)
- This means: no additional rotation in Blender

**Physical Meaning:**
- Blender loads Y-up mesh (already rotated by R)
- We tell Blender: no rotation
- Mesh appears in its Y-up orientation

## Which is Correct?

The answer depends on **what the transformation data represents**:

1. **If transformation describes object pose in world space (absolute):**
   - The Y-up mesh needs to be "unrotated" back to match Z-up world
   - Use: `Q_blender = R^(-1) * Q_orig * R` (similarity transform)
   - For identity in Z-up: output identity for Blender

2. **If transformation describes object relative to its mesh (relative):**
   - The mesh is already in Y-up, transformations should be in Y-up too
   - Use: `Q_blender = R * Q_orig` (current implementation)
   - For identity in Z-up: output R to account for mesh rotation

## Current Implementation Analysis

The current code uses `R * Q_orig`, which assumes the transformation should be applied in the transformed (Y-up) space.

**Potential Issue:**
- If model outputs "object at identity rotation" (lying flat in XY plane)
- Mesh gets exported in Y-up (physically rotated)
- Blender gets rotation = R (90° around X)
- Result: Object appears rotated in Blender, even though model said "identity"

**Expected Behavior:**
- Object should appear in same pose as model predicted
- But coordinate axes might be different (Z-up vs Y-up)

## Recommendation

The rotation conversion likely needs to use **similarity transformation** or the **inverse** rotation:

```python
# Option 1: Similarity transformation (frame change)
q_transformed = quaternion_multiply(quaternion_multiply(rot_x_90_inv, q_orig), rot_x_90)

# Option 2: Inverse rotation (counteract mesh rotation)
rot_x_neg90 = np.array([-0.7071068, 0.0, 0.0, 0.7071068])  # -90° around X
q_transformed = quaternion_multiply(rot_x_neg90, q_orig)
```

However, this needs **empirical testing** with actual 3D models to verify correct behavior.
