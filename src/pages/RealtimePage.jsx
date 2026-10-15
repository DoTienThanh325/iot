import React, { useEffect, useState } from 'react';
import { Box, Grid } from '@mui/material';
import useEmergencyStore from '../store/useEmergencyStore';
import useRealtimeSocket from '../hooks/useRealtimeSocket';
import vitalsApi from '../api/vitalsApi';

import VitalStatCards from '../components/realtime/VitalStatCards';
import EcgWaveformCanvas from '../components/realtime/EcgWaveformCanvas';
import BpmSpo2LiveChart from '../components/realtime/BpmSpo2LiveChart';
import AiDiagnosticPanel from '../components/realtime/AiDiagnosticPanel';
import CriticalAlertOverlay from '../components/realtime/CriticalAlertOverlay';

export const RealtimePage = () => {
  const selectedDeviceId = useEmergencyStore((state) => state.selectedDeviceId);
  const [initialVitals, setInitialVitals] = useState([]);

  // Nạp 60 giây dữ liệu gần nhất từ REST API khi vừa mở trang hoặc đổi thiết bị
  useEffect(() => {
    let isMounted = true;
    const fetchInitial = async () => {
      try {
        const data = await vitalsApi.fetchInitialVitals(selectedDeviceId, 60);
        if (isMounted && Array.isArray(data) && data.length > 0) {
          setInitialVitals(data);
        }
      } catch (err) {
        console.warn('Could not load initial vitals from REST API:', err.message);
      }
    };
    fetchInitial();
    return () => {
      isMounted = false;
    };
  }, [selectedDeviceId]);

  // Kết nối luồng WebSocket trực tiếp
  const {
    latestVitals,
    liveVitalsHistory,
    aiAnalysis,
    ecgBufferRef,
  } = useRealtimeSocket(selectedDeviceId, initialVitals);

  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2.5 }}>
      {/* 1. Hàng 1 — Cụm Thẻ Chỉ Số Sinh Tồn Cỡ Lớn */}
      <VitalStatCards vitals={latestVitals} />

      {/* 2. Hàng 2 — Phân khu Giám Sát Thời Gian Thực & Khối AI */}
      <Grid container spacing={2.5}>
        {/* Cột Trái (65% width) — Cụm Biểu Đồ Sóng ECG & Đường Sinh Hiệu */}
        <Grid item xs={12} lg={8}>
          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2.5 }}>
            {/* Đồ thị dạng sóng ECG 125Hz trên Canvas 60 FPS */}
            <EcgWaveformCanvas ecgBufferRef={ecgBufferRef} />

            {/* Biểu đồ đường kép BPM & SpO2 trượt 60 giây */}
            <BpmSpo2LiveChart data={liveVitalsHistory} />
          </Box>
        </Grid>

        {/* Cột Phải (35% width) — Bảng Điều Khiển Kết Quả AI & Demo Tool */}
        <Grid item xs={12} lg={4}>
          <AiDiagnosticPanel aiResult={aiAnalysis} />
        </Grid>
      </Grid>

      {/* 3. Lớp Phủ Khẩn Cấp — Cảnh Báo Đỏ Toàn Màn Hình & Còi Báo Động */}
      <CriticalAlertOverlay />
    </Box>
  );
};

export default RealtimePage;
