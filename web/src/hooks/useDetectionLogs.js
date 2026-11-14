import { useMemo } from 'react';

export default function useDetectionLogs(logs, detectionResult, currentTime) {
  return useMemo(() => {
    let videoLogs = [];
    const currentStats = {
      total_violations: 0,
      no_helmet_count: 0,
      vehicle_counts: {},
    };

    if (detectionResult?.violations) {
      const filteredViolations = detectionResult.violations.filter(
        (v) => v.time_sec <= currentTime
      );

      currentStats.total_violations = filteredViolations.length;
      filteredViolations.forEach((v) => {
        if (v.vehicle_type === 'no_helmet') {
          currentStats.no_helmet_count += 1;
        } else if (v.vehicle_type) {
          currentStats.vehicle_counts[v.vehicle_type] =
            (currentStats.vehicle_counts[v.vehicle_type] || 0) + 1;
        }
      });

      videoLogs = filteredViolations
        .map((v, idx) => {
          const m = Math.floor(v.time_sec / 60);
          const s = Math.floor(v.time_sec % 60);
          const timeStr = `${m.toString().padStart(2, '0')}:${s
            .toString()
            .padStart(2, '0')}`;
          return {
            id: `v-${idx}`,
            severity: v.severity,
            icon: v.icon,
            title: v.title,
            time: timeStr,
            source: v.source,
          };
        })
        .reverse();
    }

    return {
      combinedLogs: [...videoLogs, ...logs].slice(0, 50),
      dynamicStats: currentStats,
    };
  }, [logs, detectionResult, currentTime]);
}

