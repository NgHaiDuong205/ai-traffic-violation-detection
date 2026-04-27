import React, { useRef, useState, useCallback } from 'react';

function UploadSection({ onFileUpload }) {
  const fileInputRef = useRef(null);
  const [isDragOver, setIsDragOver] = useState(false);

  const handleDragOver = useCallback((e) => {
    e.preventDefault();
    setIsDragOver(true);
  }, []);

  const handleDragLeave = useCallback(() => {
    setIsDragOver(false);
  }, []);

  const handleDrop = useCallback((e) => {
    e.preventDefault();
    setIsDragOver(false);
    if (e.dataTransfer.files.length) {
      onFileUpload(e.dataTransfer.files[0]);
    }
  }, [onFileUpload]);

  const handleClick = () => {
    fileInputRef.current.click();
  };

  const handleChange = (e) => {
    if (e.target.files.length) {
      onFileUpload(e.target.files[0]);
      e.target.value = '';
    }
  };

  return (
    <footer className="upload-section">
      <div
        className={`upload-dropzone ${isDragOver ? 'dragover' : ''}`}
        onClick={handleClick}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
      >
        <input
          type="file"
          ref={fileInputRef}
          accept="image/*,video/*"
          onChange={handleChange}
          hidden
        />
        <div className="upload-inner">
          <span className="upload-cloud-icon"></span>
          <h3>Tải lên ảnh / video để phân tích</h3>
          <p>
            Kéo thả file vào đây, hoặc{' '}
            <span className="browse-link">chọn file</span>
          </p>
          <span className="upload-hint">
            Hỗ trợ MP4, AVI, JPEG, PNG (Tối đa 50MB)
          </span>
        </div>
      </div>
    </footer>
  );
}

export default UploadSection;
