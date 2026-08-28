import React, { useRef, useEffect, useState, useMemo, useCallback, forwardRef, useImperativeHandle } from 'react';
import { Stage, Layer, Shape, Line, Circle, Text, Group, Rect, RegularPolygon } from 'react-konva';
import { Canvas, useThree } from '@react-three/fiber';
import { OrthographicCamera, Environment, OrbitControls } from '@react-three/drei';
import * as THREE from 'three';
import { STLLoader } from 'three-stdlib';
import { snapEngine } from './snapLogic';

const CameraUpdater = ({ pan, zoom, bounds, dims, is3DActive }) => {
  const { camera } = useThree();
  useEffect(() => {
    if (!is3DActive && bounds) {
      camera.zoom = zoom;
      const camX = (dims.width / 2 - pan.x) / zoom + bounds.minX;
      const camY = bounds.maxY - (dims.height / 2 - pan.y) / zoom;
      camera.position.set(camX, camY, 200);
      
      // Bắt buộc camera nhìn thẳng xuống (không bị nghiêng)
      camera.rotation.set(0, 0, 0); // Orthographic nhìn thẳng dọc trục -Z
      camera.lookAt(camX, camY, 0);
      
      camera.updateProjectionMatrix();
    }
  }, [pan, zoom, bounds, dims, is3DActive, camera]);
  return null;
};

