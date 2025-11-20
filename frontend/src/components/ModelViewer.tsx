import React, { useEffect, useRef, useState } from 'react';
import { Canvas, useThree } from '@react-three/fiber';
import {
  OrbitControls,
  Environment,
  PerspectiveCamera,
  useGLTF,
  TransformControls,
  Grid,
  Sky,
} from '@react-three/drei';
import * as THREE from 'three';
import { PLYLoader } from 'three/examples/jsm/loaders/PLYLoader.js';
import { Settings, RotateCw, Move, Maximize2 } from 'lucide-react';

interface ModelViewerProps {
  plyUrl?: string;
  glbUrl?: string;
  modelType: 'ply' | 'glb';
}

interface ControlsState {
  envIntensity: number;
  ambientIntensity: number;
  directionalIntensity: number;
  showGrid: boolean;
  showSky: boolean;
  metalness: number;
  roughness: number;
  transformMode: 'translate' | 'rotate' | 'scale' | null;
  backgroundColor: string;
  cameraFov: number;
}

const PLYModel: React.FC<{ url: string; controls: ControlsState }> = ({ url, controls }) => {
  const meshRef = useRef<THREE.Mesh>(null);
  const [geometry, setGeometry] = useState<THREE.BufferGeometry | null>(null);

  useEffect(() => {
    console.log('[PLYLoader] Loading PLY from:', url);
    const loader = new PLYLoader();

    loader.load(
      url,
      (loadedGeometry) => {
        console.log('[PLYLoader] PLY loaded successfully');
        console.log('[PLYLoader] Vertices:', loadedGeometry.attributes.position?.count);
        console.log('[PLYLoader] Has colors:', !!loadedGeometry.attributes.color);

        loadedGeometry.computeVertexNormals();

        // Center and scale
        loadedGeometry.center();
        loadedGeometry.computeBoundingBox();
        const bbox = loadedGeometry.boundingBox!;
        const size = bbox.getSize(new THREE.Vector3());
        const maxDim = Math.max(size.x, size.y, size.z);
        const scale = 2 / maxDim; // Normalize to size 2
        loadedGeometry.scale(scale, scale, scale);

        console.log('[PLYLoader] Model size:', size, 'Scale:', scale);

        setGeometry(loadedGeometry);
      },
      (progress) => {
        console.log('[PLYLoader] Progress:', (progress.loaded / progress.total * 100).toFixed(2) + '%');
      },
      (error) => {
        console.error('[PLYLoader] Error loading PLY:', error);
      }
    );
  }, [url]);

  if (!geometry) {
    return (
      <mesh>
        <boxGeometry args={[0.5, 0.5, 0.5]} />
        <meshStandardMaterial color="#666" wireframe />
      </mesh>
    );
  }

  return (
    <mesh ref={meshRef} geometry={geometry}>
      <meshStandardMaterial
        vertexColors={geometry.attributes.color !== undefined}
        side={THREE.DoubleSide}
        metalness={controls.metalness}
        roughness={controls.roughness}
      />
    </mesh>
  );
};

const GLBModel: React.FC<{ url: string; controls: ControlsState }> = ({ url, controls }) => {
  const { scene } = useGLTF(url);
  const groupRef = useRef<THREE.Group>(null);

  useEffect(() => {
    // Center and scale the model
    const box = new THREE.Box3().setFromObject(scene);
    const center = box.getCenter(new THREE.Vector3());
    const size = box.getSize(new THREE.Vector3());

    const maxDim = Math.max(size.x, size.y, size.z);
    const scale = 2 / maxDim;

    scene.position.set(-center.x, -center.y, -center.z);
    scene.scale.setScalar(scale);
  }, [scene]);

  return <primitive ref={groupRef} object={scene} />;
};

const SceneController: React.FC<{ controls: ControlsState }> = ({ controls }) => {
  const { scene, gl } = useThree();

  useEffect(() => {
    // Update renderer background
    if (controls.backgroundColor === 'transparent') {
      gl.setClearColor(0x000000, 0);
    } else {
      gl.setClearColor(new THREE.Color(controls.backgroundColor), 1);
    }
  }, [controls.backgroundColor, gl]);

  return null;
};

