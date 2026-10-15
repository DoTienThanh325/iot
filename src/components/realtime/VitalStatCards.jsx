import React from 'react';
import { Grid, Card, CardContent, Typography, Box, Chip } from '@mui/material';
import {
  Favorite as HeartIcon,
  Air as LungIcon,
  Thermostat as TempIcon,
  DirectionsWalk as MotionIcon,
} from '@mui/icons-material';

export const VitalStatCards = ({ vitals }) => {
  const {
    bpm = '--',
    spo2 = '--',
    temperature = '--',
    svm = 1.0,
    posture = 'Đang nằm yên',
  } = vitals || {};

  // BPM Color & Status
  let bpmColor = '#10b981'; // Green
  let bpmStatus = 'Bình thường';
  if (typeof bpm === 'number') {
    if (bpm > 120) {
      bpmColor = '#ef4444'; // Red
      bpmStatus = 'Nhịp nhanh nguy hiểm';
    } else if (bpm > 100) {
      bpmColor = '#f59e0b'; // Amber
      bpmStatus = 'Nhịp nhanh';
    } else if (bpm < 50) {
      bpmColor = '#f59e0b'; // Amber
      bpmStatus = 'Nhịp chậm';
    }
  }

  // SpO2 Color & Status
  let spo2Color = '#10b981';
  let spo2Status = 'Bình thường';
  if (typeof spo2 === 'number') {
    if (spo2 < 92) {
      spo2Color = '#ef4444';
      spo2Status = 'Thiếu oxy cấp';
    } else if (spo2 <= 94) {
      spo2Color = '#f59e0b';
      spo2Status = 'Cảnh báo giảm SpO2';
    }
  }

  // Temp Color & Status
  let tempColor = '#10b981';
  let tempStatus = 'Thân nhiệt chuẩn';
  if (typeof temperature === 'number') {
    if (temperature > 38.5) {
      tempColor = '#ef4444';
      tempStatus = 'Sốt cao';
    } else if (temperature > 37.5) {
      tempColor = '#f59e0b';
      tempStatus = 'Sốt nhẹ';
    } else if (temperature < 35.5) {
      tempColor = '#3b82f6';
      tempStatus = 'Hạ thân nhiệt';
    }
  }

  // SVM & Motion status
  let motionColor = '#3b82f6';
  if (svm > 2.5 || posture === 'Phát hiện va chạm') {
    motionColor = '#ef4444';
  } else if (svm > 1.3 || posture === 'Đang vận động') {
    motionColor = '#10b981';
  }

  const cards = [
    {
      title: 'NHỊP TIM (MAX30102)',
      value: typeof bpm === 'number' ? bpm : '--',
      unit: 'BPM',
      status: bpmStatus,
      color: bpmColor,
      icon: <HeartIcon sx={{ fontSize: 32, color: bpmColor }} />,
      pulse: typeof bpm === 'number' && bpm > 0,
    },
    {
      title: 'NỒNG ĐỘ OXY (SpO2)',
      value: typeof spo2 === 'number' ? `${spo2}%` : '--',
      unit: 'SpO2',
      status: spo2Status,
      color: spo2Color,
      icon: <LungIcon sx={{ fontSize: 32, color: spo2Color }} />,
      pulse: false,
    },
    {
      title: 'THÂN NHIỆT (DS18B20)',
      value: typeof temperature === 'number' ? `${temperature.toFixed(1)}°` : '--',
      unit: '°C',
      status: tempStatus,
      color: tempColor,
      icon: <TempIcon sx={{ fontSize: 32, color: tempColor }} />,
      pulse: false,
    },
    {
      title: 'VẬN ĐỘNG & TƯ THẾ (MPU6050)',
      value: typeof svm === 'number' ? `${svm.toFixed(2)}` : '--',
      unit: 'SVM (g)',
      status: posture,
      color: motionColor,
      icon: <MotionIcon sx={{ fontSize: 32, color: motionColor }} />,
      pulse: false,
    },
  ];

  return (
    <Grid container spacing={2}>
      {cards.map((c, idx) => (
        <Grid item xs={12} sm={6} md={3} key={idx}>
          <Card
            elevation={0}
            sx={{
              backgroundColor: '#1e293b',
              borderRadius: '12px',
              border: `1px solid ${c.color}33`,
              boxShadow: `0 4px 20px -2px ${c.color}15`,
              position: 'relative',
              overflow: 'hidden',
              transition: 'transform 0.2s ease, box-shadow 0.2s ease',
              '&:hover': {
                transform: 'translateY(-2px)',
                boxShadow: `0 6px 24px -2px ${c.color}25`,
              },
            }}
          >
            {/* Top colored indicator bar */}
            <Box sx={{ height: 4, width: '100%', backgroundColor: c.color }} />

            <CardContent sx={{ p: 2, '&:last-child': { pb: 2 } }}>
              <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', mb: 1 }}>
                <Typography variant="caption" sx={{ color: '#94a3b8', fontWeight: 700, letterSpacing: '0.5px' }}>
                  {c.title}
                </Typography>
                <Box
                  sx={{
                    animation: c.pulse ? 'heartBeat 1.2s infinite' : 'none',
                    '@keyframes heartBeat': {
                      '0%': { transform: 'scale(1)' },
                      '14%': { transform: 'scale(1.18)' },
                      '28%': { transform: 'scale(1)' },
                      '42%': { transform: 'scale(1.14)' },
                      '70%': { transform: 'scale(1)' },
                    },
                  }}
                >
                  {c.icon}
                </Box>
              </Box>

              <Box sx={{ display: 'flex', alignItems: 'baseline', gap: 1, my: 0.5 }}>
                <Typography
                  variant="h3"
                  sx={{
                    fontFamily: 'Roboto Mono, monospace',
                    fontWeight: 700,
                    color: c.color,
                    lineHeight: 1,
                  }}
                >
                  {c.value}
                </Typography>
                <Typography variant="body2" sx={{ color: '#64748b', fontWeight: 600 }}>
                  {c.unit}
                </Typography>
              </Box>

              <Box sx={{ mt: 1.5, display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                <Chip
                  size="small"
                  label={c.status}
                  sx={{
                    fontSize: '0.72rem',
                    fontWeight: 600,
                    backgroundColor: `${c.color}22`,
                    color: c.color,
                    border: `1px solid ${c.color}44`,
                    height: 22,
                  }}
                />
              </Box>
            </CardContent>
          </Card>
        </Grid>
      ))}
    </Grid>
  );
};

export default VitalStatCards;
