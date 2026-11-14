import { useCallback, useEffect, useRef, useState } from 'react';
import { API_BASE_URL, WS_BASE_URL } from '../config';

const getTimeString = () =>
  new Date().toLocaleTimeString([], {
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  });

export default function useVideoDetectionBackend() {
  const [logs, setLogs] = useState([]);
  const [mediaFile, setMediaFile] = useState(null);
  const [mediaType, setMediaType] = useState(null);
  const [isDetecting, setIsDetecting] = useState(false);
  const [isProcessing, setIsProcessing] = useState(false); // ← Thêm state mới
  const [isDrawingLine, setIsDrawingLine] = useState(false);
  const [firstFrame, setFirstFrame] = useState(null);
  const [videoFilename, setVideoFilename] = useState(null);
  const [stats, setStats] = useState({ total_violations: 0, vehicle_counts: {} });
  const [progress, setProgress] = useState(0);
  const [detectionResult, setDetectionResult] = useState(null);
  const [lineCoords, setLineCoords] = useState(null);

  const wsRef = useRef(null);

  useEffect(() => {
    return () => {
      if (wsRef.current) wsRef.current.close();
    };
  }, []);

  const startDetection = useCallback(
    (coords = null) => {
      if (!videoFilename) return;

      console.log('🚀 startDetection called', { 
        videoFilename, 
        coords, 
        isDrawingLine: false 
      });

      // ✅ Không block UI, chỉ đánh dấu đang xử lý background
      setIsProcessing(true);
      setIsDrawingLine(false);
      setDetectionResult({ frames: [], violations: [] });

      if (wsRef.current) wsRef.current.close();

      let url = `${WS_BASE_URL}/api/ws/video/${videoFilename}`;
      if (coords) {
        url += `?line_coords=${encodeURIComponent(JSON.stringify(coords))}`;
      }

      const ws = new WebSocket(url);
      wsRef.current = ws;

      ws.onmessage = (event) => {
        const msg = JSON.parse(event.data);
        if (msg.error) {
          console.error(msg.error);
          setIsProcessing(false);
          setProgress(0);
        } else if (msg.status === 'processing') {
          setProgress(msg.progress);
        } else if (msg.status === 'frame_batch') {
          // ✅ Cập nhật overlay ngay khi nhận data
          setDetectionResult((prev) => ({
            frames: [...(prev?.frames || []), ...(msg.frames || [])],
            violations: msg.violations || prev?.violations || [],
          }));
        } else if (msg.status === 'completed') {
          setDetectionResult((prev) => ({
            frames: prev?.frames || [],
            violations: msg.result.violations || [],
            stats: msg.result.stats,
          }));

          if (msg.result.stats) {
            setStats(msg.result.stats);
          }

          // ✅ Chỉ tắt processing indicator, không block UI
          setIsProcessing(false);
          setProgress(0);
          ws.close();
        }
      };

      ws.onclose = () => {
        setIsProcessing(false);
      };

      ws.onerror = (err) => {
        console.error('WS error:', err);
        setIsProcessing(false);
      };
    },
    [videoFilename]
  );

  const handleFileUpload = useCallback(
    async (file) => {
      if (!file) return;

      const type = file.type.startsWith('video/') ? 'video' : 'image';
      const localUrl = URL.createObjectURL(file);

      setMediaFile(localUrl);
      setMediaType(type);
      setDetectionResult(null);
      setLineCoords(null);
      setProgress(0);
      setStats({ total_violations: 0, vehicle_counts: {} });
      
      // ✅ Reset tất cả states
      setIsDetecting(false);
      setIsProcessing(false);
      
      setLogs([
        {
          id: Date.now(),
          severity: 'info',
          title: `Đang tải lên: ${file.name}`,
          time: getTimeString(),
          source: 'Hệ thống',
        },
      ]);

      if (type === 'image') {
        setIsDetecting(true); // ← Chỉ block UI cho ảnh
        try {
          const formData = new FormData();
          formData.append('file', file);

          const response = await fetch(`${API_BASE_URL}/api/detect`, {
            method: 'POST',
            body: formData,
          });
          const data = await response.json();

          if (data.success) {
            setMediaFile(data.annotated_image);

            if (data.violations?.length > 0) {
              const newLogs = data.violations.map((v, idx) => ({
                id: Date.now() + idx + 1,
                severity: v.severity,
                icon: v.icon || '⚠️',
                title: v.title,
                time: getTimeString(),
                source: v.source,
              }));
              setLogs((prev) => [...newLogs, ...prev]);
            } else {
              setLogs((prev) => [
                {
                  id: Date.now() + 999,
                  severity: 'info',
                  icon: '✅',
                  title: 'Không phát hiện vi phạm',
                  time: getTimeString(),
                  source: 'AI',
                },
                ...prev,
              ]);
            }
          }
        } catch (err) {
          console.error('API error:', err);
        } finally {
          setIsDetecting(false);
        }
        return;
      }

      try {
        console.log('📤 Uploading video...');
        const formData = new FormData();
        formData.append('file', file);

        const uploadRes = await fetch(`${API_BASE_URL}/api/upload_video`, {
          method: 'POST',
          body: formData,
        });
        const uploadData = await uploadRes.json();
        console.log('✅ Upload response:', uploadData);

        if (uploadData.success) {
          const filename = uploadData.filename;
          setVideoFilename(filename);

          console.log('🎬 Fetching first frame...');
          const frameRes = await fetch(
            `${API_BASE_URL}/api/video_first_frame/${filename}`
          );
          const frameData = await frameRes.json();
          console.log('✅ First frame response:', frameData ? 'exists' : 'null');

          if (frameData.frame) {
            setFirstFrame(frameData.frame);
            setIsDrawingLine(true);
            console.log('✏️ Drawing line mode activated');
          } else {
            console.log('⚠️ No first frame, starting detection directly');
            startDetection();
          }
        }
      } catch (err) {
        console.error('❌ Video error:', err);
      }
    },
    [startDetection]
  );

  const confirmLine = useCallback(
    (coords) => {
      console.log('✅ confirmLine called with coords:', coords);
      setLineCoords(coords);
      setIsDrawingLine(false); // ← Đảm bảo tắt drawing mode
      startDetection(coords);
    },
    [startDetection]
  );

  const cancelLine = useCallback(() => {
    console.log('❌ cancelLine called');
    setIsDrawingLine(false);
    setMediaFile(null); // ← Reset video
    setVideoFilename(null);
  }, []);

  return {
    logs,
    mediaFile,
    mediaType,
    isDetecting,
    isProcessing, // ← Export state mới
    isDrawingLine,
    firstFrame,
    stats,
    progress,
    detectionResult,
    lineCoords,
    handleFileUpload,
    confirmLine,
    cancelLine,
  };
}