export const ModelViewer: React.FC<ModelViewerProps> = ({
  plyUrl,
  glbUrl,
  modelType,
}) => {
  const url = modelType === 'ply' ? plyUrl : glbUrl;
  const [showControls, setShowControls] = useState(false);
  const [controls, setControls] = useState<ControlsState>({
    envIntensity: 1.0,
    ambientIntensity: 0.5,
    directionalIntensity: 1.0,
    showGrid: true,
    showSky: false,
    metalness: 0.2,
    roughness: 0.8,
    transformMode: null,
    backgroundColor: '#1c1c1e',
    cameraFov: 50,
  });

  const updateControl = <K extends keyof ControlsState>(
    key: K,
    value: ControlsState[K]
  ) => {
    setControls((prev) => ({ ...prev, [key]: value }));
  };

  if (!url) {
    return (
      <div className="w-full h-full flex items-center justify-center bg-dark-elevated rounded-apple">
        <p className="text-dark-text-secondary">No model available</p>
      </div>
    );
  }

  return (
    <div className="w-full h-full flex gap-4">
      {/* 3D Canvas - Takes remaining space */}
      <div className="flex-1 bg-dark-elevated rounded-apple overflow-hidden relative" style={{ minHeight: '600px' }}>
        <Canvas
          shadows
          style={{ width: '100%', height: '100%' }}
          gl={{ preserveDrawingBuffer: true }}
        >
          <PerspectiveCamera
            makeDefault
            position={[3, 2, 3]}
            fov={controls.cameraFov}
          />

          <SceneController controls={controls} />

          {/* Lighting */}
          <ambientLight intensity={controls.ambientIntensity} />
          <directionalLight
            position={[10, 10, 5]}
            intensity={controls.directionalIntensity}
            castShadow
          />
          <directionalLight
            position={[-10, -10, -5]}
            intensity={controls.directionalIntensity * 0.5}
          />
          <pointLight position={[0, 5, 0]} intensity={0.3} />

          {/* Model */}
          <React.Suspense
            fallback={
              <mesh>
                <boxGeometry args={[1, 1, 1]} />
                <meshStandardMaterial color="#444" wireframe />
              </mesh>
            }
          >
            <group>
              {modelType === 'ply' && plyUrl && (
                <PLYModel url={plyUrl} controls={controls} />
              )}
              {modelType === 'glb' && glbUrl && (
                <GLBModel url={glbUrl} controls={controls} />
              )}

              {/* Transform Controls */}
              {controls.transformMode && (
                <TransformControls mode={controls.transformMode} />
              )}
            </group>
          </React.Suspense>

          {/* Environment */}
          <Environment
            preset="studio"
            background={false}
            environmentIntensity={controls.envIntensity}
          />

          {/* Sky */}
          {controls.showSky && <Sky sunPosition={[100, 20, 100]} />}

          {/* Grid */}
          {controls.showGrid && (
            <Grid
              args={[20, 20]}
              cellSize={0.5}
              cellThickness={0.5}
              cellColor="#333"
              sectionSize={2}
              sectionThickness={1}
              sectionColor="#444"
              fadeDistance={25}
              fadeStrength={1}
              infiniteGrid
            />
          )}

          <OrbitControls
            enableDamping
            dampingFactor={0.05}
            minDistance={0.5}
            maxDistance={20}
          />
        </Canvas>

        {/* Toggle Controls Button */}
        <button
          onClick={() => setShowControls(!showControls)}
          className="absolute top-4 right-4 p-2 bg-dark-surface border border-dark-border rounded-apple hover:bg-dark-elevated transition-colors"
          title="Toggle Debug Controls"
        >
          <Settings className="w-5 h-5" />
        </button>
      </div>

      {/* Debug Controls Panel */}
      {showControls && (
        <div className="w-80 bg-dark-surface rounded-apple p-4 overflow-y-auto" style={{ maxHeight: '600px' }}>
          <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
            <Settings className="w-5 h-5" />
            Debug Controls
          </h3>

          <div className="space-y-4">
            {/* Environment */}
            <div className="space-y-2">
              <h4 className="font-medium text-sm text-dark-text-secondary uppercase">Environment</h4>

              <label className="block">
                <span className="text-sm">HDR Intensity</span>
                <input
                  type="range"
                  min="0"
                  max="3"
                  step="0.1"
                  value={controls.envIntensity}
                  onChange={(e) => updateControl('envIntensity', parseFloat(e.target.value))}
                  className="w-full"
                />
                <span className="text-xs text-dark-text-tertiary">{controls.envIntensity.toFixed(1)}</span>
              </label>

              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={controls.showSky}
                  onChange={(e) => updateControl('showSky', e.target.checked)}
                  className="w-4 h-4"
                />
                <span className="text-sm">Show Sky</span>
              </label>

              <label className="block">
                <span className="text-sm">Background Color</span>
                <div className="flex gap-2">
                  {['#1c1c1e', '#000000', '#ffffff', 'transparent'].map((color) => (
                    <button
                      key={color}
                      onClick={() => updateControl('backgroundColor', color)}
                      className={`w-8 h-8 rounded border-2 ${
                        controls.backgroundColor === color
                          ? 'border-accent-primary'
                          : 'border-dark-border'
                      }`}
                      style={{
                        backgroundColor: color === 'transparent' ? '#1c1c1e' : color,
                        backgroundImage:
                          color === 'transparent'
                            ? 'repeating-conic-gradient(#888 0% 25%, #444 0% 50%) 50% / 8px 8px'
                            : undefined,
                      }}
                    />
                  ))}
                </div>
              </label>

              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={controls.showGrid}
                  onChange={(e) => updateControl('showGrid', e.target.checked)}
                  className="w-4 h-4"
                />
                <span className="text-sm">Show Grid</span>
              </label>
            </div>

            {/* Lighting */}
            <div className="space-y-2 pt-4 border-t border-dark-border">
              <h4 className="font-medium text-sm text-dark-text-secondary uppercase">Lighting</h4>

              <label className="block">
                <span className="text-sm">Ambient Light</span>
                <input
                  type="range"
                  min="0"
                  max="2"
                  step="0.1"
                  value={controls.ambientIntensity}
                  onChange={(e) => updateControl('ambientIntensity', parseFloat(e.target.value))}
                  className="w-full"
                />
                <span className="text-xs text-dark-text-tertiary">{controls.ambientIntensity.toFixed(1)}</span>
              </label>

              <label className="block">
                <span className="text-sm">Directional Light</span>
                <input
                  type="range"
                  min="0"
                  max="3"
                  step="0.1"
                  value={controls.directionalIntensity}
                  onChange={(e) => updateControl('directionalIntensity', parseFloat(e.target.value))}
                  className="w-full"
                />
                <span className="text-xs text-dark-text-tertiary">{controls.directionalIntensity.toFixed(1)}</span>
              </label>
            </div>

            {/* Material */}
            <div className="space-y-2 pt-4 border-t border-dark-border">
              <h4 className="font-medium text-sm text-dark-text-secondary uppercase">Material</h4>

              <label className="block">
                <span className="text-sm">Metalness</span>
                <input
                  type="range"
                  min="0"
                  max="1"
                  step="0.05"
                  value={controls.metalness}
                  onChange={(e) => updateControl('metalness', parseFloat(e.target.value))}
                  className="w-full"
                />
                <span className="text-xs text-dark-text-tertiary">{controls.metalness.toFixed(2)}</span>
              </label>

              <label className="block">
                <span className="text-sm">Roughness</span>
                <input
                  type="range"
                  min="0"
                  max="1"
                  step="0.05"
                  value={controls.roughness}
                  onChange={(e) => updateControl('roughness', parseFloat(e.target.value))}
                  className="w-full"
                />
                <span className="text-xs text-dark-text-tertiary">{controls.roughness.toFixed(2)}</span>
              </label>
            </div>

            {/* Camera */}
            <div className="space-y-2 pt-4 border-t border-dark-border">
              <h4 className="font-medium text-sm text-dark-text-secondary uppercase">Camera</h4>

              <label className="block">
                <span className="text-sm">Field of View (FOV)</span>
                <input
                  type="range"
                  min="20"
                  max="100"
                  step="5"
                  value={controls.cameraFov}
                  onChange={(e) => updateControl('cameraFov', parseFloat(e.target.value))}
                  className="w-full"
                />
                <span className="text-xs text-dark-text-tertiary">{controls.cameraFov}°</span>
              </label>
            </div>

            {/* Transform Controls */}
            <div className="space-y-2 pt-4 border-t border-dark-border">
              <h4 className="font-medium text-sm text-dark-text-secondary uppercase">Transform</h4>
              <p className="text-xs text-dark-text-tertiary mb-2">
                Click a mode to enable model transformation
              </p>

              <div className="flex gap-2">
                <button
                  onClick={() =>
                    updateControl('transformMode', controls.transformMode === 'translate' ? null : 'translate')
                  }
                  className={`flex-1 px-3 py-2 rounded-apple text-sm flex items-center justify-center gap-2 ${
                    controls.transformMode === 'translate'
                      ? 'bg-accent-primary text-white'
                      : 'bg-dark-elevated hover:bg-dark-border'
                  }`}
                >
                  <Move className="w-4 h-4" />
                  Move
                </button>

                <button
                  onClick={() =>
                    updateControl('transformMode', controls.transformMode === 'rotate' ? null : 'rotate')
                  }
                  className={`flex-1 px-3 py-2 rounded-apple text-sm flex items-center justify-center gap-2 ${
                    controls.transformMode === 'rotate'
                      ? 'bg-accent-primary text-white'
                      : 'bg-dark-elevated hover:bg-dark-border'
                  }`}
                >
                  <RotateCw className="w-4 h-4" />
                  Rotate
                </button>

                <button
                  onClick={() =>
                    updateControl('transformMode', controls.transformMode === 'scale' ? null : 'scale')
                  }
                  className={`flex-1 px-3 py-2 rounded-apple text-sm flex items-center justify-center gap-2 ${
                    controls.transformMode === 'scale'
                      ? 'bg-accent-primary text-white'
                      : 'bg-dark-elevated hover:bg-dark-border'
                  }`}
                >
                  <Maximize2 className="w-4 h-4" />
                  Scale
                </button>
              </div>
            </div>

            {/* Info */}
            <div className="pt-4 border-t border-dark-border text-xs text-dark-text-tertiary space-y-1">
              <p>Model Type: <span className="text-dark-text-secondary">{modelType.toUpperCase()}</span></p>
              <p>Controls: Drag to rotate • Scroll to zoom • Right-click to pan</p>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
