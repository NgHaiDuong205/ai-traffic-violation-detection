import React from 'react';

function ViolationPanel({ logs }) {
  const handleDownloadCSV = () => {
    if (!logs || logs.length === 0) return;

    const headers = ['Thời gian', 'Tiêu đề', 'Mức độ', 'Nguồn'];
    
    const rows = logs.map(log => {
      // Ensure values are strings and escape quotes for CSV format
      const time = `"${String(log.time || '').replace(/"/g, '""')}"`;
      const title = `"${String(log.title || '').replace(/"/g, '""')}"`;
      const severity = `"${String(log.severity || '').replace(/"/g, '""')}"`;
      const source = `"${String(log.source || '').replace(/"/g, '""')}"`;
      return [time, title, severity, source].join(',');
    });

    const csvContent = "\uFEFF" + [headers.join(','), ...rows].join('\n');
    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    
    const link = document.createElement("a");
    link.setAttribute("href", url);
    link.setAttribute("download", "danh_sach_vi_pham.csv");
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  };

  return (
    <section className="panel violations-panel">
      <div className="panel-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <h2>
            <span className="panel-icon">🚨</span>
            Ghi nhận vi phạm
          </h2>
          {logs.length > 0 && (
            <span className="log-count-badge">{logs.length}</span>
          )}
        </div>
        
        {logs.length > 0 && (
          <button 
            onClick={handleDownloadCSV}
            style={{
              padding: '6px 12px',
              backgroundColor: '#10b981',
              color: 'white',
              border: 'none',
              borderRadius: '6px',
              cursor: 'pointer',
              fontSize: '0.85rem',
              fontWeight: 'bold',
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
              boxShadow: '0 2px 4px rgba(0,0,0,0.2)',
              transition: 'background-color 0.2s'
            }}
            onMouseOver={(e) => e.currentTarget.style.backgroundColor = '#059669'}
            onMouseOut={(e) => e.currentTarget.style.backgroundColor = '#10b981'}
          >
            <span>📥</span> Tải CSV
          </button>
        )}
      </div>

      <div className="log-list">
        {logs.length === 0 ? (
          <div className="log-empty">
            <span className="log-empty-icon">📭</span>
            <p>Chưa có dữ liệu.<br />Hãy tải lên ảnh hoặc video.</p>
          </div>
        ) : (
          logs.map((log) => (
            <div className="log-card" key={log.id}>
              <div className={`log-icon-circle ${log.severity}`}>
                <span>{log.icon}</span>
              </div>
              <div className="log-details">
                <span className="log-title">{log.title}</span>
                <span className="log-time">{log.time} — {log.source}</span>
              </div>
              <span className={`log-severity-tag ${log.severity}`}>
                {log.severity === 'critical' && 'Nghiêm trọng'}
                {log.severity === 'high' && 'Cao'}
                {log.severity === 'medium' && 'Trung bình'}
                {log.severity === 'info' && 'Thông tin'}
              </span>
            </div>
          ))
        )}
      </div>
    </section>
  );
}

export default ViolationPanel;
