import React, { useState, useCallback, useRef, useEffect } from 'react';
import './App.css';
import ViolationPanel from './components/ViolationPanel';
import DetectionViewer from './components/DetectionViewer';
import UploadSection from './components/UploadSection';

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
  
  const wsRef = useRef(null);

  useEffect(() => {
    return () => {
      if (wsRef.current) wsRef.current.close();
    };
  }, []);

  const handleFileUpload = useCallback(async (file) => {
    if (!file) return;
    const type = file.type.startsWith('video/') ? 'video' : 'image';
    const localUrl = URL.createObjectURL(file);
    setMediaFile(localUrl);
    setMediaType(type);
    setIsDetecting(true);

    setLogs([
      {
        id: Date.now(),
        severity: 'info',
        title: `Đang phân tích: ${file.name}`,
        time: getTimeString(),
        source: 'Hệ thống',
      }
    ]);

    if (type === 'image') {
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
              icon: v.icon,
              title: v.title,
              time: getTimeString(),
              source: v.source
            }));
            setLogs((prev) => [...newLogs, ...prev]);
          } else {
             setLogs((prev) => [{
              id: Date.now() + 999,
              severity: 'info',
              icon: '',
              title: 'Không phát hiện vi phạm mũ bảo hiểm',
              time: getTimeString(),
              source: 'YOLOv8 AI'
            }, ...prev]);
          }
        } else {
          console.error(data.error);
        }
      } catch (err) {
        console.error("API error:", err);
      } finally {
        setIsDetecting(false);
      }
    } else {
      try {
        const formData = new FormData();
        formData.append('file', file);
        
        const response = await fetch('http://localhost:8000/api/upload_video', {
          method: 'POST',
          body: formData,
        });
        
        const data = await response.json();
        
        if (data.success) {
           const filename = data.filename;
           
           if (wsRef.current) wsRef.current.close();
           
           const ws = new WebSocket(`ws://localhost:8000/api/ws/video/${filename}`);
           wsRef.current = ws;
           
           ws.onmessage = (event) => {
              const msg = JSON.parse(event.data);
              if (msg.error) {
                 console.error(msg.error);
                 setIsDetecting(false);
              } else if (msg.status === 'completed') {
                 setIsDetecting(false);
                 ws.close();
              } else if (msg.frame) {
                 setMediaType('image'); 
                 setMediaFile(msg.frame); 
                 
                 setIsDetecting(false);
                 
                 if (msg.violations && msg.violations.length > 0) {
                     const newLogs = msg.violations.map((v, idx) => ({
                          id: Date.now() + idx + Math.random(),
                          severity: v.severity,
                          icon: v.icon,
                          title: v.title,
                          time: getTimeString(),
                          source: v.source
                     }));
                     setLogs((prev) => [...newLogs, ...prev].slice(0, 50)); 
                 }
              }
           };
           
           ws.onclose = () => {
              setIsDetecting(false);
           };
           
           ws.onerror = (err) => {
               console.error("WS error:", err);
               setIsDetecting(false);
           };
           
        } else {
          console.error("Video upload failed:", data.error);
          setIsDetecting(false);
        }
      } catch (err) {
        console.error("Video API error:", err);
        setIsDetecting(false);
      }
    }
  }, []);

  return (
    <div className="app-container">
      {/* Header */}
      <header className="app-header">
        <h1>
          <span className="header-icon">🚦</span>
          SmartTraffic AI
        </h1>
        <span className="status-badge">
          <span className="status-dot"></span>
          Hệ thống hoạt động
        </span>
      </header>

      {/* Main: Left panel + Right panel */}
      <main className="main-content">
        <ViolationPanel logs={logs} />
        <DetectionViewer
          mediaFile={mediaFile}
          mediaType={mediaType}
          isDetecting={isDetecting}
        />
      </main>

      {/* Bottom: Upload */}
      <UploadSection onFileUpload={handleFileUpload} />
    </div>
  );
}

export default App;
