#!/usr/bin/env python3
"""
Test script to verify rotation conversion from Z-up to Y-up coordinate system.

Coordinate transformation:
- Z-up to Y-up: [X, Y, Z] -> [X, -Z, Y]
- Rotation matrix: [[1, 0, 0], [0, 0, -1], [0, 1, 0]]
- As quaternion: 90° around X-axis = [0.7071068, 0, 0, 0.7071068] in [x,y,z,w] format
"""

import numpy as np
from scipy.spatial.transform import Rotation as R

def quaternion_multiply(q1, q2):
    """Hamilton product of two quaternions in [x, y, z, w] format."""
    x1, y1, z1, w1 = q1
    x2, y2, z2, w2 = q2
    return np.array([
        w1*x2 + x1*w2 + y1*z2 - z1*y2,
        w1*y2 - x1*z2 + y1*w2 + z1*x2,
        w1*z2 + x1*y2 - y1*x2 + z1*w2,
        w1*w2 - x1*x2 - y1*y2 - z1*z2
    ])

def test_rotation_conversion():
    """Test various rotation scenarios."""

    # The coordinate system transformation: 90° around X-axis
    # This transforms Z-up to Y-up
    rot_x_90_deg = 90
    rot_x_90_rad = np.radians(rot_x_90_deg)
    rot_x_90 = np.array([np.sin(rot_x_90_rad/2), 0, 0, np.cos(rot_x_90_rad/2)])
    print(f"Coordinate transformation quaternion (90° around X): {rot_x_90}")
    print(f"  = [{rot_x_90[0]:.7f}, {rot_x_90[1]:.7f}, {rot_x_90[2]:.7f}, {rot_x_90[3]:.7f}]")
    print()

    # Verify with scipy
    r_scipy = R.from_euler('x', 90, degrees=True)
    q_scipy = r_scipy.as_quat()  # scipy uses [x, y, z, w] format
    print(f"Scipy verification: {q_scipy}")
    print()

    # Test case 1: Identity rotation (no rotation)
    print("=" * 70)
    print("Test 1: Identity rotation (object not rotated)")
    print("=" * 70)
    q_identity = np.array([0, 0, 0, 1])  # [x, y, z, w]
    print(f"Original rotation (Z-up): {q_identity}")

    q_transformed_1 = quaternion_multiply(rot_x_90, q_identity)
    print(f"After coord transform (Y-up): {q_transformed_1}")
    print(f"Expected: Same as coordinate transformation = {rot_x_90}")
    print()

    # Test case 2: 90° rotation around Z-axis (in Z-up)
    # In Z-up: rotating 90° around Z
    # After transformation to Y-up: Z becomes Y, so this should become 90° around Y
    print("=" * 70)
    print("Test 2: 90° rotation around Z-axis (in Z-up coordinate system)")
    print("=" * 70)
    rot_z_90_rad = np.radians(90)
    q_z_90 = np.array([0, 0, np.sin(rot_z_90_rad/2), np.cos(rot_z_90_rad/2)])
    print(f"Original rotation (Z-up): 90° around Z = {q_z_90}")

    q_transformed_2 = quaternion_multiply(rot_x_90, q_z_90)
    print(f"After coord transform (Y-up): {q_transformed_2}")

    # What should this be? 90° around Y in Y-up system
    rot_y_90_rad = np.radians(90)
    q_y_90_expected = np.array([0, np.sin(rot_y_90_rad/2), 0, np.cos(rot_y_90_rad/2)])
    print(f"Expected (90° around Y): {q_y_90_expected}")
    print(f"Match: {np.allclose(q_transformed_2, q_y_90_expected)}")
    print()

    # Test case 3: 90° rotation around Y-axis (in Z-up)
    # In Z-up: rotating 90° around Y
    # After transformation to Y-up: Y becomes -Z, so this should become -90° around Z?
    print("=" * 70)
    print("Test 3: 90° rotation around Y-axis (in Z-up coordinate system)")
    print("=" * 70)
    rot_y_90_rad = np.radians(90)
    q_y_90_zup = np.array([0, np.sin(rot_y_90_rad/2), 0, np.cos(rot_y_90_rad/2)])
    print(f"Original rotation (Z-up): 90° around Y = {q_y_90_zup}")

    q_transformed_3 = quaternion_multiply(rot_x_90, q_y_90_zup)
    print(f"After coord transform (Y-up): {q_transformed_3}")

    # In Y-up, Y becomes -Z from Z-up perspective
    # So 90° around Y (in Z-up) should become 90° around -Z = -90° around Z (in Y-up)
    rot_z_neg90_rad = np.radians(-90)
    q_z_neg90_expected = np.array([0, 0, np.sin(rot_z_neg90_rad/2), np.cos(rot_z_neg90_rad/2)])
    print(f"Expected (-90° around Z): {q_z_neg90_expected}")
    print(f"Match: {np.allclose(q_transformed_3, q_z_neg90_expected)}")
    print()

    # Test case 4: Using scipy to verify the transformation
    print("=" * 70)
    print("Test 4: Verify using scipy Rotation composition")
    print("=" * 70)

    # Original rotation: 90° around Z in Z-up
    r_orig = R.from_euler('z', 90, degrees=True)
    print(f"Original: 90° around Z (Z-up)")

    # Coordinate transformation: 90° around X
    r_coord_transform = R.from_euler('x', 90, degrees=True)
    print(f"Coord transform: 90° around X")

    # Combined rotation: apply coord transform, then original rotation
    r_combined = r_coord_transform * r_orig
    q_combined = r_combined.as_quat()
    print(f"Combined (scipy): {q_combined}")
    print(f"Our implementation: {q_transformed_2}")
    print(f"Match: {np.allclose(q_combined, q_transformed_2)}")
    print()

    # Alternative: Is it R * Q * R^(-1) (similarity transformation)?
    print("=" * 70)
    print("Test 5: Try similarity transformation R * Q * R^(-1)")
    print("=" * 70)

    r_inv = r_coord_transform.inv()
    r_similarity = r_coord_transform * r_orig * r_inv
    q_similarity = r_similarity.as_quat()
    print(f"Similarity transform: {q_similarity}")
    print(f"Simple multiplication: {q_combined}")
    print(f"Are they same? {np.allclose(q_similarity, q_combined)}")
    print()

    # Test the actual transformation on a point
    print("=" * 70)
    print("Test 6: Verify by transforming actual points")
    print("=" * 70)

    # Point in Z-up coordinates
    point_zup = np.array([1, 0, 0])
    print(f"Point in Z-up: {point_zup}")

    # Apply rotation in Z-up (90° around Z)
    point_rotated_zup = r_orig.apply(point_zup)
    print(f"After 90° rotation around Z: {point_rotated_zup}")

    # Now transform this point to Y-up coordinates
    # Z-up to Y-up: [X, Y, Z] -> [X, -Z, Y]
    point_yup = np.array([point_rotated_zup[0], -point_rotated_zup[2], point_rotated_zup[1]])
    print(f"Transformed to Y-up coordinates: {point_yup}")

    # Alternative: First transform point to Y-up, then apply transformed rotation
    point_zup_to_yup = np.array([point_zup[0], -point_zup[2], point_zup[1]])
    print(f"\nOriginal point in Y-up coords: {point_zup_to_yup}")

    # Apply the transformed rotation in Y-up
    r_transformed = R.from_quat(q_combined)
    point_rotated_yup = r_transformed.apply(point_zup_to_yup)
    print(f"After applying transformed rotation: {point_rotated_yup}")

    print(f"\nDo they match? {np.allclose(point_yup, point_rotated_yup)}")
    print()

if __name__ == "__main__":
    test_rotation_conversion()
