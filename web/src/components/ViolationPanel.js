import React from 'react';

function ViolationPanel({ logs }) {
  return (
    <section className="panel left-panel">
      <div className="panel-header">
        <h2>
          <span className="panel-icon"></span>
          Ghi nhận vi phạm
        </h2>
        {logs.length > 0 && (
          <span className="log-count-badge">{logs.length}</span>
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
