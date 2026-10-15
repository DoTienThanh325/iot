import React, { useState } from 'react';
import {
  Paper,
  Box,
  Typography,
  Chip,
  Tabs,
  Tab,
  Divider,
} from '@mui/material';
import {
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
  Legend,
  Brush,
} from 'recharts';

export const HistoryTrendChart = ({ vitalsData = [], ecgRecords = [] }) => {
  const [activeTab, setActiveTab] = useState(0);

  // Format vitals data for Recharts
  const formattedVitals = vitalsData.map((item, idx) => {
    let timeLabel = `${idx}`;
    if (item.timestamp) {
      try {
        const d = new Date(item.timestamp);
        timeLabel = d.toLocaleTimeString('vi-VN', { hour: '2-digit', minute: '2-digit', second: '2-digit' });
      } catch {
        timeLabel = `${idx}`;
      }
    }
    return {
      time: timeLabel,
      bpm: item.bpm ?? null,
      spo2: item.spo2 ?? null,
      temp: item.temperature ? parseFloat(item.temperature.toFixed(1)) : null,
      svm: item.svm ? parseFloat(item.svm.toFixed(2)) : null,
    };
  });

  // Chọn mẫu ECG gần nhất để xem lại
  const selectedEcg = ecgRecords.length > 0 ? ecgRecords[ecgRecords.length - 1] : null;
  const ecgSamples = selectedEcg?.samples || [];
  const formattedEcg = ecgSamples.map((val, idx) => ({
    index: idx,
    value: val,
  }));

  return (
    <Paper
      elevation={0}
      sx={{
        p: 2.5,
        backgroundColor: '#1e293b',
        borderRadius: '12px',
        border: '1px solid #334155',
        display: 'flex',
        flexDirection: 'column',
        gap: 1.5,
      }}
    >
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <Typography variant="subtitle1" sx={{ fontWeight: 700, color: '#f1f5f9' }}>
          BIỂU ĐỒ DIỄN BIẾN LỊCH SỬ SINH HIỆU
        </Typography>

        <Tabs
          value={activeTab}
          onChange={(e, val) => setActiveTab(val)}
          sx={{
            minHeight: 32,
            '& .MuiTab-root': {
              minHeight: 32,
              py: 0.5,
              fontSize: '0.8rem',
              fontWeight: 600,
              color: '#94a3b8',
              '&.Mui-selected': { color: '#38bdf8' },
            },
          }}
        >
          <Tab label="Sinh hiệu (BPM / SpO2 / Nhiệt độ)" />
          <Tab label={`Đoạn sóng ECG đã lưu (${ecgRecords.length} đoạn)`} />
        </Tabs>
      </Box>

      <Divider sx={{ borderColor: '#334155' }} />

      {activeTab === 0 ? (
        /* Vitals Trend Chart */
        <Box sx={{ width: '100%', height: 320 }}>
          {formattedVitals.length === 0 ? (
            <Box sx={{ height: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
              <Typography variant="body2" sx={{ color: '#64748b' }}>
                Chưa có dữ liệu sinh hiệu trong khoảng thời gian đã chọn. Hãy bấm "Truy Vấn Dữ Liệu".
              </Typography>
            </Box>
          ) : (
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={formattedVitals} margin={{ top: 10, right: 20, left: -10, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
                <XAxis dataKey="time" stroke="#64748b" tick={{ fontSize: 11, fill: '#64748b' }} />
                <YAxis yAxisId="left" domain={[30, 180]} stroke="#ef4444" tick={{ fontSize: 11, fill: '#ef4444' }} />
                <YAxis yAxisId="right" orientation="right" domain={[70, 100]} stroke="#38bdf8" tick={{ fontSize: 11, fill: '#38bdf8' }} />
                <Tooltip
                  contentStyle={{
                    backgroundColor: '#0f172a',
                    border: '1px solid #334155',
                    borderRadius: '8px',
                    color: '#f8fafc',
                  }}
                />
                <Legend wrapperStyle={{ fontSize: '0.8rem' }} />
                <Line
                  yAxisId="left"
                  type="monotone"
                  dataKey="bpm"
                  name="Nhịp tim (BPM)"
                  stroke="#ef4444"
                  strokeWidth={2}
                  dot={false}
                />
                <Line
                  yAxisId="right"
                  type="monotone"
                  dataKey="spo2"
                  name="SpO2 (%)"
                  stroke="#38bdf8"
                  strokeWidth={2}
                  dot={false}
                />
                <Line
                  yAxisId="left"
                  type="monotone"
                  dataKey="temp"
                  name="Nhiệt độ (°C)"
                  stroke="#f59e0b"
                  strokeWidth={1.5}
                  strokeDasharray="4 4"
                  dot={false}
                />
                {/* Brush Slider */}
                <Brush dataKey="time" height={28} stroke="#475569" fill="#0f172a" />
              </LineChart>
            </ResponsiveContainer>
          )}
        </Box>
      ) : (
        /* Historical ECG Segment Waveform */
        <Box sx={{ width: '100%', height: 320 }}>
          {formattedEcg.length === 0 ? (
            <Box sx={{ height: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
              <Typography variant="body2" sx={{ color: '#64748b' }}>
                Không tìm thấy bản ghi sóng ECG trong khoảng thời gian này.
              </Typography>
            </Box>
          ) : (
            <Box sx={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
              <Typography variant="caption" sx={{ color: '#94a3b8', mb: 1 }}>
                Thời điểm ghi nhận: {selectedEcg.timestamp ? new Date(selectedEcg.timestamp).toLocaleString('vi-VN') : 'N/A'} • Tần số lấy mẫu: {selectedEcg.fs || 125} Hz • Số điểm: {ecgSamples.length}
              </Typography>
              <Box sx={{ flexGrow: 1, backgroundColor: '#051314', borderRadius: '8px', p: 1, border: '1px solid rgba(16, 185, 129, 0.2)' }}>
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={formattedEcg} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                    <CartesianGrid stroke="rgba(16, 185, 129, 0.15)" strokeDasharray="2 2" />
                    <XAxis dataKey="index" stroke="#64748b" tick={{ fontSize: 10, fill: '#64748b' }} />
                    <YAxis domain={[0, 1023]} stroke="#10b981" tick={{ fontSize: 10, fill: '#10b981' }} />
                    <Tooltip
                      contentStyle={{
                        backgroundColor: '#0f172a',
                        border: '1px solid #10b981',
                        borderRadius: '6px',
                        color: '#10b981',
                      }}
                    />
                    <Line
                      type="monotone"
                      dataKey="value"
                      stroke="#00ff88"
                      strokeWidth={1.5}
                      dot={false}
                      isAnimationActive={false}
                    />
                    <Brush dataKey="index" height={25} stroke="#10b981" fill="#0b111e" />
                  </LineChart>
                </ResponsiveContainer>
              </Box>
            </Box>
          )}
        </Box>
      )}
    </Paper>
  );
};

export default HistoryTrendChart;
