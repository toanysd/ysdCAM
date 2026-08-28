import React, { useEffect, useState } from 'react';
import { Canvas } from '@react-three/fiber';
import { OrbitControls, Stage } from '@react-three/drei';
import { STLLoader } from 'three-stdlib';

const ModelPreview3D = ({ filename, boundingBox }) => {
  const [geometry, setGeometry] = useState(null);
  const [error, setError] = useState(false);

  useEffect(() => {
    if (!filename) return;
    
    // Fetch the STL from our backend API
    const loadModel = async () => {
      try {
        const response = await fetch(`http://localhost:8888/api/export-3d?filename=${encodeURIComponent(filename)}`);
        if (!response.ok) {
          throw new Error('Failed to fetch STL file');
        }
        
        const contentType = response.headers.get('content-type');
        if (contentType && contentType.includes('application/json')) {
            const errData = await response.json();
            throw new Error(errData.message || 'Error exporting STL');
        }
        
        const arrayBuffer = await response.arrayBuffer();
        
        const headerText = new TextDecoder().decode(arrayBuffer.slice(0, 100));
        if (headerText.includes('"status"') || headerText.includes('Mock Mode')) {
            throw new Error('Backend returned an error instead of STL');
        }

        const loader = new STLLoader();
        const geom = loader.parse(arrayBuffer);
        
        // Center geometry
        geom.computeBoundingBox();
        const centerOffset = -0.5 * (geom.boundingBox.max.x - geom.boundingBox.min.x);
        geom.translate(centerOffset, 
                       -0.5 * (geom.boundingBox.max.y - geom.boundingBox.min.y), 
                       -0.5 * (geom.boundingBox.max.z - geom.boundingBox.min.z));
                       
        setGeometry(geom);
        setError(false);
      } catch (err) {
        console.error("Error loading 3D model:", err);
        setError(true);
      }
    };

    loadModel();
  }, [filename]);

  if (error) {
    return (
      <div style={{ width: '100%', height: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#ff4757', fontSize: '10px', textAlign: 'center', padding: '5px' }}>
        Preview not available.<br/>(Mock Mode or Load Error)
      </div>
    );
  }

  if (!geometry) {
    return (
      <div style={{ width: '100%', height: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'rgba(255,255,255,0.5)', fontSize: '10px' }}>
        Loading 3D Preview...
      </div>
    );
  }

  return (
    <div style={{ width: '100%', height: '100%', position: 'relative' }}>
      {boundingBox && (
        <div style={{
          position: 'absolute', top: '5px', left: '5px', zIndex: 10,
          background: 'rgba(0,0,0,0.6)', color: '#ffb142', fontSize: '10px',
          padding: '2px 6px', borderRadius: '4px', border: '1px solid rgba(255,177,66,0.3)', pointerEvents: 'none'
        }}>
          {Math.abs(boundingBox.x_max - boundingBox.x_min).toFixed(0)} x {Math.abs(boundingBox.y_max - boundingBox.y_min).toFixed(0)} x {Math.abs(boundingBox.z_max - boundingBox.z_min).toFixed(0)} mm
        </div>
      )}
      <Canvas shadows camera={{ position: [0, 0, 150], fov: 50 }} style={{ background: 'transparent' }}>
        <Stage environment="city" intensity={0.5}>
          <mesh geometry={geometry}>
            <meshStandardMaterial color="#3498db" roughness={0.4} metalness={0.5} />
          </mesh>
        </Stage>
        <OrbitControls autoRotate autoRotateSpeed={1.5} enableZoom={true} enablePan={false} />
      </Canvas>
    </div>
  );
};

export default ModelPreview3D;
