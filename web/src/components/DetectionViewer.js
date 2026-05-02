import React, { useRef, useState, useEffect, useCallback } from 'react';

function DetectionViewer({ mediaFile, mediaType, isDetecting, progress, stats, detectionResult, lineCoords, onTimeUpdate, children }) {
  const videoRef = useRef(null);
  const containerRef = useRef(null);
  const [currentFrameData, setCurrentFrameData] = useState(null);
  const [overlayTransform, setOverlayTransform] = useState({ scaleX: 1, scaleY: 1, offsetX: 0, offsetY: 0 });

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

  useEffect(() => {
    let animationFrameId;
    const updateOverlay = () => {
      if (videoRef.current && detectionResult && detectionResult.frames) {
         const currentTime = videoRef.current.currentTime;
         let closest = detectionResult.frames[0];
         let minDiff = Infinity;
         for (let frame of detectionResult.frames) {
             const diff = Math.abs(frame.time_sec - currentTime);
             if (diff < minDiff) {
                 minDiff = diff;
                 closest = frame;
             } else if (diff > minDiff) {
                 break;
             }
         }
         setCurrentFrameData(closest);
      }
      animationFrameId = requestAnimationFrame(updateOverlay);
    };
    if (detectionResult && mediaType === 'video') {
        updateOverlay();
    }
    return () => cancelAnimationFrame(animationFrameId);
  }, [detectionResult, mediaType]);

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
                   e.target.playbackRate = 1.0;
                   updateTransform();
                }}
                onTimeUpdate={(e) => {
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
                  
                  const isRed = box.is_violation;
                  const color = isRed ? '#ef4444' : '#22c55e';
                  
                  return (
                    <React.Fragment key={`${box.id}-${idx}`}>
                      <div style={{
                        position: 'absolute',
                        left, top, width, height,
                        border: `2px solid ${color}`,
                        zIndex: 10
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
                        whiteSpace: 'nowrap'
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
                            zIndex: 12
                         }}>
                           VIOLATION!
                         </div>
                      )}
                    </React.Fragment>
                  );
                })}
              </div>
            )}
          </>
        )}



        {/* This allows LineDrawerOverlay to be rendered inside viewer-container */}
        {children}

        {isDetecting && (
          <div className="detection-overlay">
            <div className="detection-spinner"></div>
            <p>AI đang phân tích video...</p>
            <div style={{ width: '60%', background: 'rgba(255,255,255,0.2)', height: '10px', borderRadius: '5px', overflow: 'hidden', marginTop: '10px' }}>
              <div style={{ width: `${progress}%`, height: '100%', background: '#3b82f6', transition: 'width 0.2s' }}></div>
            </div>
            <p style={{ fontSize: '0.8rem', marginTop: '5px' }}>{progress}% hoàn thành</p>
          </div>
        )}
      </div>
    </section>
  );
}

export default DetectionViewer;