const CADCanvas = forwardRef(({ showFrameColor, holesData, setHolesData, edgesData, origin, hiddenLayers, allDepths, uniqueDepths, depthColors, activeTool, dimensionsData, setDimensionsData, onMouseMoveWorld, stepFileName, show3DLayer, stepBoundingBox }, ref) => {
  const containerRef = useRef(null);
  const [dims, setDims] = useState({ width: 800, height: 600 });
  const [zoom, setZoom] = useState(1);
  const [pan, setPan] = useState({ x: 0, y: 0 });
  const [selectedHoleIdx, setSelectedHoleIdx] = useState(null);
  const [dimStartPos, setDimStartPos] = useState(null);
  const [mousePos, setMousePos] = useState(null);
  const [actionBasePoint, setActionBasePoint] = useState(null); // Base point cho Move/Copy
  const [currentSnap, setCurrentSnap] = useState(null); // Trạng thái chứa điểm snap hiện tại (type, x, y)
  
  const [geometry3D, setGeometry3D] = useState(null);
  const [geomBounds, setGeomBounds] = useState(null);
  const [viewMode, setViewMode] = useState('2d'); // '2d' or '3d'
  const [isOrbiting, setIsOrbiting] = useState(false);
  const [isLoading3D, setIsLoading3D] = useState(false);

  // Load STL for 3D overlay
  useEffect(() => {
    if (!stepFileName || !show3DLayer) return;
    setIsLoading3D(true);
    const loadModel = async () => {
      try {
        const response = await fetch(`http://localhost:8888/api/export-3d?filename=${encodeURIComponent(stepFileName)}`);
        if (!response.ok) throw new Error('Failed to fetch STL');
        
        const contentType = response.headers.get('content-type');
        if (contentType && contentType.includes('application/json')) {
            const errData = await response.json();
            throw new Error(errData.message || 'Error exporting STL');
        }
        
        const arrayBuffer = await response.arrayBuffer();
        
        // Check if the arrayBuffer is actually a JSON error string
        const headerText = new TextDecoder().decode(arrayBuffer.slice(0, 100));
        if (headerText.includes('"status"') || headerText.includes('Mock Mode')) {
            throw new Error('Backend returned an error instead of STL');
        }

        const loader = new STLLoader();
        const geom = loader.parse(arrayBuffer);
        
        // No translation to center! Keep it at true absolute coordinates
        // CAD Origin matches Three.js Origin (0,0,0)
        geom.computeBoundingBox();
        if (geom.boundingBox) {
          const { min, max } = geom.boundingBox;
          setGeomBounds({ minX: min.x, maxX: max.x, minY: min.y, maxY: max.y, minZ: min.z, maxZ: max.z });
        }
        
        setGeometry3D(geom);
      } catch (err) {
        console.error("Error loading 3D model in CADCanvas:", err);
      } finally {
        setIsLoading3D(false);
      }
    };
    loadModel();
  }, [stepFileName, show3DLayer]);

  // Reset states khi chuyển đổi công cụ
  useEffect(() => {
    setActionBasePoint(null);
    setDimStartPos(null);
    setMousePos(null);
    if (activeTool !== 'move' && activeTool !== 'copy') {
      setSelectedHoleIdx(null);
    }
  }, [activeTool]);

  useEffect(() => {
    let animationFrameId;
    
    const handleResize = () => {
      if (containerRef.current) {
        const { offsetWidth, offsetHeight } = containerRef.current;
        if (offsetWidth > 0 && offsetHeight > 0) {
          setDims({ width: offsetWidth, height: offsetHeight });
        }
      }
    };

    const observer = new ResizeObserver(() => {
      // Use requestAnimationFrame to avoid "ResizeObserver loop limit exceeded"
      if (animationFrameId) cancelAnimationFrame(animationFrameId);
      animationFrameId = requestAnimationFrame(() => {
        handleResize();
      });
    });

    if (containerRef.current) {
      observer.observe(containerRef.current);
      handleResize(); // Initial set
    }
    
    window.addEventListener('resize', handleResize);

    return () => {
      observer.disconnect();
      window.removeEventListener('resize', handleResize);
      if (animationFrameId) cancelAnimationFrame(animationFrameId);
    };
  }, []);

  // ===== MEMOIZED CALCULATIONS =====
  // Tính toán bounds của tất cả lỗ và cạnh để Fit to screen
  const bounds = useMemo(() => {
    let xMin = Infinity, xMax = -Infinity, yMin = Infinity, yMax = -Infinity;
    
    if (holesData && holesData.length > 0) {
      for (const h of holesData) {
        if (h.x < xMin) xMin = h.x;
        if (h.x > xMax) xMax = h.x;
        if (h.y < yMin) yMin = h.y;
        if (h.y > yMax) yMax = h.y;
      }
    }

    if (edgesData && edgesData.length > 0) {
      edgesData.forEach(layer => {
        if (!layer.wires) return;
        layer.wires.forEach(wire => {
          if (wire.type === 'Line' && wire.start && wire.end) {
            xMin = Math.min(xMin, wire.start[0], wire.end[0]);
            xMax = Math.max(xMax, wire.start[0], wire.end[0]);
            yMin = Math.min(yMin, wire.start[1], wire.end[1]);
            yMax = Math.max(yMax, wire.start[1], wire.end[1]);
          } else if ((wire.type === 'Arc' || wire.type === 'ARC') && wire.center && wire.radius) {
            xMin = Math.min(xMin, wire.center[0] - wire.radius);
            xMax = Math.max(xMax, wire.center[0] + wire.radius);
            yMin = Math.min(yMin, wire.center[1] - wire.radius);
            yMax = Math.max(yMax, wire.center[1] + wire.radius);
          }
        });
      });
    }

    if (xMin === Infinity && geomBounds) {
      xMin = geomBounds.minX;
      xMax = geomBounds.maxX;
      yMin = geomBounds.minY;
      yMax = geomBounds.maxY;
    } else if (xMin === Infinity && stepBoundingBox) {
      xMin = stepBoundingBox.x_min;
      xMax = stepBoundingBox.x_max;
      yMin = stepBoundingBox.y_min;
      yMax = stepBoundingBox.y_max;
    }

    if (xMin === Infinity) return null;

    if (origin) {
      // Bỏ qua việc đưa origin vào bounds để tránh việc Zoom Fit bị kéo dãn ra quá xa
      // xMin = Math.min(xMin, origin.x) - 20;
      // xMax = Math.max(xMax, origin.x) + 20;
      // yMin = Math.min(yMin, origin.y) - 20;
      // yMax = Math.max(yMax, origin.y) + 20;
    }
    return { minX: xMin, maxX: xMax, minY: yMin, maxY: yMax, origW: xMax - xMin, origH: yMax - yMin };
  }, [holesData, edgesData, geomBounds, stepBoundingBox, origin]);

  // Dựng 3D Edges BufferGeometry để render cực nhanh hàng vạn đường line
  const edgesGeometry = useMemo(() => {
    if (!edgesData || edgesData.length === 0) return null;
    const positions = [];
    const colors = [];
    const colorObj = new THREE.Color();
    edgesData.forEach(layer => {
      if (!layer.wires) return;
      layer.wires.forEach(wire => {
        if ((wire.type === 'Line' || wire.type === 'LINE') && wire.start && wire.end) {
          // Đặt Z = 0.5 để viền hơi nổi lên mặt khối
          positions.push(wire.start[0], wire.start[1], 0.5);
          positions.push(wire.end[0], wire.end[1], 0.5);
          colorObj.set(wire.color || '#ffffff');
          colors.push(colorObj.r, colorObj.g, colorObj.b);
          colors.push(colorObj.r, colorObj.g, colorObj.b);
        } else if ((wire.type === 'Arc' || wire.type === 'ARC') && wire.center && wire.radius) {
          const segments = 24;
          const { center, radius, startAngle, endAngle, counterClockwise } = wire;
          const sa = startAngle;
          let ea = endAngle;
          if (counterClockwise && ea < sa) ea += 2 * Math.PI;
          if (!counterClockwise && ea > sa) ea -= 2 * Math.PI;
          colorObj.set(wire.color || '#ffffff');
          let prevX = center[0] + radius * Math.cos(sa);
          let prevY = center[1] + radius * Math.sin(sa);
          for (let i = 1; i <= segments; i++) {
            const t = i / segments;
            const a = sa + (ea - sa) * t;
            const x = center[0] + radius * Math.cos(a);
            const y = center[1] + radius * Math.sin(a);
            positions.push(prevX, prevY, 0.5);
            positions.push(x, y, 0.5);
            colors.push(colorObj.r, colorObj.g, colorObj.b);
            colors.push(colorObj.r, colorObj.g, colorObj.b);
            prevX = x; prevY = y;
          }
        }
      });
    });
    if (positions.length === 0) return null;
    const geom = new THREE.BufferGeometry();
    geom.setAttribute('position', new THREE.Float32BufferAttribute(positions, 3));
    geom.setAttribute('color', new THREE.Float32BufferAttribute(colors, 3));
    return geom;
  }, [edgesData]);

  const depthColorMap = useMemo(() => {
    const m = {};
    const zList = [...new Set([
      ...holesData.map(h => h.zDepth), 
      ...(edgesData || []).map(e => e.zDepth)
    ])].filter(x => x !== undefined).sort((a,b) => a - b);
    
    const zColors = {};
    zList.forEach((z, i) => { zColors[z] = depthColors[i % depthColors.length]; });
    
    holesData.forEach(h => { m[h.depth] = zColors[h.zDepth]; });
    (edgesData || []).forEach(e => { m[e.depth] = zColors[e.zDepth]; });
    return m;
  }, [holesData, edgesData, depthColors]);

  const holesByDepth = useMemo(() => {
    const g = {};
    holesData.forEach((hole, idx) => {
      if (!g[hole.depth]) g[hole.depth] = [];
      g[hole.depth].push({ ...hole, _idx: idx });
    });
    return g;
  }, [holesData]);

  // Khi dùng strokeScaleEnabled={false}, độ dày nét (strokeWidth) được tính bằng Pixel thực trên màn hình!
  const strokeW = 1.2; // Nét mảnh chuẩn CAD (1.2px)
  // Tính tỷ lệ font chữ nghịch đảo với zoom để kích thước chữ cố định trên màn hình
  const fontSize = 12 / (zoom || 1); 

  // ===== LOAD DATA INTO RBUSH FOR OSNAP =====
  useEffect(() => {
    if (bounds) {
      snapEngine.loadData(holesData, edgesData, bounds.minX, bounds.maxY, hiddenLayers);
    }
  }, [holesData, edgesData, bounds, hiddenLayers]);

  // ===== ZOOM =====
  const handleWheel = useCallback((e) => {
    e.evt.preventDefault();
    const scaleBy = 1.1;
    const stage = e.target.getStage();
    const oldScale = stage.scaleX();
    const pointer = stage.getPointerPosition();
    const mp = { x: (pointer.x - stage.x()) / oldScale, y: (pointer.y - stage.y()) / oldScale };
    const newScale = e.evt.deltaY > 0 ? oldScale / scaleBy : oldScale * scaleBy;
    setZoom(newScale);
    setPan({ x: pointer.x - mp.x * newScale, y: pointer.y - mp.y * newScale });
  }, []);
  const getRelPos = (stage) => {
    const p = stage.getPointerPosition();
    const s = stage.scaleX();
    return { x: (p.x - stage.x()) / s, y: (p.y - stage.y()) / s };
  };

  // ===== CLICK HANDLER =====
  const handleStageClick = useCallback((e) => {
    const stage = e.target.getStage();
    const pos = getRelPos(stage);
    const snap = snapEngine.findSnapPoint(pos.x, pos.y, 15 / zoom); // Threshold scale theo zoom (AutoCAD Aperture box)

    if (activeTool === 'select') {
      if (snap && snap.type === 'center') {
        setSelectedHoleIdx(snap.originalIndex);
      } else {
        setSelectedHoleIdx(null);
      }
    } else if (activeTool === 'move' || activeTool === 'copy') {
      if (selectedHoleIdx === null) {
        // Bước 1: Chọn đối tượng
        if (snap && snap.type === 'center') {
          setSelectedHoleIdx(snap.originalIndex);
        }
      } else if (!actionBasePoint) {
        // Bước 2: Chọn Base Point
        setActionBasePoint(snap ? { x: snap.x, y: snap.y } : pos);
      } else {
        // Bước 3: Đặt xuống Target Point
        const targetPos = snap ? { x: snap.x, y: snap.y } : pos;
        const dx = targetPos.x - actionBasePoint.x;
        const dy = targetPos.y - actionBasePoint.y;
        
        const orig = holesData[selectedHoleIdx];
        if (activeTool === 'move') {
          const nh = [...holesData];
          nh[selectedHoleIdx] = { ...orig, x: orig.x + dx, y: orig.y - dy }; // y bị ngược chiều trong Canvas
          setHolesData(nh);
        } else if (activeTool === 'copy') {
          setHolesData([...holesData, { ...orig, x: orig.x + dx, y: orig.y - dy }]);
        }
        
        // Reset trạng thái thực thi (giữ nguyên lựa chọn object để move tiếp nếu cần, giống CAD)
        setActionBasePoint(null);
        setMousePos(null);
      }
    } else if (activeTool === 'dimension' && bounds) {
      const targetPos = snap ? { x: snap.x, y: snap.y } : pos;
      
      if (!dimStartPos) {
        setDimStartPos(targetPos);
      } else {
        setDimensionsData([...dimensionsData, { start: dimStartPos, end: targetPos }]);
        setDimStartPos(null);
        setMousePos(null);
      }
    }
  }, [activeTool, selectedHoleIdx, holesData, bounds, dimStartPos, dimensionsData, setHolesData, setDimensionsData]);

  const handleMouseMove = useCallback((e) => {
    const stage = e.target.getStage();
    const pos = getRelPos(stage);
    
    // Tìm điểm Snap gần nhất
    const snap = snapEngine.findSnapPoint(pos.x, pos.y, 15 / zoom);
    setCurrentSnap(snap);

    if (activeTool === 'dimension' && dimStartPos) {
      setMousePos(pos);
    } else if ((activeTool === 'move' || activeTool === 'copy') && actionBasePoint) {
      setMousePos(pos);
    }
    
    // Gửi tọa độ thực (World Coordinates) ra App.jsx cho Status Bar
    if (onMouseMoveWorld && bounds) {
      const worldX = pos.x + bounds.minX;
      const worldY = bounds.maxY - pos.y;
      onMouseMoveWorld(worldX, worldY);
    }
  }, [activeTool, dimStartPos, actionBasePoint, zoom, bounds, onMouseMoveWorld]);

  // ===== FIT =====
  const fitToScreen = useCallback(() => {
    if (!bounds) return;
    const pad = 40;
    const sx = (dims.width - pad * 2) / bounds.origW;
    const sy = (dims.height - pad * 2) / bounds.origH;
    const s = Math.min(sx, sy);
    setZoom(s);
    setPan({ x: dims.width / 2 - (bounds.origW / 2) * s, y: dims.height / 2 - (bounds.origH / 2) * s });
  }, [bounds, dims]);

  useEffect(() => {
    if (holesData.length > 0 || (edgesData && edgesData.length > 0)) fitToScreen();
  }, [holesData.length, edgesData ? edgesData.length : 0, dims.width, dims.height]);

  // Expose fitToScreen để App.jsx gọi qua ref (nút Zoom Fit trên Toolbar)
  useImperativeHandle(ref, () => ({
    fitToScreen
  }), [fitToScreen]);

  const handlePointerDownWrapper = (e) => {
    if (e.button === 1 || (e.button === 0 && (e.ctrlKey || e.shiftKey))) {
        setIsOrbiting(true);
    }
  };
  
  const handlePointerUpWrapper = (e) => {
    if (isOrbiting) {
        setIsOrbiting(false);
    }
  };

  const is3DActive = viewMode === '3d' || isOrbiting;
  const minX = bounds ? bounds.minX : 0;
  const maxY = bounds ? bounds.maxY : 0;

  return (
    <div ref={containerRef} 
         onPointerDown={handlePointerDownWrapper} 
         onPointerUp={handlePointerUpWrapper}
         onContextMenu={(e) => e.preventDefault()}
         style={{ width: '100%', height: '100%', backgroundColor: '#0f1115', position: 'relative', overflow: 'hidden' }}>
      
      {/* ===== EMPTY STATE ===== */}
      {!bounds ? (
        <div style={{ textAlign: 'center', height: '100%', display: 'flex', flexDirection: 'column', justifyContent: 'center' }}>
          {isLoading3D ? (
            <div>
              <h2 style={{ fontSize: '1.4rem', color: '#3498db', letterSpacing: '3px' }}>
                <span className="blink-text">LOADING 3D GEOMETRY...</span>
              </h2>
              <p style={{ color: 'var(--text-muted)' }}>Parsing STEP and rendering triangles...</p>
            </div>
          ) : (
            <div>
              <h2 style={{ fontSize: '1.4rem', color: 'var(--text-muted)', letterSpacing: '3px' }}>
                NO DATA LOADED
              </h2>
              <p style={{ color: 'var(--text-muted)', fontSize: '0.9rem' }}>Upload a file or run calculation</p>
            </div>
          )}
        </div>
      ) : (
        <>
      
      {/* Toolbars & Overlays */}
      <div style={{ position: 'absolute', top: 8, right: 8, zIndex: 10, display: 'flex', gap: '8px' }}>
        <button onClick={() => setViewMode(prev => prev === '2d' ? '3d' : '2d')}
          style={{ background: viewMode === '3d' ? 'rgba(52,152,219,0.5)' : 'rgba(52,152,219,0.2)', color: '#3498db', border: '1px solid #3498db', padding: '3px 8px', borderRadius: '3px', cursor: 'pointer', fontSize: '0.7rem' }}>
          {viewMode === '3d' ? '👁 3D Mode' : '👁 2D Mode'}
        </button>
        <button onClick={fitToScreen}
          style={{ background: 'rgba(46,213,115,0.2)', color: '#2ed573', border: '1px solid #2ed573', padding: '3px 8px', borderRadius: '3px', cursor: 'pointer', fontSize: '0.7rem' }}>
          🔄 Fit
        </button>
      </div>

      {isLoading3D && (
        <div style={{ position: 'absolute', top: '10px', right: '10px', zIndex: 100, background: 'rgba(0,0,0,0.7)', color: '#3498db', padding: '10px 20px', borderRadius: '5px', fontWeight: 'bold', border: '1px solid #3498db', boxShadow: '0 0 10px rgba(52,152,219,0.5)' }}>
          <span style={{ display: 'inline-block', animation: 'spin 1s linear infinite' }}>⏳</span> Đang xử lý 3D...
        </div>
      )}

      {/* 3D Overlay Layer */}
      {show3DLayer && geometry3D && bounds && (
        <div style={{ position: 'absolute', top: 0, left: 0, width: '100%', height: '100%', zIndex: is3DActive ? 2 : 0, pointerEvents: is3DActive ? 'auto' : 'none' }}>
          <Canvas orthographic={!is3DActive} camera={{ 
            zoom: is3DActive ? 1 : zoom, 
            position: is3DActive 
                ? [(bounds.minX + bounds.maxX)/2, bounds.maxY + 300, 300]
                : [(dims.width / 2 - pan.x) / zoom + bounds.minX, bounds.maxY - (dims.height / 2 - pan.y) / zoom, 200], 
            near: -2000, far: 2000 
          }}>
            <ambientLight intensity={0.5} />
            <directionalLight position={[100, 100, 100]} intensity={1.5} castShadow />
            <Environment preset="city" />
            <CameraUpdater pan={pan} zoom={zoom} bounds={bounds} dims={dims} is3DActive={is3DActive} />
            
            {is3DActive && <OrbitControls 
              enablePan={true}
              enableZoom={true}
              enableRotate={true}
              mouseButtons={{
                LEFT: THREE.MOUSE.ROTATE,
                MIDDLE: THREE.MOUSE.ROTATE,
                RIGHT: THREE.MOUSE.PAN
              }}
              target={[(bounds.minX + bounds.maxX)/2, (bounds.minY + bounds.maxY)/2, 0]}
            />}

            <mesh geometry={geometry3D}>
              <meshStandardMaterial color="#3498db" roughness={0.4} metalness={0.5} opacity={is3DActive ? 0.8 : 0.8} transparent={true} />
            </mesh>
            
            {/* 3D Holes overlay */}
            {is3DActive && holesData.filter(h => h.is_active !== false).map((h, i) => {
              const r = h.radius || (h.diameter ? h.diameter / 2 : 2.1);
              const depthVal = h.actual_z !== undefined ? Math.abs(h.actual_z) : (parseFloat(h.depth) || 10);
              // Cylinder mặc định nằm dọc trục Y, ta xoay nó dọc trục Z (X: Math.PI/2)
              // Cylinder có tâm ở giữa, nên đẩy xuống depthVal/2 so với điểm 0
              return (
                <mesh key={i} position={[h.x, h.y, -depthVal / 2]} rotation={[Math.PI / 2, 0, 0]}>
                  <cylinderGeometry args={[r, r, depthVal, 32]} />
                  <meshStandardMaterial color="#e74c3c" emissive="#c0392b" emissiveIntensity={0.5} />
                </mesh>
              );
            })}

            {/* 3D Edges Overlay */}
            {is3DActive && edgesGeometry && (
              <lineSegments geometry={edgesGeometry}>
                <lineBasicMaterial vertexColors={true} linewidth={1} />
              </lineSegments>
            )}
          </Canvas>
        </div>
      )}

      {/* 2D Konva Layer */}
      <Stage width={dims.width} height={dims.height}
        scaleX={zoom} scaleY={zoom} x={pan.x} y={pan.y}
        onWheel={handleWheel}
        draggable={activeTool === 'select'}
        onClick={handleStageClick} onTap={handleStageClick}
        onMouseMove={handleMouseMove}
        onDragMove={(e) => { if (e.target === e.target.getStage()) setPan({ x: e.target.x(), y: e.target.y() }); }}
        onDragEnd={(e) => { if (e.target === e.target.getStage()) setPan({ x: e.target.x(), y: e.target.y() }); }}
        style={{ cursor: activeTool === 'select' ? 'grab' : 'crosshair', position: 'absolute', top: 0, left: 0, zIndex: 1, opacity: is3DActive ? 0 : 1, pointerEvents: is3DActive ? 'none' : 'auto' }}
      >
        {/* ===== STATIC LAYER — No event listeners ===== */}
        <Layer listening={false}>
          {/* Axes */}
          <Line points={[-100000, maxY - origin.y, 100000, maxY - origin.y]} stroke="#a4b0be" strokeWidth={strokeW} strokeScaleEnabled={false} dash={[10/zoom, 10/zoom]} />
          <Line points={[origin.x - minX, -100000, origin.x - minX, 100000]} stroke="#a4b0be" strokeWidth={strokeW} strokeScaleEnabled={false} dash={[10/zoom, 10/zoom]} />
          <Text x={origin.x - minX + 5/zoom} y={maxY - origin.y - 15/zoom} text="X" fill="#a4b0be" fontSize={fontSize} fontStyle="bold" />
          <Text x={origin.x - minX + 5/zoom} y={maxY - origin.y + 5/zoom} text="Y" fill="#a4b0be" fontSize={fontSize} fontStyle="bold" />

          {/* BATCH EDGES — 1 Shape per depth & color */}
          {allDepths.map(depth => {
            if (hiddenLayers[`edge-${depth}`]) return null;
            const grps = (edgesData || []).filter(eg => eg.depth === depth);
            if (grps.length === 0) return null;
            
            const allWires = grps.flatMap(eg => eg.wires);
            const colorGroups = {};
            allWires.forEach(w => {
              const c = w.color || (showFrameColor ? (depthColorMap[depth] || '#888') : '#555555');
              if (!colorGroups[c]) colorGroups[c] = [];
              colorGroups[c].push(w);
            });

            return Object.keys(colorGroups).map((c, i) => (
              <Shape key={`be-${depth}-${i}`} stroke={c} strokeWidth={strokeW} strokeScaleEnabled={false} opacity={0.6}
                sceneFunc={(ctx, shape) => {
                  ctx.beginPath();
                  colorGroups[c].forEach(wire => {
                    if (Array.isArray(wire)) {
                      if (wire.length > 0) {
                        ctx.moveTo(wire[0].x - minX, maxY - wire[0].y);
                        for (let k = 1; k < wire.length; k++) ctx.lineTo(wire[k].x - minX, maxY - wire[k].y);
                      }
                    } else if (wire.type === 'Line' || wire.type === 'LINE') {
                      ctx.moveTo(wire.start[0] - minX, maxY - wire.start[1]);
                      ctx.lineTo(wire.end[0] - minX, maxY - wire.end[1]);
                    } else if (wire.type === 'Circle' || wire.type === 'CIRCLE') {
                      ctx.moveTo(wire.center[0] - minX + wire.radius, maxY - wire.center[1]);
                      ctx.arc(wire.center[0] - minX, maxY - wire.center[1], wire.radius, 0, Math.PI * 2);
                    } else if (wire.type === 'Arc' || wire.type === 'ARC') {
                      ctx.moveTo(
                        wire.center[0] - minX + wire.radius * Math.cos(wire.startAngle), 
                        maxY - wire.center[1] - wire.radius * Math.sin(wire.startAngle)
                      );
                      const antiClockwise = wire.isCCW !== false;
                      ctx.arc(wire.center[0] - minX, maxY - wire.center[1], wire.radius, -wire.startAngle, -wire.endAngle, antiClockwise);
                    }
                  });
                  ctx.strokeShape(shape);
                }} />
            ));
          })}

          {/* BATCH HOLES — 1 Shape per depth */}
          {allDepths.map(depth => {
            if (hiddenLayers[`hole-${depth}`]) return null;
            const holes = (holesByDepth[depth] || []).filter(h => h.is_active !== false);
            if (holes.length === 0) return null;
            const color = depthColorMap[depth] || '#888';
            return (
              <React.Fragment key={`bh-group-${depth}`}>
                <Shape stroke={color} strokeWidth={strokeW} strokeScaleEnabled={false}
                  sceneFunc={(ctx, shape) => {
                    ctx.beginPath();
                    holes.forEach(h => {
                      if (h._idx === selectedHoleIdx || h.is_calculated) return; // skip selected and calculated
                      const cx = h.x - minX, cy = maxY - h.y, r = (h.diameter || 4.2) / 2;
                      ctx.moveTo(cx + r, cy);
                      ctx.arc(cx, cy, r, 0, Math.PI * 2);
                    });
                    ctx.fillStrokeShape(shape);
                  }} />
                <Shape stroke="#2ecc71" strokeWidth={strokeW * 1.5} strokeScaleEnabled={false}
                  sceneFunc={(ctx, shape) => {
                    ctx.beginPath();
                    holes.forEach(h => {
                      if (h._idx === selectedHoleIdx || !h.is_calculated) return; // skip selected and non-calculated
                      const cx = h.x - minX, cy = maxY - h.y, r = (h.diameter || 4.2) / 2;
                      ctx.moveTo(cx + r, cy);
                      ctx.arc(cx, cy, r, 0, Math.PI * 2);
                      ctx.arc(cx, cy, r, 0, Math.PI * 2);
                    });
                    ctx.fillStrokeShape(shape);
                  }} />
              </React.Fragment>
            );
          })}

          {/* Committed Dimensions */}
          {dimensionsData && dimensionsData.map((dim, idx) => {
            const dx = dim.end.x - dim.start.x, dy = dim.end.y - dim.start.y;
            const dist = Math.sqrt(dx * dx + dy * dy).toFixed(2);
            const mx = (dim.start.x + dim.end.x) / 2, my = (dim.start.y + dim.end.y) / 2;
            return (
              <Group key={`dim-${idx}`}>
                <Line points={[dim.start.x, dim.start.y, dim.end.x, dim.end.y]} stroke="#f1c40f" strokeWidth={strokeW * 1.5} strokeScaleEnabled={false} dash={[4/zoom, 4/zoom]} />
                <Text x={mx} y={my - fontSize} text={`${dist} mm`} fill="#f1c40f" fontSize={fontSize * 0.9} />
              </Group>
            );
          })}
        </Layer>

        {/* ===== INTERACTIVE LAYER — Selected hole + active dimension ===== */}
        <Layer>
          {selectedHoleIdx !== null && holesData[selectedHoleIdx] && (() => {
            const hole = holesData[selectedHoleIdx];
            if (hiddenLayers[`hole-${hole.depth}`]) return null;
            const cx = hole.x - minX, cy = maxY - hole.y, r = (hole.diameter || 4.2) / 2;
            return (
              <Group name="selected-hole" x={cx} y={cy}
                draggable={activeTool === 'select'}
                onDragEnd={(e) => {
                  const nh = [...holesData];
                  nh[selectedHoleIdx] = { ...nh[selectedHoleIdx], x: e.target.x() + minX, y: maxY - e.target.y() };
                  setHolesData(nh);
                }}>
                <Circle x={0} y={0} radius={r + 2/zoom} stroke="#fff" strokeWidth={strokeW * 2} strokeScaleEnabled={false} dash={[4/zoom, 4/zoom]} />
                <Circle x={0} y={0} radius={r} stroke="#fff" strokeWidth={strokeW} strokeScaleEnabled={false} fill="rgba(255,255,255,0.15)" />
                <Line points={[-r - 1.5/zoom, 0, r + 1.5/zoom, 0]} stroke="#fff" strokeWidth={strokeW} strokeScaleEnabled={false} />
                <Line points={[0, -r - 1.5/zoom, 0, r + 1.5/zoom]} stroke="#fff" strokeWidth={strokeW} strokeScaleEnabled={false} />
              </Group>
            );
          })()}

          {activeTool === 'dimension' && dimStartPos && mousePos && (
            <Group>
              <Line points={[dimStartPos.x, dimStartPos.y, mousePos.x, mousePos.y]} stroke="#f1c40f" strokeWidth={strokeW * 1.5} strokeScaleEnabled={false} dash={[4/zoom, 4/zoom]} />
              <Text
                x={(dimStartPos.x + mousePos.x) / 2}
                y={(dimStartPos.y + mousePos.y) / 2 - fontSize}
                text={`${Math.sqrt(Math.pow(mousePos.x - dimStartPos.x, 2) + Math.pow(mousePos.y - dimStartPos.y, 2)).toFixed(2)} mm`}
                fill="#f1c40f" fontSize={fontSize * 0.9} />
            </Group>
          )}

          {/* RUBBER-BAND LINE FOR MOVE/COPY */}
          {(activeTool === 'move' || activeTool === 'copy') && actionBasePoint && mousePos && (
            <Group>
              <Line points={[actionBasePoint.x, actionBasePoint.y, mousePos.x, mousePos.y]} stroke="#a4b0be" strokeWidth={strokeW} strokeScaleEnabled={false} dash={[4/zoom, 4/zoom]} />
              
              {/* Vị trí bóng ma (Ghost) của đối tượng */}
              {selectedHoleIdx !== null && holesData[selectedHoleIdx] && (() => {
                const hole = holesData[selectedHoleIdx];
                const r = (hole.diameter || 4.2) / 2;
                const old_cx = hole.x - bounds.minX;
                const old_cy = bounds.maxY - hole.y;
                const dx = mousePos.x - actionBasePoint.x;
                const dy = mousePos.y - actionBasePoint.y;
                return (
                  <Circle x={old_cx + dx} y={old_cy + dy} radius={r} stroke={activeTool === 'move' ? '#f1c40f' : '#2ed573'} strokeWidth={strokeW} strokeScaleEnabled={false} dash={[4/zoom, 4/zoom]} fill="rgba(255,255,255,0.1)" />
                );
              })()}
            </Group>
          )}

          {/* OSNAP HIGHLIGHT INDICATOR (AutoCAD-like) */}
          {currentSnap && (
            <Group x={currentSnap.x} y={currentSnap.y}>
              {currentSnap.type === 'center' && (
                <Circle x={0} y={0} radius={6 / zoom} stroke="#2ed573" strokeWidth={1.5} strokeScaleEnabled={false} />
              )}
              {currentSnap.type === 'endpoint' && (
                <Rect x={-5 / zoom} y={-5 / zoom} width={10 / zoom} height={10 / zoom} stroke="#2ed573" strokeWidth={1.5} strokeScaleEnabled={false} />
              )}
              {currentSnap.type === 'midpoint' && (
                <RegularPolygon x={0} y={4 / zoom} sides={3} radius={7 / zoom} stroke="#2ed573" strokeWidth={1.5} strokeScaleEnabled={false} />
              )}
            </Group>
          )}
        </Layer>
      </Stage>
      </>
      )}
    </div>
  );
});

CADCanvas.displayName = 'CADCanvas';

export default CADCanvas;
