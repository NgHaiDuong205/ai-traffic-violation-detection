import React, { useRef, useState, useEffect, useCallback } from 'react';

function DetectionViewer({ mediaFile, mediaType, isDetecting, isProcessing, progress, stats, detectionResult, lineCoords, onTimeUpdate, children }) {
  const videoRef = useRef(null);
  const containerRef = useRef(null);
  const [currentFrameData, setCurrentFrameData] = useState(null);
  const [overlayTransform, setOverlayTransform] = useState({ scaleX: 1, scaleY: 1, offsetX: 0, offsetY: 0 });
  const [videoDuration, setVideoDuration] = useState(0);
  const [currentPlaybackTime, setCurrentPlaybackTime] = useState(0);

  // ✅ Debug states
  useEffect(() => {
    console.log('📺 DetectionViewer states:', {
      mediaFile: mediaFile ? 'exists' : 'null',
      mediaType,
      isDetecting,
      isProcessing,
      hasChildren: !!children
    });
  }, [mediaFile, mediaType, isDetecting, isProcessing, children]);

  const updateTransform = useCallback(() => {
      if (!videoRef.current || !containerRef.current) return;
      const v = videoRef.current;
      if (!v.videoWidth) return;
      const videoRatio = v.videoWidth / v.videoHeight;
      const elementRatio = v.clientWidth / v.clientHeight;
      let renderWidth, renderHeight, offsetX = 0, offsetY = 0;
      if (elementRatio > videoRatio) {
        renderHeight = v.clientHeight;
        renderWidth = v.clientHeight * videoRatio;
        offsetX = (v.clientWidth - renderWidth) / 2;
      } else {
        renderWidth = v.clientWidth;
        renderHeight = v.clientWidth / videoRatio;
        offsetY = (v.clientHeight - renderHeight) / 2;
      }
      setOverlayTransform({
          scaleX: renderWidth / v.videoWidth,
          scaleY: renderHeight / v.videoHeight,
          offsetX,
          offsetY
      });
  }, []);

  useEffect(() => {
      window.addEventListener('resize', updateTransform);
      return () => window.removeEventListener('resize', updateTransform);
  }, [updateTransform]);

  const findClosestFrame = useCallback((frames, currentTime) => {
    if (!frames?.length) return null;
    let lo = 0;
    let hi = frames.length - 1;
    let closest = frames[0];
    while (lo <= hi) {
      const mid = (lo + hi) >> 1;
      const diff = frames[mid].time_sec - currentTime;
      if (Math.abs(diff) < Math.abs(closest.time_sec - currentTime)) {
        closest = frames[mid];
      }
      if (diff < 0) lo = mid + 1;
      else hi = mid - 1;
    }
    return closest;
  }, []);

  const updateOverlayAtTime = useCallback((currentTime) => {
    const closest = findClosestFrame(detectionResult?.frames, currentTime);
    setCurrentFrameData(closest);
  }, [detectionResult, findClosestFrame]);

  useEffect(() => {
    if (mediaType !== 'video' || !detectionResult?.frames?.length) {
      setCurrentFrameData(null);
      return;
    }
    updateOverlayAtTime(videoRef.current?.currentTime || 0);
  }, [detectionResult, mediaType, updateOverlayAtTime]);

  const maxProcessedTime = detectionResult?.frames?.length 
      ? detectionResult.frames[detectionResult.frames.length - 1].time_sec 
      : 0;

  const isWaitingForAI = isProcessing && mediaType === 'video' && (currentPlaybackTime > maxProcessedTime + 0.5);

  const trafficLight = currentFrameData 
      ? { state: currentFrameData.light_state, time: currentFrameData.time_left } 
      : null;

  return (
    <section className="panel viewer-panel">
      <div className="panel-header" style={{ display: 'flex', justifyContent: 'space-between', flexWrap: 'wrap', gap: '1rem' }}>
        <h2>
          <span className="panel-icon">📺</span>
          Màn hình phát hiện
        </h2>
        
        <div style={{ display: 'flex', gap: '1.5rem', alignItems: 'center' }}>
            {isProcessing && maxProcessedTime > 0 && (
               <div style={{
                 display: 'flex',
                 alignItems: 'center',
                 gap: '0.6rem',
                 background: 'rgba(59, 130, 246, 0.15)',
                 padding: '0.4rem 1rem',
                 borderRadius: '8px',
                 border: '1px solid rgba(59, 130, 246, 0.35)',
                 boxShadow: '0 0 10px rgba(59, 130, 246, 0.1)'
               }}>
                 <span className="status-dot" style={{ backgroundColor: '#60a5fa', animation: 'blink 1.5s infinite', margin: 0 }}></span>
                 <span style={{ fontSize: '0.75rem', color: '#93c5fd', fontWeight: 'bold', textTransform: 'uppercase', letterSpacing: '0.5px' }}>
                   AI đã xử lý
                 </span>
                 <span style={{ fontFamily: 'monospace', fontWeight: 'bold', fontSize: '1.1rem', color: 'white' }}>
                   {maxProcessedTime.toFixed(1)}s
                 </span>
                 {videoDuration > 0 && (
                   <span style={{ fontSize: '0.75rem', color: '#94a3b8' }}>
                     / {videoDuration.toFixed(1)}s
                   </span>
                 )}
               </div>
            )}

            {trafficLight && trafficLight.state !== 'unknown' && (
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', background: 'rgba(0,0,0,0.4)', padding: '0.4rem 1rem', borderRadius: '8px', border: '1px solid rgba(255,255,255,0.1)' }}>
                <span style={{ fontSize: '0.85rem', color: '#ccc', fontWeight: '600' }}>TÍN HIỆU:</span>
                <div className={`light-bulb ${trafficLight.state}`} style={{ width: '24px', height: '24px', borderWidth: '1px' }}></div>
                <span style={{ fontFamily: 'monospace', fontWeight: 'bold', fontSize: '1.2rem', color: trafficLight.state === 'red' ? '#ef4444' : '#22c55e', width: '30px', textAlign: 'right' }}>
                  {trafficLight.time}s
                </span>
              </div>
            )}
            
            {stats && stats.total_violations !== undefined && (
               <div style={{ display: 'flex', alignItems: 'center', gap: '1rem', background: 'rgba(239, 68, 68, 0.1)', padding: '0.4rem 1rem', borderRadius: '8px', border: '1px solid rgba(239, 68, 68, 0.3)' }}>
                 <div style={{ display: 'flex', flexDirection: 'column' }}>
                    <span style={{ fontSize: '0.75rem', color: '#ef4444', fontWeight: 'bold', textTransform: 'uppercase' }}>Tổng vi phạm</span>
                    <span style={{ fontSize: '1.2rem', fontWeight: 'bold', color: 'white', lineHeight: '1' }}>{stats.total_violations}</span>
                 </div>
                 
                 {stats.no_helmet_count !== undefined && (
                   <div style={{ display: 'flex', flexDirection: 'column', borderLeft: '1px solid rgba(255,255,255,0.2)', paddingLeft: '1rem' }}>
                      <span style={{ fontSize: '0.75rem', color: '#fbbf24', fontWeight: 'bold', textTransform: 'uppercase' }}>Không MBH</span>
                      <span style={{ fontSize: '1.2rem', fontWeight: 'bold', color: 'white', lineHeight: '1' }}>{stats.no_helmet_count}</span>
                   </div>
                 )}
                 
                 {Object.keys(stats.vehicle_counts).length > 0 && (
                   <div style={{ display: 'flex', gap: '0.75rem', borderLeft: '1px solid rgba(255,255,255,0.2)', paddingLeft: '1rem' }}>
                      {Object.entries(stats.vehicle_counts).map(([type, count]) => (
                         <div key={type} style={{ display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
                           <span style={{ fontSize: '0.7rem', color: '#aaa', textTransform: 'capitalize' }}>{type}</span>
                           <span style={{ fontSize: '0.9rem', fontWeight: 'bold', color: 'white' }}>{count}</span>
                         </div>
                      ))}
                   </div>
                 )}
               </div>
            )}
        </div>
      </div>

      <div className="viewer-container" ref={containerRef} style={{ position: 'relative' }}>
        {!mediaFile ? (
          <div className="viewer-placeholder">
            <span className="viewer-placeholder-icon">📷</span>
            <p>Chưa có media. Hãy tải lên ảnh hoặc video để bắt đầu phân tích.</p>
          </div>
        ) : (
          <>
            {mediaType === 'video' ? (
              <video
                ref={videoRef}
                className="uploaded-media"
                src={mediaFile}
                controls
                autoPlay
                muted
                onLoadedMetadata={(e) => {
                   e.target.playbackRate = 0.5; // Giảm tốc độ phát chậm lại
                   setVideoDuration(e.target.duration || 0);
                   updateTransform();
                   updateOverlayAtTime(e.target.currentTime || 0);
                }}
                onTimeUpdate={(e) => {
                   setCurrentPlaybackTime(e.target.currentTime);
                   updateOverlayAtTime(e.target.currentTime);
                   if (onTimeUpdate) onTimeUpdate(e.target.currentTime);
                }}
                onEnded={() => {
                  // Ensure video stops and doesn't loop
                }}
                style={{ width: '100%', height: '100%', objectFit: 'contain' }}
              />
            ) : (
              <img
                className="uploaded-media"
                src={mediaFile}
                alt="Uploaded for detection"
                style={{ width: '100%', height: '100%', objectFit: 'contain' }}
              />
            )}
            
            {/* Overlay bounding boxes */}
            {currentFrameData && currentFrameData.bboxes && mediaType === 'video' && (
              <div style={{ position: 'absolute', inset: 0, pointerEvents: 'none', overflow: 'hidden' }}>
                {/* Draw Line */}
                {lineCoords && (
                  <svg style={{ position: 'absolute', inset: 0, width: '100%', height: '100%' }}>
                    <line 
                      x1={overlayTransform.offsetX + lineCoords.x1 * overlayTransform.scaleX} 
                      y1={overlayTransform.offsetY + lineCoords.y1 * overlayTransform.scaleY} 
                      x2={overlayTransform.offsetX + lineCoords.x2 * overlayTransform.scaleX} 
                      y2={overlayTransform.offsetY + lineCoords.y2 * overlayTransform.scaleY} 
                      stroke={trafficLight && trafficLight.state === 'red' ? '#ef4444' : '#ffffff'} 
                      strokeWidth="3" 
                    />
                  </svg>
                )}

                {/* Draw BBoxes */}
                {currentFrameData.bboxes.map((box, idx) => {
                  const left = overlayTransform.offsetX + box.bbox[0] * overlayTransform.scaleX;
                  const top = overlayTransform.offsetY + box.bbox[1] * overlayTransform.scaleY;
                  const width = (box.bbox[2] - box.bbox[0]) * overlayTransform.scaleX;
                  const height = (box.bbox[3] - box.bbox[1]) * overlayTransform.scaleY;
                  
                  let color = '#22c55e'; // Xanh lá mặc định cho xe/mũ hợp lệ
                  if (box.is_violation) {
                    color = box.type === 'helmet' ? '#3b82f6' : '#ef4444'; // Xanh nước biển cho Không MBH, Đỏ cho Vượt đèn đỏ
                  }
                  
                  // Use combination of type and id as the key for stable elements, enabling smooth transition
                  const uniqueKey = box.id ? `${box.type}-${box.id}` : `box-${idx}`;
                  
                  return (
                    <React.Fragment key={uniqueKey}>
                      <div style={{
                        position: 'absolute',
                        left, top, width, height,
                        border: `2px solid ${color}`,
                        zIndex: 10,
                        transition: 'left 0.15s cubic-bezier(0.1, 0.8, 0.2, 1), top 0.15s cubic-bezier(0.1, 0.8, 0.2, 1), width 0.15s cubic-bezier(0.1, 0.8, 0.2, 1), height 0.15s cubic-bezier(0.1, 0.8, 0.2, 1), border-color 0.2s ease',
                      }} />
                      <div style={{
                        position: 'absolute',
                        left, top: top - 20,
                        background: color,
                        color: 'white',
                        fontSize: '12px',
                        fontWeight: 'bold',
                        padding: '2px 6px',
                        borderRadius: '4px 4px 0 0',
                        zIndex: 11,
                        whiteSpace: 'nowrap',
                        transition: 'left 0.15s cubic-bezier(0.1, 0.8, 0.2, 1), top 0.15s cubic-bezier(0.1, 0.8, 0.2, 1), background-color 0.2s ease',
                      }}>
                        {box.class_name} #{box.id} {box.conf ? `(${Math.round(box.conf * 100)}%)` : ''}
                      </div>
                      {box.just_violated && (
                         <div style={{
                            position: 'absolute',
                            left, top: top + height + 5,
                            color: '#ef4444',
                            fontSize: '16px',
                            fontWeight: 'bold',
                            textShadow: '1px 1px 2px black',
                            zIndex: 12,
                            transition: 'left 0.15s cubic-bezier(0.1, 0.8, 0.2, 1), top 0.15s cubic-bezier(0.1, 0.8, 0.2, 1)',
                         }}>
                           VIOLATION!
                         </div>
                      )}
                    </React.Fragment>
                  );
                })}
              </div>
            )}

            {/* Subtle alert overlay if user seeks past the processed AI timeline */}
            {isWaitingForAI && (
              <div style={{
                position: 'absolute',
                top: '20px',
                left: '50%',
                transform: 'translateX(-50%)',
                background: 'rgba(30, 41, 59, 0.85)',
                backdropFilter: 'blur(8px)',
                border: '1px solid rgba(234, 179, 8, 0.3)',
                color: '#fef08a',
                padding: '0.5rem 1.2rem',
                borderRadius: '20px',
                fontSize: '0.85rem',
                fontWeight: '600',
                display: 'flex',
                alignItems: 'center',
                gap: '0.5rem',
                boxShadow: '0 4px 15px rgba(0,0,0,0.5)',
                zIndex: 15,
                pointerEvents: 'none',
                animation: 'fadeInOverlay 0.2s ease'
              }}>
                <span style={{ animation: 'blink 1.5s infinite' }}>⏳</span>
                AI đang phân tích đoạn này, vui lòng đợi...
              </div>
            )}
          </>
        )}

        {/* This allows LineDrawerOverlay to be rendered inside viewer-container */}
        {children}

        {/* ✅ Chỉ block UI khi đang vẽ line hoặc xử lý ảnh */}
        {isDetecting && (
          <div className="detection-overlay">
            <div className="detection-spinner"></div>
            <p>AI đang phân tích ảnh...</p>
            <div style={{ width: '60%', background: 'rgba(255,255,255,0.2)', height: '10px', borderRadius: '5px', overflow: 'hidden', marginTop: '10px' }}>
              <div style={{ width: `${progress}%`, height: '100%', background: '#3b82f6', transition: 'width 0.2s' }}></div>
            </div>
            <p style={{ fontSize: '0.8rem', marginTop: '5px' }}>{progress}% hoàn thành</p>
          </div>
        )}

        {/* ✅ Progress indicator nhỏ ở góc khi xử lý video */}
        {isProcessing && mediaType === 'video' && (
          <div className="processing-indicator">
            <div className="processing-header">
              <span className="processing-icon">⚙️</span>
              <span className="processing-text">Đang phân tích video</span>
            </div>
            <div className="progress-bar-container">
              <div className="progress-bar" style={{ width: `${progress}%` }}></div>
            </div>
            <span className="progress-percentage">{progress}%</span>
          </div>
        )}
      </div>
    </section>
  );
}

export default DetectionViewer;
