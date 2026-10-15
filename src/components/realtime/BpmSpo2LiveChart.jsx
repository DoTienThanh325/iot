import React from 'react';
import { Paper, Box, Typography, Chip } from '@mui/material';
import {
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
  Legend,
} from 'recharts';

export const BpmSpo2LiveChart = ({ data = [] }) => {
  // Chuẩn hóa dữ liệu hiển thị (lấy 60 điểm gần nhất)
  const chartData = data.slice(-60).map((item, index) => {
    let timeLabel = `${index}s`;
    if (item.timestamp) {
      try {
        const d = new Date(item.timestamp);
        timeLabel = `${d.getMinutes().toString().padStart(2, '0')}:${d.getSeconds().toString().padStart(2, '0')}`;
      } catch {
        timeLabel = `${index}s`;
      }
    }
    return {
      time: timeLabel,
      bpm: item.bpm ?? 0,
      spo2: item.spo2 ?? 0,
    };
  });

  return (
    <Paper
      elevation={0}
      sx={{
        p: 2,
        backgroundColor: '#1e293b',
        borderRadius: '12px',
        border: '1px solid #334155',
        display: 'flex',
        flexDirection: 'column',
      }}
    >
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 1.5 }}>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          <Typography variant="subtitle2" sx={{ fontWeight: 700, color: '#f1f5f9' }}>
            XU HƯỚNG NHỊP TIM & SpO2 (60 GIÂY GẦN NHẤT)
          </Typography>
          <Chip label="Cửa sổ 60s" size="small" sx={{ backgroundColor: '#0f172a', color: '#94a3b8', height: 20, fontSize: '0.7rem' }} />
        </Box>
        <Box sx={{ display: 'flex', gap: 2 }}>
          <Typography variant="caption" sx={{ color: '#ef4444', fontWeight: 600, display: 'flex', alignItems: 'center', gap: 0.5 }}>
            ● Nhịp tim (BPM)
          </Typography>
          <Typography variant="caption" sx={{ color: '#38bdf8', fontWeight: 600, display: 'flex', alignItems: 'center', gap: 0.5 }}>
            ● Nồng độ oxy (SpO2 %)
          </Typography>
        </Box>
      </Box>

      <Box sx={{ width: '100%', height: 210 }}>
        {chartData.length === 0 ? (
          <Box sx={{ height: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
            <Typography variant="body2" sx={{ color: '#64748b' }}>
              Đang chờ dữ liệu sinh hiệu từ cảm biến...
            </Typography>
          </Box>
        ) : (
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={chartData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#334155" vertical={false} />
              <XAxis
                dataKey="time"
                stroke="#64748b"
                tick={{ fontSize: 11, fill: '#64748b' }}
                tickLine={false}
              />
              {/* Y-axis Trái cho BPM */}
              <YAxis
                yAxisId="left"
                domain={[40, 160]}
                stroke="#ef4444"
                tick={{ fontSize: 11, fill: '#ef4444' }}
                tickLine={false}
              />
              {/* Y-axis Phải cho SpO2 */}
              <YAxis
                yAxisId="right"
                orientation="right"
                domain={[80, 100]}
                stroke="#38bdf8"
                tick={{ fontSize: 11, fill: '#38bdf8' }}
                tickLine={false}
              />
              <Tooltip
                contentStyle={{
                  backgroundColor: '#0f172a',
                  border: '1px solid #334155',
                  borderRadius: '8px',
                  color: '#f8fafc',
                  fontSize: '0.8rem',
                }}
              />
              <Line
                yAxisId="left"
                type="monotone"
                dataKey="bpm"
                stroke="#ef4444"
                strokeWidth={2}
                dot={false}
                isAnimationActive={false}
              />
              <Line
                yAxisId="right"
                type="monotone"
                dataKey="spo2"
                stroke="#38bdf8"
                strokeWidth={2}
                dot={false}
                isAnimationActive={false}
              />
            </LineChart>
          </ResponsiveContainer>
        )}
      </Box>
    </Paper>
  );
};

export default BpmSpo2LiveChart;
