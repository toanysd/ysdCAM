import { useState, useRef, useEffect, useMemo } from 'react';
import CADCanvas from './CADCanvas';
import DxfParser from 'dxf-parser';
import { useTranslation } from 'react-i18next';
import React, { Suspense } from 'react';
import { APP_PLUGINS } from './components/CAM_Manager/PluginManager';
const ModelPreview3D = React.lazy(() => import('./ModelPreview3D'));

function App() {
  const { t, i18n } = useTranslation();
  const [origin, setOrigin] = useState({ x: 0, y: 0, z: 0 });
  const [toolConfig, setToolConfig] = useState({ toolNo: 1, diameter: 4.2, spindle: 3000, feed: 150, peck: 2.0, zSafe: 10.0, clearance: 2.0 });
  const [activeStep, setActiveStep] = useState(1);
  const [strategy, setStrategy] = useState("polygon");
  const [selectedFile, setSelectedFile] = useState(null);
  const [analysisResult, setAnalysisResult] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [cmdHistory, setCmdHistory] = useState(["AG-CAM Enterprise v2.0", "Hệ thống đã sẵn sàng."]);
  const [cmdPrompt, setCmdPrompt] = useState("Type a command...");
  const [stepFileName, setStepFileName] = useState(null);
  
  // Calculate Options
  const [showCalcConfig, setShowCalcConfig] = useState(false);
  const [calcMode, setCalcMode] = useState('3d_only');
  const [dxfCalcFile, setDxfCalcFile] = useState(null);
  
  // Custom Workspace States
  const [leftWidth, setLeftWidth] = useState(320);
  const [rightWidth, setRightWidth] = useState(240);
  const [cmdHeight, setCmdHeight] = useState(80);
  const [showLeft, setShowLeft] = useState(true);
  const [showRight, setShowRight] = useState(true);
  const [showCmd, setShowCmd] = useState(true);
  const [showFrameColor, setShowFrameColor] = useState(false);
  const [menuOpen, setMenuOpen] = useState(null); // 'file', 'view', etc.
  const [isResizing, setIsResizing] = useState(false);
  const [activeModule, setActiveModule] = useState('ysdflow'); // 'sketch', '3d', 'ysdflow'

  const [tabs, setTabs] = useState([{ id: 1, name: "Untitled Project" }]);
  const [activeTabId, setActiveTabId] = useState(1);
  const [tabsData, setTabsData] = useState({});

  const getDefProj = () => ({ holesData: [], edgesData: [], origin: {x:0, y:0, z:0}, toolConfig: { toolNo: 1, diameter: 4.2, spindle: 3000, feed: 150, peck: 2.0, zSafe: 10.0, clearance: 2.0 }, dimensionsData: [], analysisResult: null, stepFileName: "", strategy: "polygon" });

  const [holesData, setHolesData] = useState([]);
  const [edgesData, setEdgesData] = useState([]);
  const [activeTool, setActiveTool] = useState('select');
  const [dimensionsData, setDimensionsData] = useState([]);
  const cadCanvasRef = useRef(null);
  
  // History for Undo/Redo
  const [history, setHistory] = useState([]);
  const [historyIndex, setHistoryIndex] = useState(-1);

  const saveHistory = (hData, eData) => {
    const newHist = history.slice(0, historyIndex + 1);
    newHist.push({ holesData: hData, edgesData: eData });
    if (newHist.length > 20) newHist.shift(); // keep 20 steps
    setHistory(newHist);
    setHistoryIndex(newHist.length - 1);
  };

  const handleUndo = () => {
    if (historyIndex > 0) {
      const state = history[historyIndex - 1];
      setHolesData(state.holesData);
      setEdgesData(state.edgesData);
      setHistoryIndex(historyIndex - 1);
    }
  };

  const handleRedo = () => {
    if (historyIndex < history.length - 1) {
      const state = history[historyIndex + 1];
      setHolesData(state.holesData);
      setEdgesData(state.edgesData);
      setHistoryIndex(historyIndex + 1);
    }
  };

  const syncCurrentTab = () => {
    setTabsData(prev => ({ ...prev, [activeTabId]: { holesData, edgesData, origin, toolConfig, dimensionsData, analysisResult, stepFileName, strategy } }));
    setTabs(prev => prev.map(t => t.id === activeTabId ? { ...t, name: stepFileName || "Untitled Project" } : t));
  };

  const switchTab = (id) => {
    if (id === activeTabId) return;
    syncCurrentTab();
    const data = tabsData[id] || getDefProj();
    setHolesData(data.holesData || []);
    setEdgesData(data.edgesData || []);
    setOrigin(data.origin || {x:0, y:0, z:0});
    setToolConfig(data.toolConfig || getDefProj().toolConfig);
    setDimensionsData(data.dimensionsData || []);
    setAnalysisResult(data.analysisResult || null);
    setStepFileName(data.stepFileName || "");
    setStrategy(data.strategy || "polygon");
    setActiveTabId(id);
    setHistory([]);
    setHistoryIndex(-1);
  };

  const handleNewProject = () => {
    syncCurrentTab();
    const newId = Date.now();
    setTabs(prev => [...prev, { id: newId, name: "Untitled Project" }]);
    const def = getDefProj();
    setTabsData(prev => ({ ...prev, [newId]: def }));
    setHolesData(def.holesData);
    setEdgesData(def.edgesData);
    setOrigin(def.origin);
    setToolConfig(def.toolConfig);
    setDimensionsData(def.dimensionsData);
    setAnalysisResult(def.analysisResult);
    setStepFileName(def.stepFileName);
    setStrategy(def.strategy);
    setActiveTabId(newId);
    setHistory([]);
    setHistoryIndex(-1);
  };

  const handleCloseTab = (id, e) => {
    e.stopPropagation();
    if (tabs.length === 1) return;
    if (!window.confirm("Close this tab? Unsaved changes will be lost.")) return;
    const newTabs = tabs.filter(t => t.id !== id);
    setTabs(newTabs);
    if (activeTabId === id) {
      switchTab(newTabs[newTabs.length - 1].id);
    }
  };

  // Mouse position in real coordinates for Status Bar
  const [worldMousePos, setWorldMousePos] = useState({ x: 0, y: 0, z: 0 });

  // Layer Manager
  const [hiddenLayers, setHiddenLayers] = useState({});
  const [show3DLayer, setShow3DLayer] = useState(false);
  // Bảng màu tương phản cao (High contrast palette)
  // ANA 10 ưu tiên màu trắng (#FFFFFF) theo yêu cầu.
  const depthColors = useMemo(() => [
    '#FFFFFF', '#FF3333', '#33CCFF', '#FF9900', '#33FF33',
    '#FF33CC', '#FFFF00', '#00FFFF', '#FF6600', '#9933FF'
  ], []);
  const uniqueDepths = [...new Set(holesData.map(h => h.depth))];
  const uniqueEdgeDepths = [...new Set((edgesData || []).map(e => e.depth))];
  
  const [activeLayer, setActiveLayer] = useState(null);
  const [layerNames, setLayerNames] = useState({});
  const [sortConfig, setSortConfig] = useState({ key: 'z', direction: 'desc' });

  const getLayerProps = (depth) => {
    const layerHoles = holesData.filter(h => h.depth === depth);
    const layerEdges = (edgesData || []).filter(e => e.depth === depth);
    const items = layerHoles.length + layerEdges.reduce((sum, eg) => sum + eg.wires.length, 0);
    
    let zVal = 0;
    if (layerHoles.length > 0 && layerHoles[0].zDepth !== undefined) zVal = Number(layerHoles[0].zDepth);
    else if (layerEdges.length > 0 && layerEdges[0].zDepth !== undefined) zVal = Number(layerEdges[0].zDepth);
    
    const name = String(layerNames[depth] || depth).toLowerCase();
    return { name, items, z: zVal };
  };

  const handleSort = (key) => {
    let direction = 'asc';
    if (sortConfig.key === key && sortConfig.direction === 'asc') direction = 'desc';
    setSortConfig({ key, direction });
  };

  const allDepths = [...new Set([...uniqueDepths, ...uniqueEdgeDepths])].sort((a, b) => {
     const pA = getLayerProps(a);
     const pB = getLayerProps(b);
     
     if (pA[sortConfig.key] < pB[sortConfig.key]) return sortConfig.direction === 'asc' ? -1 : 1;
     if (pA[sortConfig.key] > pB[sortConfig.key]) return sortConfig.direction === 'asc' ? 1 : -1;
     return 0;
  });

  const toggleLayer = (depth) => {
    const isHidden = hiddenLayers[`hole-${depth}`] && hiddenLayers[`edge-${depth}`];
    setHiddenLayers(prev => ({
      ...prev,
      [`hole-${depth}`]: !isHidden,
      [`edge-${depth}`]: !isHidden
    }));
  };

  const deleteLayer = (depth) => {
    if (!window.confirm(`Delete layer ${depth}?`)) return;
    const newH = holesData.filter(h => h.depth !== depth);
    const newE = edgesData.filter(e => e.depth !== depth);
    setHolesData(newH);
    setEdgesData(newE);
    saveHistory(newH, newE);
  };

  const addLayer = () => {
    const newName = window.prompt("New layer name:", "Layer 1");
    if (!newName) return;
    const newE = [...edgesData, { face_index: 0, depth: newName, wires: [] }];
    setEdgesData(newE);
    saveHistory(holesData, newE);
    setActiveLayer(newName);
  };

  const logCmd = (msg) => {
    setCmdHistory(prev => [...prev.slice(-4), msg]); // Giữ 5 dòng gần nhất
  };

  useEffect(() => {
    // Update Command Line Prompt based on activeTool
    switch(activeTool) {
      case 'select': setCmdPrompt("Select objects..."); break;
      case 'move': setCmdPrompt("MOVE Select base point or [Displacement] <Displacement>:"); break;
      case 'copy': setCmdPrompt("COPY Specify base point or [Displacement/mOde] <Displacement>:"); break;
      case 'dimension': setCmdPrompt("DIM Specify first extension line origin:"); break;
      default: setCmdPrompt("Command:"); break;
    }
  }, [activeTool]);

  // Handle Panel Resizing
  const handleResize = (e, direction) => {
    e.preventDefault();
    setIsResizing(true);
    const startPos = direction === 'y' ? e.clientY : e.clientX;
    const startLeft = leftWidth;
    const startRight = rightWidth;
    const startCmd = cmdHeight;

    const onMouseMove = (ev) => {
      if (direction === 'left') setLeftWidth(Math.max(200, Math.min(600, startLeft + (ev.clientX - startPos))));
      if (direction === 'right') setRightWidth(Math.max(200, Math.min(600, startRight - (ev.clientX - startPos))));
      if (direction === 'y') setCmdHeight(Math.max(40, Math.min(300, startCmd - (ev.clientY - startPos))));
    };
    const onMouseUp = () => {
      setIsResizing(false);
      document.removeEventListener('mousemove', onMouseMove);
      document.removeEventListener('mouseup', onMouseUp);
    };
    document.addEventListener('mousemove', onMouseMove);
    document.addEventListener('mouseup', onMouseUp);
  };

  const handleOriginChange = (axis, value) => setOrigin(prev => ({ ...prev, [axis]: parseFloat(value) || 0 }));
  
  const handleOpenProject = async () => {
    if ('showOpenFilePicker' in window) {
      try {
        const [fileHandle] = await window.showOpenFilePicker({
          types: [
            { description: 'YSD CAM Project', accept: { 'application/json': ['.ycam'] } },
            { description: 'CAD Files', accept: { 'model/step': ['.step', '.stp'], 'image/dxf': ['.dxf'] } }
          ]
        });
        const file = await fileHandle.getFile();
        handleNewProject(); // Mở sang tab mới
        setTimeout(() => processFile(file, true), 100);
      } catch (err) {
        if (err.name !== 'AbortError') logCmd(`Open Error: ${err.message}`);
      }
    } else {
      const input = document.createElement('input');
      input.type = 'file';
      input.accept = '.ycam,.step,.stp,.dxf';
      input.onchange = (e) => {
        if (e.target.files[0]) {
          handleNewProject(); // Mở sang tab mới
          setTimeout(() => processFile(e.target.files[0], true), 100);
        }
      };
      input.click();
    }
  };

  const handleImportCAD = async () => {
    if ('showOpenFilePicker' in window) {
      try {
        const [fileHandle] = await window.showOpenFilePicker({
          types: [
            {
              description: 'CAD Files',
              accept: {
                'model/step': ['.step', '.stp'],
                'model/iges': ['.iges', '.igs'],
                'image/dxf': ['.dxf']
              }
            }
          ]
        });
        const file = await fileHandle.getFile();
        processFile(file, false); // Nạp vào tab hiện tại
      } catch (err) {
        if (err.name !== 'AbortError') logCmd(`Open Error: ${err.message}`);
      }
    } else {
      const input = document.createElement('input');
      input.type = 'file';
      input.accept = '.step,.stp,.iges,.igs,.dxf';
      input.onchange = (e) => {
        if (e.target.files[0]) processFile(e.target.files[0], false);
      };
      input.click();
    }
  };

  const processFile = async (file, isProject) => {
    if (!file) return;
    
    if (file.name.toLowerCase().endsWith('.ycam')) {
      const reader = new FileReader();
      reader.onload = (ev) => {
        try {
          const data = JSON.parse(ev.target.result);
          setHolesData(data.holesData || []);
          setEdgesData(data.edgesData || []);
          setOrigin(data.origin || { x: 0, y: 0, z: 0 });
          setToolConfig(data.toolConfig || { toolNo: 1, diameter: 4.2, spindle: 3000, feed: 150, peck: 2.0, zSafe: 10.0, clearance: 2.0 });
          setDimensionsData(data.dimensionsData || []);
          setAnalysisResult(data.analysisResult || null);
          setStepFileName(data.stepFileName || file.name);
          setStrategy(data.strategy || "polygon");
          setActiveStep(3);
          saveHistory(data.holesData || [], data.edgesData || []);
          logCmd(`Loaded yCAM project: ${file.name}`);
        } catch(err) {
          logCmd("Error loading yCAM file.");
        }
      };
      reader.readAsText(file);
      return;
    }

    if (file.name.toLowerCase().endsWith('.dxf')) {
      const reader = new FileReader();
      reader.onload = (ev) => {
        try {
          const parser = new DxfParser();
          const dxf = parser.parseSync(ev.target.result);
          
          const newEdges = [];
          const newHoles = [];
          
          if (dxf.entities) {
            const wires = [];
            
            // Hàm xử lý bulge
            const getBulgeArc = (x1, y1, x2, y2, bulge) => {
              const dx = x2 - x1;
              const dy = y2 - y1;
              const d = Math.sqrt(dx * dx + dy * dy);
              const r = (d / 2) * (1 + bulge * bulge) / Math.abs(2 * bulge);
              const alpha = Math.atan2(dy, dx);
              const sagitta = (d / 2) * Math.abs(bulge);
              const apothem = r - sagitta;
              const sign = bulge < 0 ? -1 : 1;
              const cx = (x1 + dx / 2) - sign * apothem * Math.sin(alpha);
              const cy = (y1 + dy / 2) + sign * apothem * Math.cos(alpha);
              const startAngle = Math.atan2(y1 - cy, x1 - cx);
              const endAngle = Math.atan2(y2 - cy, x2 - cx);
              const isCCW = bulge > 0;
              return { type: 'Arc', center: [cx, cy, 0], radius: r, startAngle, endAngle, isCCW };
            };

            const dxfColorMap = {
              1: '#FF0000', 2: '#FFFF00', 3: '#00FF00', 4: '#00FFFF', 5: '#0000FF', 6: '#FF00FF', 7: '#FFFFFF',
              8: '#414141', 9: '#808080', 250: '#333333', 251: '#555555', 252: '#777777', 253: '#999999', 254: '#CCCCCC', 255: '#FFFFFF'
            };
            const getDxfColor = (idx) => dxfColorMap[idx] || '#FFFFFF';

            const layerTable = dxf.tables?.layer?.layers || {};

            dxf.entities.forEach(ent => {
              const layerName = ent.layer || "0";
              let cIdx = ent.colorIndex;
              if (!cIdx || cIdx === 256) {
                 if (layerTable[layerName]) cIdx = layerTable[layerName].colorNumber || layerTable[layerName].color;
              }
              const color = cIdx ? getDxfColor(cIdx) : null;
              if (ent.type === 'LINE') {
                wires.push({ type: 'Line', start: [ent.vertices[0].x, ent.vertices[0].y, 0], end: [ent.vertices[1].x, ent.vertices[1].y, 0], depth: layerName, color });
              } else if (ent.type === 'CIRCLE') {
                if (ent.radius <= 5) {
                  // Cap drill diameter at 4.2mm (pilot hole standard)
                  const drillDia = Math.min(ent.radius * 2, 4.2);
                  newHoles.push({ x: ent.center.x, y: ent.center.y, depth: layerName, r: drillDia / 2, diameter: drillDia, color });
                } else {
                  wires.push({ type: 'Circle', center: [ent.center.x, ent.center.y, 0], radius: ent.radius, depth: layerName, color });
                }
              } else if (ent.type === 'ARC') {
                wires.push({ type: 'Arc', center: [ent.center.x, ent.center.y, 0], radius: ent.radius, startAngle: ent.startAngle, endAngle: ent.endAngle, isCCW: true, depth: layerName, color });
              } else if (ent.type === 'LWPOLYLINE' || ent.type === 'POLYLINE') {
                for (let i = 0; i < ent.vertices.length - 1; i++) {
                  const p1 = ent.vertices[i];
                  const p2 = ent.vertices[i+1];
                  if (p1.bulge) {
                    wires.push({ ...getBulgeArc(p1.x, p1.y, p2.x, p2.y, p1.bulge), depth: layerName, color });
                  } else {
                    wires.push({ type: 'Line', start: [p1.x, p1.y, 0], end: [p2.x, p2.y, 0], depth: layerName, color });
                  }
                }
                if (ent.shape || ent.closed) {
                   const p1 = ent.vertices[ent.vertices.length-1];
                   const p2 = ent.vertices[0];
                   if (p1.bulge) {
                     wires.push({ ...getBulgeArc(p1.x, p1.y, p2.x, p2.y, p1.bulge), depth: layerName, color });
                   } else {
                     wires.push({ type: 'Line', start: [p1.x, p1.y, 0], end: [p2.x, p2.y, 0], depth: layerName, color });
                   }
                }
              }
            });
            
            if (wires.length > 0) {
              // Group wires by layer
              const layers = [...new Set(wires.map(w => w.depth))];
              layers.forEach(l => {
                const layerWires = wires.filter(w => w.depth === l);
                newEdges.push({ face_index: 0, depth: l, wires: layerWires });
              });
            }
          }
          
          setHolesData(prev => { 
            const n = [...prev, ...newHoles]; 
            return n;
          });
          setEdgesData(prevE => {
            const ne = [...prevE, ...newEdges];
            return ne;
          });
          setStepFileName(prev => prev ? `${prev} + ${file.name}` : file.name);
          // Wait for state to update, then save history
          setTimeout(() => {
             setHolesData(h => {
               setEdgesData(e => {
                  saveHistory(h, e);
                  return e;
               });
               return h;
             });
          }, 50);
          setActiveStep(3);
          logCmd(`Loaded DXF drawing: ${file.name}`);
        } catch(err) {
          logCmd(`Error parsing DXF file: ${err.message}`);
        }
      };
      reader.readAsText(file);
      return;
    }

    setSelectedFile(file);
    setActiveStep(2);
    logCmd(`Loaded CAD model: ${file.name}`);

    // Tự động upload để backend có file tạo STL 3D
    const formData = new FormData();
    formData.append("file", file);
    try {
      await fetch('http://localhost:8888/api/upload', { method: 'POST', body: formData });
      setStepFileName(file.name);
      setShow3DLayer(true);
    } catch(e) {
      console.error("Upload error:", e);
    }
  };

  const handleSaveProject = async () => {
    if (holesData.length === 0) {
      logCmd("No data to save.");
      return;
    }
    const projectData = { holesData, edgesData, origin, toolConfig, dimensionsData, analysisResult, stepFileName, strategy };
    const jsonStr = JSON.stringify(projectData, null, 2);
    
    try {
      const suggestedName = stepFileName ? stepFileName.replace(/\.[^/.]+$/, "") + ".ycam" : "project.ycam";
      if ('showSaveFilePicker' in window) {
        const handle = await window.showSaveFilePicker({
          suggestedName,
          types: [{ description: 'YSD CAM Project', accept: { 'application/json': ['.ycam'] } }],
        });
        const writable = await handle.createWritable();
        await writable.write(jsonStr);
        await writable.close();
        logCmd(`Saved project successfully to ${handle.name}`);
      } else {
        const blob = new Blob([jsonStr], { type: "application/json" });
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url; a.download = suggestedName; a.click();
        logCmd(`Saved project via download.`);
      }
    } catch (err) {
      if (err.name !== 'AbortError') logCmd(`Save Error: ${err.message}`);
    }
  };

  const handleExecuteHoles = async () => {
    if (!selectedFile && calcMode === '3d_only') return alert("Vui lòng nạp file STEP trước!");
    if (calcMode !== '3d_only' && !dxfCalcFile) return alert("Vui lòng chọn file DXF cho giải thuật 2D!");
    
    setShowCalcConfig(false);
    setIsLoading(true);
    logCmd(`Analyzing geometry with mode [${calcMode}]...`);
    try {
      const formData = new FormData();
      if (selectedFile) formData.append("file", selectedFile);
      if (dxfCalcFile) formData.append("dxf_file", dxfCalcFile);
      formData.append("strategy", strategy);
      formData.append("calc_mode", calcMode);
      formData.append("tool_radius", toolConfig.diameter / 2.0);
      formData.append("clearance", toolConfig.clearance !== undefined ? toolConfig.clearance : 2.0);
      
      const res = await fetch("http://localhost:8888/api/analyze", {
        method: "POST",
        body: formData
      });
      const data = await res.json();
      if (data.status === "success") {
        setAnalysisResult(data);
        
        // Đổi tên layer tự động theo độ sâu
        // Đổi tên layer tự động theo actual_z để ghép chung Frame và Holes vào cùng 1 Layer
        const renamedHoles = (data.holes || []).map(h => ({
           ...h, 
           depth: `Z ${h.actual_z}`, 
           zDepth: h.actual_z 
        }));
        let renamedEdges = (data.edges || []).map(e => ({
           ...e, 
           depth: `Z ${e.actual_z}`, 
           zDepth: e.actual_z 
        }));
        
        // HLR outline has been removed since we now use depth-based layers exclusively.

        setHolesData(renamedHoles);
        setEdgesData(renamedEdges);
        
        setTimeout(() => {
          setHolesData(h => {
             setEdgesData(e => {
                saveHistory(h, e);
                return e;
             });
             return h;
          });
        }, 50);

        setHiddenLayers({});
        setActiveStep(3);
        logCmd(`Found ${data.holes_processed} holes and extracted pocket edges.`);
      } else {
        logCmd(`Error: ${data.message}`);
      }
    } catch (err) {
      logCmd(`Connection Error: ${err.message}`);
    } finally {
      setIsLoading(false);
    }
  };

  const handleExportDXF = async () => {
    try {
      const formData = new FormData();
      formData.append("origin_x", origin.x);
      formData.append("origin_y", origin.y);
      const res = await fetch("http://localhost:8888/api/export-dxf", { method: "POST", body: formData });
      if (!res.ok) throw new Error("File chưa sẵn sàng");
      const blob = await res.blob();
      
      const suggestedName = stepFileName ? stepFileName.replace(/\.[^/.]+$/, "") + "_Back_Ana.dxf" : "kiem_tra_lo_back_ana.dxf";
      
      if ('showSaveFilePicker' in window) {
        const handle = await window.showSaveFilePicker({
          suggestedName,
          types: [{ description: 'AutoCAD DXF', accept: { 'application/dxf': ['.dxf'] } }],
        });
        const writable = await handle.createWritable();
        await writable.write(blob);
        await writable.close();
        logCmd("Exported DXF drawing successfully.");
      } else {
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url; a.download = suggestedName; a.click();
        logCmd("Exported DXF drawing successfully.");
      }
    } catch (err) {
      if (err.name !== 'AbortError') logCmd(`Export DXF Error: ${err.message}`);
    }
  };

  const handleExportGCode = async () => {
    try {
      const res = await fetch("http://localhost:8888/api/export-gcode", { method: "POST" });
      if (!res.ok) throw new Error("Chưa có GCode");
      const blob = await res.blob();
      
      const suggestedName = stepFileName ? stepFileName.replace(/\.[^/.]+$/, "") + "_G83_DRILL.nc" : "G83_DRILL_BACK_ANA.nc";

      if ('showSaveFilePicker' in window) {
        const handle = await window.showSaveFilePicker({
          suggestedName,
          types: [{ description: 'NC Code / G-Code', accept: { 'text/plain': ['.nc', '.txt', '.gcode'] } }],
        });
        const writable = await handle.createWritable();
        await writable.write(blob);
        await writable.close();
        logCmd("Generated G83 NC code successfully.");
      } else {
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url; a.download = suggestedName; a.click();
        logCmd("Generated G83 NC code successfully.");
      }
    } catch (err) {
      if (err.name !== 'AbortError') logCmd(`Export GCode Error: ${err.message}`);
    }
  };

  return (
    <div className="app-container" onClick={() => { if (menuOpen) setMenuOpen(null) }}>
      {/* 1. MENU BAR */}
      <div className="menu-bar">
        <div className={`menu-item ${menuOpen === 'file' ? 'active' : ''}`} onClick={(e) => { e.stopPropagation(); setMenuOpen(menuOpen === 'file' ? null : 'file'); }}>
          {t('menu.file')}
          {menuOpen === 'file' && (
            <div className="dropdown" onClick={(e) => e.stopPropagation()}>
              <div className="dropdown-item" onClick={() => { handleOpenProject(); setMenuOpen(null); }}><span>{t('menu.open_project')}</span><span>Ctrl+O</span></div>
              <div className="dropdown-item" onClick={() => { handleImportCAD(); setMenuOpen(null); }}><span>{t('menu.import_cad')}</span><span>Ctrl+I</span></div>
              <div className="dropdown-item" onClick={() => { handleSaveProject(); setMenuOpen(null); }}><span>{t('menu.save_as')}</span><span>Ctrl+Shift+S</span></div>
              <div style={{ height: '1px', background: 'var(--border-color)', margin: '4px 0' }}></div>
              <div className="dropdown-item" onClick={() => { handleExportDXF(); setMenuOpen(null); }}><span>{t('menu.export_dxf')}</span></div>
              <div className="dropdown-item" onClick={() => { handleExportGCode(); setMenuOpen(null); }}><span>{t('menu.export_gcode')}</span></div>
              <div style={{ height: '1px', background: 'var(--border-color)', margin: '4px 0' }}></div>
              <div className="dropdown-item" onClick={() => { alert("Settings feature coming soon!"); setMenuOpen(null); }}><span>{t('menu.settings')}</span></div>
            </div>
          )}
        </div>
        <div className="menu-item">{t('menu.edit')}</div>
        <div className={`menu-item ${menuOpen === 'view' ? 'active' : ''}`} onClick={(e) => { e.stopPropagation(); setMenuOpen(menuOpen === 'view' ? null : 'view'); }}>
          {t('menu.view')}
          {menuOpen === 'view' && (
            <div className="dropdown" onClick={(e) => e.stopPropagation()}>
              <div className="dropdown-item" onClick={() => setShowLeft(!showLeft)}>
                <span>{activeModule === 'sketch' ? 'Entities Tree' : activeModule === '3d' ? 'Model Tree' : t('panels.ops_manager')}</span><span>{showLeft ? '✓' : ''}</span>
              </div>
              <div className="dropdown-item" onClick={() => setShowRight(!showRight)}>
                <span>{activeModule === 'sketch' ? t('panels.levels_manager') : activeModule === '3d' ? 'Properties' : 'CAM Parameters'}</span><span>{showRight ? '✓' : ''}</span>
              </div>
              <div className="dropdown-item" onClick={() => setShowCmd(!showCmd)}>
                <span>Command Line</span><span>{showCmd ? '✓' : ''}</span>
              </div>
            </div>
          )}
        </div>
        <div className="menu-item">{t('menu.tools')}</div>
        <div className="menu-item">{t('menu.machine')}</div>
        <div className="menu-item">{t('menu.window')}</div>
        <div className="menu-item">{t('menu.help')}</div>
        
        <div className="menu-item" style={{ marginLeft: 'auto', display: 'flex', alignItems: 'center', gap: '8px' }} onClick={(e) => {
          e.stopPropagation();
          const nextLang = i18n.language === 'en' ? 'vi' : (i18n.language === 'vi' ? 'ja' : 'en');
          i18n.changeLanguage(nextLang);
        }}>
          🌐 {i18n.language.toUpperCase()}
        </div>
      </div>

      {/* 2. RIBBON / STANDARD TOOLBAR */}
      <div className="ribbon">
        {activeModule === 'sketch' && (
          <>
            <button className={`ribbon-btn ${activeTool === 'select' ? 'primary' : ''}`} onClick={() => setActiveTool('select')}>↖ Select</button>
            <button className={`ribbon-btn ${activeTool === 'move' ? 'primary' : ''}`} onClick={() => setActiveTool('move')}>↔ Move</button>
            <button className={`ribbon-btn ${activeTool === 'copy' ? 'primary' : ''}`} onClick={() => setActiveTool('copy')}>⧉ Copy</button>
            <div className="ribbon-divider"></div>
            <button className={`ribbon-btn ${activeTool === 'dimension' ? 'primary' : ''}`} onClick={() => setActiveTool('dimension')}>⭤ Dimension</button>
            <button className="ribbon-btn" onClick={() => setDimensionsData([])}>🗑 Clear Dims</button>
            <div className="ribbon-divider"></div>
            <button className="ribbon-btn" onClick={() => cadCanvasRef.current?.fitToScreen()}>🔄 Fit to Screen</button>
          </>
        )}
        {activeModule === 'ysdflow' && (
          <>
            <button className="ribbon-btn" onClick={handleNewProject}>✨ New</button>
            <button className="ribbon-btn" onClick={handleOpenProject}>📂 {t('toolbar.open_project')}</button>
            <button className="ribbon-btn" onClick={handleImportCAD}>📥 {t('toolbar.import_cad')}</button>
            <button className="ribbon-btn" onClick={handleSaveProject}>💾 {t('toolbar.save_project')}</button>
            <div className="ribbon-divider"></div>
            <button className="ribbon-btn" onClick={handleUndo} disabled={historyIndex <= 0} title="Undo">↩</button>
            <button className="ribbon-btn" onClick={handleRedo} disabled={historyIndex >= history.length - 1} title="Redo">↪</button>
            <div className="ribbon-divider"></div>
            <button className="ribbon-btn" onClick={() => setShowCalcConfig(true)} disabled={activeStep < 2 || isLoading}>
              {isLoading ? `⏳ ${t('toolbar.processing')}` : `⚙️ ${t('toolbar.calc_holes')}`}
            </button>
            <div className="ribbon-divider"></div>
            <button className="ribbon-btn" onClick={handleExportDXF} disabled={activeStep < 3}>📐 {t('toolbar.export_dxf')}</button>
            <button className="ribbon-btn" onClick={handleExportGCode} disabled={activeStep < 3}>🔥 {t('toolbar.post_gcode')}</button>
            <div className="ribbon-divider"></div>
            <button className="ribbon-btn" onClick={() => cadCanvasRef.current?.fitToScreen()}>🔄 {t('toolbar.fit_screen')}</button>
          </>
        )}
        {activeModule === '3d' && (
          <div style={{color: 'var(--text-muted)', fontSize: '12px', paddingLeft: '10px'}}>Mô hình 3D Reference. Di chuột trái để xoay, chuột giữa để cuộn/phóng to.</div>
        )}
      </div>

      {/* 3. MAIN WORKSPACE */}
      <div className="workspace-wrapper">
        {/* MODULE SWITCHER (LEFT EDGE) */}
        <div className="module-switcher">
          {APP_PLUGINS.filter(p => p.enabled).map(plugin => (
            <div 
              key={plugin.id}
              className={`module-btn ${activeModule === plugin.id ? 'active' : ''}`} 
              onClick={() => setActiveModule(plugin.id)} 
              title={plugin.title}
            >
              <span>{plugin.icon}</span>
              <span className="module-btn-text">{plugin.title.split(' ')[0]}</span>
            </div>
          ))}
        </div>

        <div className="workspace" style={{ display: 'flex', flexDirection: 'row', width: '100%', height: '100%', position: 'relative', overflow: 'hidden' }}>
        
        {/* DOCK LEFT: OPERATIONS MANAGER */}
        {showLeft && (
          <div style={{ display: 'flex', position: 'relative', flexShrink: 0 }}>
            <div className="dock-panel left-panel" style={{ width: `${leftWidth}px`, minWidth: `${leftWidth}px`, position: 'relative', boxShadow: '2px 0 10px rgba(0,0,0,0.5)' }}>
              <div className="dock-header">
                <span>{activeModule === 'sketch' ? 'Entities Tree' : activeModule === '3d' ? 'Model Tree' : 'Operations Manager'}</span>
                <span className="close-btn" onClick={() => setShowLeft(false)}>✕</span>
              </div>
              <div className="dock-content">
                
                {activeModule === 'ysdflow' && (
                  <>
                    <div className="input-row"><span className="input-label">Algorithm Strategy</span></div>
                    <div style={{ marginBottom: '15px' }}>
                      <select 
                        value={strategy} 
                        onChange={(e) => setStrategy(e.target.value)}
                        style={{ width: '100%', padding: '5px', background: 'var(--bg-darker)', color: 'white', border: '1px solid var(--border-color)', borderRadius: '4px' }}
                      >
                        <option value="polygon">2D Polygon (Heuristics)</option>
                        <option value="medial_axis">Physics Proxy (Medial Axis)</option>
                      </select>
                    </div>
                  
                    <div className="input-row"><span className="input-label">WCS Origin (G54)</span></div>
                <div style={{ display: 'flex', gap: '5px', marginBottom: '15px' }}>
                  <input type="number" placeholder="X" value={origin.x} onChange={(e) => handleOriginChange('x', e.target.value)} />
                  <input type="number" placeholder="Y" value={origin.y} onChange={(e) => handleOriginChange('y', e.target.value)} />
                  <input type="number" placeholder="Z" value={origin.z} onChange={(e) => handleOriginChange('z', e.target.value)} />
                </div>

                <div className="input-row"><span className="input-label">Tool Setup (T-Plane)</span></div>
                <div style={{ display: 'flex', gap: '5px', marginBottom: '5px' }}>
                  <div style={{ flex: 1 }}><span className="input-label" style={{fontSize: '9px'}}>Tool No.</span><input type="number" value={toolConfig.toolNo} onChange={(e) => handleToolChange('toolNo', e.target.value)} /></div>
                  <div style={{ flex: 1 }}><span className="input-label" style={{fontSize: '9px'}}>Dia (mm)</span><input type="number" value={toolConfig.diameter} onChange={(e) => handleToolChange('diameter', e.target.value)} /></div>
                </div>
                <div style={{ display: 'flex', gap: '5px', marginBottom: '5px' }}>
                  <div style={{ flex: 1 }}><span className="input-label" style={{fontSize: '9px'}}>Spindle (S)</span><input type="number" value={toolConfig.spindle} onChange={(e) => handleToolChange('spindle', e.target.value)} /></div>
                  <div style={{ flex: 1 }}><span className="input-label" style={{fontSize: '9px'}}>Feed (F)</span><input type="number" value={toolConfig.feed} onChange={(e) => handleToolChange('feed', e.target.value)} /></div>
                </div>
                <div style={{ display: 'flex', gap: '5px', marginBottom: '15px' }}>
                  <div style={{ flex: 1 }}><span className="input-label" style={{fontSize: '9px'}}>Peck (Q)</span><input type="number" value={toolConfig.peck} onChange={(e) => handleToolChange('peck', e.target.value)} /></div>
                  <div style={{ flex: 1 }}><span className="input-label" style={{fontSize: '9px'}}>Z Safe</span><input type="number" value={toolConfig.zSafe} onChange={(e) => handleToolChange('zSafe', e.target.value)} /></div>
                </div>
                <div style={{ display: 'flex', gap: '5px', marginBottom: '15px' }}>
                  <div style={{ flex: 1 }}><span className="input-label" style={{fontSize: '9px'}}>Clearance</span><input type="number" step="0.1" value={toolConfig.clearance !== undefined ? toolConfig.clearance : 2.0} onChange={(e) => handleToolChange('clearance', e.target.value)} /></div>
                  <div style={{ flex: 1 }}></div>
                </div>

                <div className="input-row"><span className="input-label">Output</span></div>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                  <button className="ribbon-btn" onClick={handleExportDXF} disabled={!analysisResult} style={{justifyContent: 'center', background: 'rgba(255,255,255,0.1)'}}>📐 Export DXF (2D)</button>
                  <button className="ribbon-btn primary" onClick={handleExportGCode} disabled={activeStep < 3} style={{justifyContent: 'center'}}>🔥 Post G-Code</button>
                </div>
                  </>
                )}
                {activeModule === 'sketch' && (
                  <div style={{ padding: '10px', color: 'var(--text-muted)' }}>2D Entities Tree will be implemented here.</div>
                )}
                {activeModule === '3d' && (
                  <div style={{ padding: '10px', color: 'var(--text-muted)' }}>3D Model Tree will be implemented here.</div>
                )}
              </div>
            </div>
            <div className="resizer-x" style={{ left: '100%', marginLeft: '-2px' }} onMouseDown={(e) => handleResize(e, 'left')}></div>
          </div>
        )}

        {/* VIEWPORT CENTER */}
        <div className="viewport" style={{ 
          flex: 1,
          position: 'relative', 
          display: 'flex', 
          flexDirection: 'column',
          minWidth: 0,
          minHeight: 0,
          pointerEvents: isResizing ? 'none' : 'auto', 
          zIndex: 1 
        }}>
          
          {/* TOPSOLID CONFIG POPUP */}
          {showCalcConfig && (
            <div style={{
              position: 'absolute', top: 0, left: 0, right: 0, background: 'linear-gradient(180deg, #222 0%, #111 100%)',
              borderBottom: '2px solid #555', boxShadow: '0 4px 10px rgba(0,0,0,0.5)', zIndex: 100, padding: '10px 20px',
              display: 'flex', justifyContent: 'space-between', alignItems: 'center', color: '#fff'
            }}>
               <div style={{display:'flex', gap: '20px', alignItems: 'center'}}>
                 <div style={{fontWeight: 'bold', color: '#88ccff'}}>⚙️ Calculate Holes</div>
                 <div>
                   <label style={{marginRight: '10px', fontSize: '12px'}}>Source:</label>
                   <select value={calcMode} onChange={(e) => setCalcMode(e.target.value)} style={{background: '#333', color: 'white', border: '1px solid #555', padding: '4px 8px', borderRadius: '3px'}}>
                     <option value="3d_only">3D Model (STEP)</option>
                     <option value="dxf_layer">2D DXF (Layer Z-Depth)</option>
                     <option value="dxf_raycast">2D DXF (Raycast to 3D)</option>
                   </select>
                 </div>
                 {calcMode !== '3d_only' && (
                   <div>
                     <input type="file" accept=".dxf" onChange={(e) => setDxfCalcFile(e.target.files[0])} style={{fontSize: '12px'}}/>
                   </div>
                 )}
               </div>
               <div style={{display:'flex', gap: '10px'}}>
                 <button onClick={handleExecuteHoles} style={{background: '#2ecc71', color: '#000', border: 'none', padding: '5px 15px', borderRadius: '3px', cursor: 'pointer', fontWeight: 'bold'}}>✓ Execute</button>
                 <button onClick={() => setShowCalcConfig(false)} style={{background: '#e74c3c', color: '#fff', border: 'none', padding: '5px 15px', borderRadius: '3px', cursor: 'pointer'}}>✕ Cancel</button>
               </div>
            </div>
          )}
        
          {/* FLOATING TOOLBAR */}
          <div className="floating-toolbar">
            <button className={`float-btn ${activeTool === 'select' ? 'active' : ''}`} onClick={() => setActiveTool('select')} title="Select">↖</button>
            <button className={`float-btn ${activeTool === 'move' ? 'active' : ''}`} onClick={() => setActiveTool('move')} title="Move">✋</button>
            <button className={`float-btn ${activeTool === 'copy' ? 'active' : ''}`} onClick={() => setActiveTool('copy')} title="Copy">📄</button>
            <button className={`float-btn ${activeTool === 'dimension' ? 'active' : ''}`} onClick={() => setActiveTool('dimension')} title="Dimension">📏</button>
          </div>
          
          {activeModule === '3d' ? (
            <div style={{ flex: 1, position: 'relative', background: '#0f1115', width: '100%', height: '100%' }}>
              {stepFileName ? (
                <Suspense fallback={<div style={{color:'white', padding: 20}}>Loading 3D Module...</div>}>
                  <ModelPreview3D filename={stepFileName} boundingBox={analysisResult?.boundingBox} />
                </Suspense>
              ) : (
                <div style={{ textAlign: 'center', height: '100%', display: 'flex', flexDirection: 'column', justifyContent: 'center' }}>
                  <h2 style={{ fontSize: '24px', color: 'rgba(255,255,255,0.2)', letterSpacing: '4px' }}>{t('canvas.no_model')}</h2>
                  <p style={{ color: 'var(--text-muted)' }}>Vui lòng nạp file STEP/IGES trước.</p>
                </div>
              )}
            </div>
          ) : (holesData.length > 0 || (edgesData && edgesData.length > 0) || stepFileName) ? (
            <div style={{ flex: 1, position: 'relative', width: '100%', height: '100%', minHeight: 0, minWidth: 0 }}>
              <CADCanvas 
                ref={cadCanvasRef}
                showFrameColor={showFrameColor}
                holesData={holesData}
                setHolesData={setHolesData}
                edgesData={edgesData}
                origin={origin}
                hiddenLayers={hiddenLayers}
                allDepths={allDepths}
                uniqueDepths={uniqueDepths}
                depthColors={depthColors}
                activeTool={activeTool}
                dimensionsData={dimensionsData}
                setDimensionsData={setDimensionsData}
                onMouseMoveWorld={(x,y) => setWorldMousePos({x, y, z: 0})}
                stepFileName={stepFileName}
                show3DLayer={show3DLayer}
                stepBoundingBox={analysisResult?.boundingBox}
              />
            </div>
          ) : (
            <div style={{ textAlign: 'center', flex: 1, display: 'flex', flexDirection: 'column', justifyContent: 'center' }}>
              <h2 style={{ fontSize: '24px', color: 'rgba(255,255,255,0.2)', letterSpacing: '4px' }}>{t('canvas.no_model')}</h2>
            </div>
          )}

          {/* 4. COMMAND LINE (Inside Viewport Column) */}
          {showCmd && activeModule !== '3d' && (
            <>
              <div className="resizer-y" onMouseDown={(e) => handleResize(e, 'y')} style={{ position: 'absolute', bottom: `${cmdHeight}px`, left: 0, right: 0, zIndex: 10 }}></div>
              <div className="command-line" style={{ height: `${cmdHeight}px`, position: 'absolute', bottom: 0, left: 0, right: 0, zIndex: 10 }}>
                <div className="cmd-history">
                  {cmdHistory.map((cmd, i) => (
                    <div key={i}>{cmd}</div>
                  ))}
                </div>
                <div className="cmd-input-row">
                  <span className="cmd-prompt">Command:</span>
                  <span className="cmd-text">{cmdPrompt}</span>
                  <span style={{ animation: 'blink 1s step-end infinite', marginLeft: '2px', backgroundColor: '#fff', width: '6px', height: '12px', display: 'inline-block' }}></span>
                </div>
              </div>
            </>
          )}
        </div>

        {/* DOCK RIGHT: LEVELS MANAGER */}
        {showRight && (
          <div style={{ display: 'flex', position: 'relative', flexShrink: 0 }}>
            <div className="resizer-x" style={{ left: 0, marginLeft: '-2px' }} onMouseDown={(e) => handleResize(e, 'right')}></div>
            <div className="dock-panel right-panel" style={{ width: `${rightWidth}px`, minWidth: `${rightWidth}px`, position: 'relative', boxShadow: '-2px 0 10px rgba(0,0,0,0.5)' }}>
              <div className="dock-header">
                <span>{activeModule === 'sketch' ? t('panels.levels_manager') : activeModule === '3d' ? 'Properties' : 'CAM Parameters'}</span>
                <span className="close-btn" onClick={() => setShowRight(false)}>✕</span>
              </div>
              <div className="dock-content">
                {stepFileName && (
                  <div style={{ fontSize: '11px', color: '#fff', marginBottom: '15px', padding: '5px', background: 'rgba(255,255,255,0.05)', borderLeft: '2px solid var(--accent)' }}>
                    <div style={{ marginBottom: '4px' }}><strong>{t('panels.model')}</strong> {stepFileName}</div>
                    {/* 3D Preview */}
                    <div style={{ width: '100%', height: '140px', background: 'rgba(0,0,0,0.3)', border: '1px solid rgba(255,255,255,0.1)', marginTop: '8px', display: 'flex', alignItems: 'center', justifyContent: 'center', position: 'relative' }}>
                       <Suspense fallback={<div style={{color: 'rgba(255,255,255,0.3)', fontSize: '10px'}}>Loading 3D...</div>}>
                         {stepFileName && <ModelPreview3D filename={stepFileName} boundingBox={analysisResult?.boundingBox} />}
                       </Suspense>
                    </div>
                  </div>
                )}
                
                {analysisResult && analysisResult.mold_health_warnings && analysisResult.mold_health_warnings.length > 0 && (
                  <div style={{ fontSize: '11px', marginBottom: '15px', padding: '5px', background: 'rgba(255, 0, 0, 0.1)', borderLeft: '2px solid #ff3333' }}>
                    <div style={{ color: '#ff3333', fontWeight: 'bold', marginBottom: '4px' }}>⚠️ MOLD HEALTH WARNING</div>
                    <div style={{ color: '#fff' }}>Phát hiện {analysisResult.mold_health_warnings.length} mặt vách đứng (&lt;3°). Nguy cơ kẹt khuôn cao!</div>
                    <ul style={{ paddingLeft: '15px', margin: '4px 0', color: '#ffaaaa' }}>
                      {analysisResult.mold_health_warnings.slice(0, 3).map((w, i) => (
                        <li key={i}>Z:{w.center[2]} ({w.draft_angle}°)</li>
                      ))}
                      {analysisResult.mold_health_warnings.length > 3 && <li>... và {analysisResult.mold_health_warnings.length - 3} lỗi khác</li>}
                    </ul>
                  </div>
                )}

                {analysisResult && analysisResult.chamfers_detected !== undefined && analysisResult.chamfers_detected > 0 && (
                  <div style={{ fontSize: '11px', marginBottom: '15px', padding: '5px', background: 'rgba(52, 152, 219, 0.1)', borderLeft: '2px solid #3498db' }}>
                    <div style={{ color: '#3498db', fontWeight: 'bold', marginBottom: '4px' }}>⚙️ AAG ANALYSIS SITUS</div>
                    <div style={{ color: '#fff' }}>Nhận diện thành công {analysisResult.chamfers_detected} bề mặt Chamfer / Fillet trong B-Rep Topology. Sẵn sàng phay vát mép.</div>
                  </div>
                )}

                {allDepths.length === 0 && (
                  <div style={{ padding: '10px', color: 'var(--text-muted)' }}>{t('panels.no_layers')}</div>
                )}
                <div className="panel-section layers-list" style={{ border: 'none', background: 'transparent', padding: '0' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '10px' }}>
                     <span style={{ fontSize: '11px', fontWeight: 'bold' }}>LAYER MANAGER</span>
                     <button onClick={addLayer} style={{ background: 'transparent', border: '1px solid var(--border-color)', color: '#fff', cursor: 'pointer', borderRadius: '3px', padding: '2px 6px', fontSize: '10px' }}>+ New Layer</button>
                  </div>
                  
                  <div className="layer-table" style={{ fontSize: '11px', width: '100%', border: '1px solid var(--border-color)', borderRadius: '4px', overflow: 'hidden' }}>
                    {stepFileName && (
                      <div style={{ display: 'flex', alignItems: 'center', background: 'rgba(52, 152, 219, 0.2)', padding: '4px 0', borderBottom: '1px solid var(--border-color)' }}>
                        <div style={{ width: '30px', textAlign: 'center', cursor: 'pointer', opacity: show3DLayer ? 1 : 0.3 }} onClick={() => setShow3DLayer(!show3DLayer)}>
                           👁
                        </div>
                        <div style={{ width: '30px', textAlign: 'center' }}>
                           🌟
                        </div>
                        <div style={{ width: '40px', textAlign: 'center', color: '#3498db', fontWeight: 'bold' }}>
                           3D
                        </div>
                        <div style={{ flex: 1, color: '#3498db', fontWeight: 'bold', display: 'flex', alignItems: 'center', gap: '6px' }}>
                           3D Model Overlay
                        </div>
                      </div>
                    )}
                    <div className="layer-header" style={{ display: 'flex', fontWeight: 'bold', background: 'rgba(255,255,255,0.05)', padding: '6px 0', borderBottom: '1px solid var(--border-color)', cursor: 'pointer' }}>
                      <div style={{ width: '30px', textAlign: 'center' }} title="Visibility">👁</div>
                      <div style={{ width: '30px', textAlign: 'center' }} title="Main Layer">★</div>
                      <div style={{ width: '40px', textAlign: 'center' }} onClick={() => handleSort('z')}>
                        Z(mm) {sortConfig.key === 'z' ? (sortConfig.direction === 'asc' ? '▲' : '▼') : ''}
                      </div>
                      <div style={{ flex: 1 }} onClick={() => handleSort('name')}>
                        Name {sortConfig.key === 'name' ? (sortConfig.direction === 'asc' ? '▲' : '▼') : ''}
                      </div>
                      <div style={{ width: '40px', textAlign: 'center' }} onClick={() => handleSort('items')}>
                        Items {sortConfig.key === 'items' ? (sortConfig.direction === 'asc' ? '▲' : '▼') : ''}
                      </div>
                      <div style={{ width: '30px', textAlign: 'center' }}></div>
                    </div>
                    {allDepths.map((depth, idx) => {
                      const color = depthColors[idx % depthColors.length];
                      const layerHoles = holesData.filter(h => h.depth === depth);
                      const layerEdges = (edgesData || []).filter(e => e.depth === depth);
                      const holeCount = layerHoles.length;
                      const edgeCount = layerEdges.reduce((sum, eg) => sum + eg.wires.length, 0);
                      const isHidden = hiddenLayers[`hole-${depth}`] && hiddenLayers[`edge-${depth}`];
                      const totalCount = holeCount + edgeCount;
                      const isMain = activeLayer === depth;
                      
                      // Lấy Z-depth nếu có
                      let zVal = "-";
                      if (layerHoles.length > 0 && layerHoles[0].zDepth !== undefined) zVal = layerHoles[0].zDepth;
                      else if (layerEdges.length > 0 && layerEdges[0].zDepth !== undefined) zVal = layerEdges[0].zDepth;
                      
                      const displayName = depth;
                      
                      return (
                        <div key={depth} style={{ display: 'flex', alignItems: 'center', background: isMain ? 'rgba(0,122,204,0.3)' : (idx % 2 === 0 ? 'transparent' : 'rgba(255,255,255,0.02)'), padding: '4px 0', borderBottom: '1px solid rgba(255,255,255,0.05)' }}>
                          <div style={{ width: '30px', textAlign: 'center', cursor: 'pointer', opacity: isHidden ? 0.3 : 1 }} onClick={() => toggleLayer(depth)}>
                             👁
                          </div>
                          <div style={{ width: '30px', textAlign: 'center', cursor: 'pointer', color: isMain ? '#2ed573' : '#555' }} onClick={() => setActiveLayer(depth)}>
                             ★
                          </div>
                          <div style={{ width: '40px', textAlign: 'center', color: '#ff9f43', fontWeight: 'bold' }}>
                             {zVal}
                          </div>
                          <div style={{ flex: 1, color: '#dcdde1', fontWeight: 'bold', display: 'flex', alignItems: 'center', gap: '6px' }}>
                             <div style={{ width: '10px', height: '10px', backgroundColor: color, borderRadius: '2px' }}></div>
                             <input 
                               value={layerNames[depth] || displayName} 
                               onChange={(e) => setLayerNames(prev => ({...prev, [depth]: e.target.value}))} 
                               style={{ background: 'transparent', border: 'none', color: '#dcdde1', width: '100%', outline: 'none', fontSize: '11px', fontWeight: 'bold' }} 
                             />
                          </div>
                          <div style={{ width: '40px', textAlign: 'center', color: 'var(--text-muted)' }}>{totalCount}</div>
                          <div style={{ width: '30px', textAlign: 'center', cursor: 'pointer', color: '#ff4757', opacity: 0.7 }} onClick={() => deleteLayer(depth)}>✕</div>
                        </div>
                      )
                    })}
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}
        </div>
      </div>

      {/* DOCUMENT TABS */}
      <div className="document-tabs">
        {tabs.map(tab => (
          <div key={tab.id} className={`doc-tab ${tab.id === activeTabId ? 'active' : ''}`} onClick={() => switchTab(tab.id)}>
            {tab.id === activeTabId ? (stepFileName ? stepFileName.replace(/\.[^/.]+$/, "") : tab.name) : tab.name}
            <span className="doc-tab-close" onClick={(e) => handleCloseTab(tab.id, e)}>✕</span>
          </div>
        ))}
        <div className="doc-tab-new" title="New Project" onClick={handleNewProject}>+</div>
      </div>

      {/* 5. STATUS BAR */}
      <div className="status-bar">
        <div className="status-widget">MODEL</div>
        <div className="status-widget">LAYOUT1</div>
        <div className="status-widget active">OSNAP</div>
        <div className="status-widget">ORTHO</div>
        <div className="status-widget">POLAR</div>
        
        <div className="coord-display">
          <span>X: {worldMousePos.x.toFixed(2)}</span>
          <span>Y: {worldMousePos.y.toFixed(2)}</span>
          <span>Z: {worldMousePos.z.toFixed(2)}</span>
        </div>
        <div className={`status-widget ${showFrameColor ? 'active' : ''}`} onClick={() => setShowFrameColor(!showFrameColor)} style={{ marginLeft: '10px', cursor: 'pointer' }} title="Toggle Frame Colors">
          🎨 Frame Color
        </div>
      </div>
    </div>
  );
}

export default App;
