import React, { useState } from 'react';
import './App.css';
import ViolationPanel from './components/ViolationPanel';
import DetectionViewer from './components/DetectionViewer';
import UploadSection from './components/UploadSection';
import LineDrawerOverlay from './components/LineDrawerOverlay';
import useVideoDetectionBackend from './hooks/useVideoDetectionBackend';
import useDetectionLogs from './hooks/useDetectionLogs';

function App() {
  const [currentTime, setCurrentTime] = useState(0);
  const {
    logs,
    mediaFile,
    mediaType,
    isDetecting,
    isDrawingLine,
    firstFrame,
    stats,
    progress,
    detectionResult,
    lineCoords,
    handleFileUpload,
    confirmLine,
    cancelLine,
  } = useVideoDetectionBackend();

  const { combinedLogs, dynamicStats } = useDetectionLogs(
    logs,
    detectionResult,
    currentTime
  );

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
              onConfirm={confirmLine}
              onCancel={cancelLine}
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
