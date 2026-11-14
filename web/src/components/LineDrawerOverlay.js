import React, { useState, useRef, useEffect } from 'react';

function LineDrawerOverlay({ image, onConfirm, onCancel }) {
  const [points, setPoints] = useState([]);
  const canvasRef = useRef(null);
  const containerRef = useRef(null);

  const handleCanvasClick = (e) => {
    if (points.length >= 2) return;

    const rect = canvasRef.current.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const y = e.clientY - rect.top;

    const img = new Image();
    img.src = image;
    img.onload = () => {
        const displayedWidth = rect.width;
        const displayedHeight = rect.height;
        const scaleX = img.width / displayedWidth;
        const scaleY = img.height / displayedHeight;
        
        const originalX = Math.round(x * scaleX);
        const originalY = Math.round(y * scaleY);
        
        setPoints([...points, { x: originalX, y: originalY, displayX: x, displayY: y }]);
    };
  };

  const handleReset = () => {
    setPoints([]);
  };

  const handleConfirm = () => {
    if (points.length === 2) {
      onConfirm({
        x1: points[0].x,
        y1: points[0].y,
        x2: points[1].x,
        y2: points[1].y
      });
    }
  };

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    
    // Match canvas internal resolution to its displayed size
    canvas.width = canvas.clientWidth;
    canvas.height = canvas.clientHeight;
    
    const ctx = canvas.getContext('2d');
    ctx.clearRect(0, 0, canvas.width, canvas.height);

    // Draw points and line
    points.forEach((p, i) => {
      ctx.fillStyle = '#4ade80';
      ctx.beginPath();
      ctx.arc(p.displayX, p.displayY, 5, 0, Math.PI * 2);
      ctx.fill();

      if (i === 1) {
        ctx.strokeStyle = '#fff';
        ctx.lineWidth = 3;
        ctx.beginPath();
        ctx.moveTo(points[0].displayX, points[0].displayY);
        ctx.lineTo(points[1].displayX, points[1].displayY);
        ctx.stroke();
      }
    });
  }, [points]);

  return (
    <div className="line-drawer-overlay">
      <div 
        className="line-drawer-canvas" 
        ref={containerRef}
        style={{ backgroundImage: `url(${image})`, position: 'relative' }}
      >
        <canvas 
            ref={canvasRef}
            onClick={handleCanvasClick}
            style={{ width: '100%', height: '100%', display: 'block' }}
        />
      </div>
      <div className="line-drawer-controls">
        <p style={{ color: 'white', marginRight: 'auto', alignSelf: 'center', fontSize: '0.9rem' }}>
          {points.length === 0 ? "📍 Click điểm đầu của vạch kẻ" : 
           points.length === 1 ? "📍 Click điểm cuối của vạch kẻ" : 
           "✅ Đã vẽ vạch kẻ. Nhấn Xác nhận để bắt đầu."}
        </p>
        <button className="btn btn-secondary" onClick={handleReset}>Vẽ lại</button>
        <button className="btn btn-secondary" onClick={onCancel}>Hủy</button>
        <button 
          className="btn btn-primary" 
          disabled={points.length < 2} 
          onClick={handleConfirm}
        >
          Xác nhận & Chạy
        </button>
      </div>
    </div>
  );
}

export default LineDrawerOverlay;
