import React, { useState, useCallback, useRef, useEffect } from 'react';
import './App.css';
import ViolationPanel from './components/ViolationPanel';
import DetectionViewer from './components/DetectionViewer';
import UploadSection from './components/UploadSection';
import LineDrawerOverlay from './components/LineDrawerOverlay';

const getTimeString = () => {
  return new Date().toLocaleTimeString([], {
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  });
};


function App() {
  const [logs, setLogs] = useState([]);
  const [mediaFile, setMediaFile] = useState(null);
  const [mediaType, setMediaType] = useState(null);
  const [isDetecting, setIsDetecting] = useState(false);
  const [isDrawingLine, setIsDrawingLine] = useState(false);
  const [firstFrame, setFirstFrame] = useState(null);
  const [videoFilename, setVideoFilename] = useState(null);
  const [stats, setStats] = useState({ total_violations: 0, vehicle_counts: {} });
  const [progress, setProgress] = useState(0);
  const [detectionResult, setDetectionResult] = useState(null);
  const [lineCoords, setLineCoords] = useState(null);
  const [currentTime, setCurrentTime] = useState(0);
  
  const wsRef = useRef(null);

  const { combinedLogs, dynamicStats } = React.useMemo(() => {
      let videoLogs = [];
      let currentStats = {
          total_violations: 0,
          no_helmet_count: 0,
          vehicle_counts: {}
      };

      if (detectionResult && detectionResult.violations) {
          const filteredViolations = detectionResult.violations.filter(v => v.time_sec <= currentTime);
          
          currentStats.total_violations = filteredViolations.length;
          filteredViolations.forEach(v => {
              if (v.vehicle_type === "no_helmet") {
                  currentStats.no_helmet_count++;
              } else if (v.vehicle_type) {
                  currentStats.vehicle_counts[v.vehicle_type] = (currentStats.vehicle_counts[v.vehicle_type] || 0) + 1;
              }
          });

          videoLogs = filteredViolations.map((v, idx) => {
                 const m = Math.floor(v.time_sec / 60);
                 const s = Math.floor(v.time_sec % 60);
                 const timeStr = `${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`;
                 return {
                     id: `v-${idx}`,
                     severity: v.severity,
                     icon: v.icon,
                     title: v.title,
                     time: timeStr, 
                     source: v.source
                 };
             }).reverse();
      }
      return {
          combinedLogs: [...videoLogs, ...logs].slice(0, 50),
          dynamicStats: currentStats
      };
  }, [logs, detectionResult, currentTime]);

  useEffect(() => {
    return () => {
      if (wsRef.current) wsRef.current.close();
    };
  }, []);

  const startDetection = useCallback((lineCoords = null) => {
    if (!videoFilename) return;

    setIsDetecting(true);
    setIsDrawingLine(false);

    if (wsRef.current) wsRef.current.close();
    
    let url = `ws://localhost:8000/api/ws/video/${videoFilename}`;
    if (lineCoords) {
      url += `?line_coords=${encodeURIComponent(JSON.stringify(lineCoords))}`;
    }

    const ws = new WebSocket(url);
    wsRef.current = ws;
    
     ws.onmessage = (event) => {
       const msg = JSON.parse(event.data);
       if (msg.error) {
          console.error(msg.error);
          setIsDetecting(false);
          setProgress(0);
       } else if (msg.status === 'processing') {
          setProgress(msg.progress);
       } else if (msg.status === 'completed') {
          setDetectionResult(msg.result);
          
          if (msg.result.stats) {
             setStats(msg.result.stats);
          }
          
          setIsDetecting(false);
          setProgress(0);
          ws.close();
       }
    };
    
    ws.onclose = () => {
       setIsDetecting(false);
    };
    
    ws.onerror = (err) => {
        console.error("WS error:", err);
        setIsDetecting(false);
    };
  }, [videoFilename]);

  const handleFileUpload = useCallback(async (file) => {
    if (!file) return;
    const type = file.type.startsWith('video/') ? 'video' : 'image';
    const localUrl = URL.createObjectURL(file);
    
    setMediaFile(localUrl);
    setMediaType(type);
    setDetectionResult(null);
    setLineCoords(null);
    setProgress(0);
    setStats({ total_violations: 0, vehicle_counts: {} });
    setLogs([
      {
        id: Date.now(),
        severity: 'info',
        title: `Đang tải lên: ${file.name}`,
        time: getTimeString(),
        source: 'Hệ thống',
      }
    ]);

    if (type === 'image') {
      setIsDetecting(true);
      try {
        const formData = new FormData();
        formData.append('file', file);
        
        const response = await fetch('http://localhost:8000/api/detect', {
          method: 'POST',
          body: formData,
        });
        
        const data = await response.json();
        
        if (data.success) {
          setMediaFile(data.annotated_image);
          
          if (data.violations && data.violations.length > 0) {
            const newLogs = data.violations.map((v, idx) => ({
              id: Date.now() + idx + 1,
              severity: v.severity,
              icon: v.icon || '⚠️',
              title: v.title,
              time: getTimeString(),
              source: v.source
            }));
            setLogs((prev) => [...newLogs, ...prev]);
          } else {
             setLogs((prev) => [{
              id: Date.now() + 999,
              severity: 'info',
              icon: '✅',
              title: 'Không phát hiện vi phạm',
              time: getTimeString(),
              source: 'AI'
            }, ...prev]);
          }
        }
      } catch (err) {
        console.error("API error:", err);
      } finally {
        setIsDetecting(false);
      }
    } else {
      // Video Flow
      try {
        const formData = new FormData();
        formData.append('file', file);
        
        const uploadRes = await fetch('http://localhost:8000/api/upload_video', {
          method: 'POST',
          body: formData,
        });
        
        const uploadData = await uploadRes.json();
        
        if (uploadData.success) {
           const filename = uploadData.filename;
           setVideoFilename(filename);
           
           // Fetch first frame for line drawing
           const frameRes = await fetch(`http://localhost:8000/api/video_first_frame/${filename}`);
           const frameData = await frameRes.json();
           
           if (frameData.frame) {
              setFirstFrame(frameData.frame);
              setIsDrawingLine(true);
           } else {
              // Fallback to direct detection if frame fetch fails
              startDetection();
           }
        }
      } catch (err) {
        console.error("Video error:", err);
      }
    }
  }, [startDetection]);

  return (
    <div className="app-container">
      {/* Header */}
      <header className="app-header">
        <h1>
          <span className="header-icon">🚦</span>
          SmartTraffic AI
        </h1>
        <div style={{ display: 'flex', gap: '1rem', alignItems: 'center' }}>
            <span className="status-badge">
            <span className="status-dot"></span>
            Hệ thống hoạt động
            </span>
        </div>
      </header>

      {/* Main: Left violations panel + Right viewer panel */}
      <main className="main-content">
        <ViolationPanel logs={combinedLogs} />
        <DetectionViewer
          mediaFile={mediaFile}
          mediaType={mediaType}
          isDetecting={isDetecting}
          progress={progress}
          stats={mediaType === 'video' ? dynamicStats : stats}
          detectionResult={detectionResult}
          lineCoords={lineCoords}
          onTimeUpdate={(time) => setCurrentTime(time)}
        >
          {isDrawingLine && (
            <LineDrawerOverlay 
              image={firstFrame} 
              onConfirm={(coords) => {
                setLineCoords(coords);
                startDetection(coords);
              }}
              onCancel={() => {
                setIsDrawingLine(false);
                // Do NOT start detection if cancelled. Must draw 2 points.
              }}
            />
          )}
        </DetectionViewer>
      </main>

      {/* Bottom: Upload */}
      <UploadSection onFileUpload={handleFileUpload} />
    </div>
  );
}

export default App;
