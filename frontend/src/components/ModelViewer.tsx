import React, { useEffect, useRef, useState } from 'react';
import { Canvas } from '@react-three/fiber';
import { OrbitControls, Environment, PerspectiveCamera, useGLTF } from '@react-three/drei';
import * as THREE from 'three';
import { PLYLoader } from 'three/examples/jsm/loaders/PLYLoader.js';

interface ModelViewerProps {
  plyUrl?: string;
  glbUrl?: string;
  modelType: 'ply' | 'glb';
}

const PLYModel: React.FC<{ url: string }> = ({ url }) => {
  const meshRef = useRef<THREE.Mesh>(null);
  const [geometry, setGeometry] = useState<THREE.BufferGeometry | null>(null);

  useEffect(() => {
    const loader = new PLYLoader();
    loader.load(
      url,
      (loadedGeometry) => {
        loadedGeometry.computeVertexNormals();
        loadedGeometry.center();
        setGeometry(loadedGeometry);
      },
      undefined,
      (error) => {
        console.error('Error loading PLY:', error);
      }
    );
  }, [url]);

  if (!geometry) {
    return null;
  }

  return (
    <mesh ref={meshRef} geometry={geometry}>
      <meshStandardMaterial
        vertexColors
        side={THREE.DoubleSide}
        metalness={0.2}
        roughness={0.8}
      />
    </mesh>
  );
};

const GLBModel: React.FC<{ url: string }> = ({ url }) => {
  const { scene } = useGLTF(url);

  useEffect(() => {
    // Center the model
    const box = new THREE.Box3().setFromObject(scene);
    const center = box.getCenter(new THREE.Vector3());
    scene.position.sub(center);
  }, [scene]);

  return <primitive object={scene} />;
};

export const ModelViewer: React.FC<ModelViewerProps> = ({
  plyUrl,
  glbUrl,
  modelType,
}) => {
  const url = modelType === 'ply' ? plyUrl : glbUrl;

  if (!url) {
    return (
      <div className="w-full h-full flex items-center justify-center bg-dark-elevated rounded-apple">
        <p className="text-dark-text-secondary">No model available</p>
      </div>
    );
  }

  return (
    <div className="w-full h-full bg-dark-elevated rounded-apple overflow-hidden">
      <Canvas>
        <PerspectiveCamera makeDefault position={[0, 0, 3]} />

        <ambientLight intensity={0.5} />
        <directionalLight position={[10, 10, 5]} intensity={1} />
        <directionalLight position={[-10, -10, -5]} intensity={0.5} />

        <React.Suspense
          fallback={
            <mesh>
              <boxGeometry args={[1, 1, 1]} />
              <meshStandardMaterial color="#444" wireframe />
            </mesh>
          }
        >
          {modelType === 'ply' && plyUrl && <PLYModel url={plyUrl} />}
          {modelType === 'glb' && glbUrl && <GLBModel url={glbUrl} />}
        </React.Suspense>

        <Environment preset="studio" />
        <OrbitControls
          enableDamping
          dampingFactor={0.05}
          minDistance={1}
          maxDistance={10}
        />

        <gridHelper args={[10, 10, '#333', '#222']} />
      </Canvas>
    </div>
  );
};
