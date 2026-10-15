import React, { useState, useEffect, useCallback } from 'react';
import { Box, Alert, Snackbar } from '@mui/material';
import useEmergencyStore from '../store/useEmergencyStore';
import vitalsApi from '../api/vitalsApi';

import HistoryFilterBar from '../components/history/HistoryFilterBar';
import HistoryTrendChart from '../components/history/HistoryTrendChart';
import AlertsAndAiTable from '../components/history/AlertsAndAiTable';

export const HistoryPage = () => {
  const selectedDeviceId = useEmergencyStore((state) => state.selectedDeviceId);

  const [timePreset, setTimePreset] = useState('1h');
  const [isLoading, setIsLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState(null);

  const [vitalsHistory, setVitalsHistory] = useState([]);
  const [ecgRecords, setEcgRecords] = useState([]);
  const [alertsList, setAlertsList] = useState([]);
  const [aiResultsList, setAiResultsList] = useState([]);

  // Chuyển đổi preset thời gian thành start_ts (Unix timestamp in seconds)
  const calculateStartTs = (preset) => {
    const nowSec = Math.floor(Date.now() / 1000);
    switch (preset) {
      case '15m':
        return nowSec - 15 * 60;
      case '1h':
        return nowSec - 60 * 60;
      case '6h':
        return nowSec - 6 * 3600;
      case '24h':
        return nowSec - 24 * 3600;
      default:
        return nowSec - 3600;
    }
  };

  const handleQuery = useCallback(async () => {
    setIsLoading(true);
    setErrorMessage(null);

    const startTs = calculateStartTs(timePreset);
    const endTs = Math.floor(Date.now() / 1000);

    try {
      // 1. Gọi song song API lịch sử và cảnh báo
      const [historyRes, alertsRes] = await Promise.all([
        vitalsApi.fetchVitalsHistory(selectedDeviceId, startTs, endTs, 500),
        vitalsApi.fetchAlertsAndAiLogs(selectedDeviceId, 'all', 100),
      ]);

      if (historyRes) {
        setVitalsHistory(historyRes.vitals || []);
        setEcgRecords(historyRes.ecg || []);
      }

      if (alertsRes) {
        setAlertsList(alertsRes.alerts || []);
        setAiResultsList(alertsRes.ai_results || []);
      }
    } catch (err) {
      console.error('History query error:', err);
      setErrorMessage(`Không thể tải dữ liệu từ Backend: ${err.message}`);
    } finally {
      setIsLoading(false);
    }
  }, [selectedDeviceId, timePreset]);

  // Tự động tải dữ liệu ban đầu khi mở trang hoặc thay đổi thiết bị / mốc thời gian
  useEffect(() => {
    handleQuery();
  }, [handleQuery]);

  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2.5 }}>
      {/* 1. Thanh Bộ Lọc Truy Vấn Thời Gian & Thiết Bị */}
      <HistoryFilterBar
        timePreset={timePreset}
        setTimePreset={setTimePreset}
        onQuery={handleQuery}
        isLoading={isLoading}
      />

      {/* 2. Biểu Đồ Diễn Biến Lịch Sử Sinh Hiệu & Đoạn Sóng ECG Quá Khứ */}
      <HistoryTrendChart vitalsData={vitalsHistory} ecgRecords={ecgRecords} />

      {/* 3. Bảng Dữ Liệu Lịch Sử Cảnh Báo & Nhật Ký AI */}
      <AlertsAndAiTable
        alerts={alertsList}
        aiResults={aiResultsList}
        onRefresh={handleQuery}
      />

      {/* Thông báo lỗi nếu có */}
      <Snackbar
        open={Boolean(errorMessage)}
        autoHideDuration={6000}
        onClose={() => setErrorMessage(null)}
      >
        <Alert severity="error" onClose={() => setErrorMessage(null)}>
          {errorMessage}
        </Alert>
      </Snackbar>
    </Box>
  );
};

export default HistoryPage;
