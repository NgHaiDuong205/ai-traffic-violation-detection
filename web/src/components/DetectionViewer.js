import React from 'react';

function DetectionViewer({ mediaFile, mediaType, isDetecting }) {
  return (
    <section className="panel right-panel">
      <div className="panel-header">
        <h2>
          <span className="panel-icon"></span>
          Màn hình phát hiện
        </h2>
      </div>

      <div className="viewer-container">
        {!mediaFile ? (
          <div className="viewer-placeholder">
            <span className="viewer-placeholder-icon"></span>
            <p>Chưa có media.</p>
          </div>
        ) : (
          <>
            {mediaType === 'video' ? (
              <video
                className="uploaded-media"
                src={mediaFile}
                controls
                autoPlay
                muted
                loop
              />
            ) : (
              <img
                className="uploaded-media"
                src={mediaFile}
                alt="Uploaded for detection"
              />
            )}
          </>
        )}

        {isDetecting && (
          <div className="detection-overlay">
            <div className="detection-spinner"></div>
            <p>AI đang phân tích...</p>
          </div>
        )}
      </div>
    </section>
  );
}

export default DetectionViewer;
