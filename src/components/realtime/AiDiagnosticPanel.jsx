import React, { useState } from 'react';
import {
  Paper,
  Box,
  Typography,
  Chip,
  LinearProgress,
  Grid,
  Button,
  Alert,
  Divider,
  CircularProgress,
} from '@mui/material';
import {
  Psychology as AiIcon,
  PlayArrow as PlayIcon,
  Warning as WarningIcon,
  CheckCircle as CheckCircleIcon,
  Info as InfoIcon,
  Science as ScienceIcon,
} from '@mui/icons-material';
import vitalsApi from '../../api/vitalsApi';
import useEmergencyStore from '../../store/useEmergencyStore';

export const AiDiagnosticPanel = ({ aiResult }) => {
  const selectedDeviceId = useEmergencyStore((state) => state.selectedDeviceId);
  const [isInjecting, setIsInjecting] = useState(false);
  const [injectStatus, setInjectStatus] = useState(null);

  // Kịch bản Demo 3: Gọi API nạp dữ liệu sóng rung nhĩ AFib
  const handleInjectAfibDemo = async () => {
    setIsInjecting(true);
    setInjectStatus(null);
    try {
      const res = await vitalsApi.triggerAfibDemo(selectedDeviceId);
      setInjectStatus({
        type: 'success',
        msg: 'Đã nạp 10s sóng Rung nhĩ giả lập vào pipeline AI thành công!',
      });
    } catch (err) {
      setInjectStatus({
        type: 'error',
        msg: `Không thể gọi API Demo: ${err.message}`,
      });
    } finally {
      setIsInjecting(false);
    }
  };

  // Trích xuất dữ liệu AI
  const contextStatus = aiResult?.context_status || 'RELIABLE_NORMAL';
  const contextMsg = aiResult?.context_message || 'Tín hiệu sinh hiệu đạt độ tin cậy cao.';
  const afibProbability = typeof aiResult?.afib_probability === 'number' ? aiResult.afib_probability : 0.05;
  const afibPercent = Math.round(afibProbability * 100);
  const isAfibDetected = aiResult?.afib_detected || afibProbability >= 0.7;

  const hrv = aiResult?.hrv_metrics || {
    rmssd: 34.2,
    pnn50: 12.5,
    cv_rr: 0.08,
    entropy: 1.45,
  };

  // Context-aware badge status
  let contextColor = 'success';
  let contextLabel = 'Tín hiệu tin cậy (Bình thường)';
  if (contextStatus === 'MOTION_ARTIFACT') {
    contextColor = 'warning';
    contextLabel = 'Lỏng cảm biến do cử động tay (Chặn báo động giả)';
  } else if (contextStatus === 'RESPIRATORY_RISK') {
    contextColor = 'error';
    contextLabel = 'Nguy cơ suy hô hấp cấp (SpO2 tụt khi bất động)';
  }

  // AFib risk color
  let riskColor = '#10b981';
  let riskText = 'Nguy cơ thấp (Nhịp xoang bình thường)';
  if (afibProbability >= 0.7 || isAfibDetected) {
    riskColor = '#ef4444';
    riskText = 'Nguy cơ rất cao (Phát hiện Rung nhĩ - AFib)';
  } else if (afibProbability >= 0.4) {
    riskColor = '#f59e0b';
    riskText = 'Nguy cơ trung bình (Biến thiên nhịp tim cao)';
  }

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
        gap: 2,
        height: '100%',
      }}
    >
      {/* Header */}
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          <AiIcon sx={{ color: '#a855f7', fontSize: 26 }} />
          <Typography variant="subtitle1" sx={{ fontWeight: 700, color: '#f1f5f9' }}>
            CHẨN ĐOÁN THÔNG MINH (AI SERVICE)
          </Typography>
        </Box>
        <Chip
          label="Edge-to-Cloud AI"
          size="small"
          sx={{ backgroundColor: 'rgba(168, 85, 247, 0.15)', color: '#c084fc', border: '1px solid rgba(168, 85, 247, 0.3)', fontWeight: 600, fontSize: '0.7rem' }}
        />
      </Box>

      {/* 1. Context-aware Status */}
      <Box sx={{ p: 1.5, backgroundColor: '#0f172a', borderRadius: '8px', border: '1px solid #334155' }}>
        <Typography variant="caption" sx={{ color: '#94a3b8', fontWeight: 600, display: 'block', mb: 0.8 }}>
          BỘ LỌC NGỮ CẢNH (CONTEXT-AWARE: MAX30102 + MPU6050)
        </Typography>
        <Chip
          color={contextColor}
          label={contextLabel}
          icon={contextColor === 'success' ? <CheckCircleIcon /> : <WarningIcon />}
          sx={{ fontWeight: 600, fontSize: '0.78rem', mb: 0.8 }}
        />
        <Typography variant="caption" sx={{ color: '#cbd5e1', display: 'block' }}>
          {contextMsg}
        </Typography>
      </Box>

      {/* 2. AFib Stroke Probability Meter */}
      <Box sx={{ p: 1.5, backgroundColor: '#0f172a', borderRadius: '8px', border: '1px solid #334155' }}>
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 0.5 }}>
          <Typography variant="caption" sx={{ color: '#94a3b8', fontWeight: 600 }}>
            XÁC SUẤT RUNG NHĨ P(AFIB)
          </Typography>
          <Typography variant="body2" sx={{ fontFamily: 'Roboto Mono', fontWeight: 700, color: riskColor }}>
            {afibPercent}%
          </Typography>
        </Box>

        <LinearProgress
          variant="determinate"
          value={afibPercent}
          sx={{
            height: 10,
            borderRadius: 5,
            backgroundColor: '#334155',
            '& .MuiLinearProgress-bar': {
              backgroundColor: riskColor,
              borderRadius: 5,
            },
            mb: 1,
          }}
        />

        <Typography variant="caption" sx={{ color: riskColor, fontWeight: 600 }}>
          {riskText}
        </Typography>
      </Box>

      {/* 3. HRV Metrics Box */}
      <Box sx={{ p: 1.5, backgroundColor: '#0f172a', borderRadius: '8px', border: '1px solid #334155' }}>
        <Typography variant="caption" sx={{ color: '#94a3b8', fontWeight: 600, display: 'block', mb: 1 }}>
          CHỈ SỐ BIẾN THIÊN NHỊP TIM (HRV METRICS)
        </Typography>
        <Grid container spacing={1}>
          <Grid item xs={6}>
            <Box sx={{ p: 1, backgroundColor: '#1e293b', borderRadius: '6px' }}>
              <Typography variant="caption" sx={{ color: '#64748b', display: 'block' }}>RMSSD</Typography>
              <Typography variant="body2" sx={{ fontFamily: 'Roboto Mono', fontWeight: 700, color: hrv.rmssd > 80 ? '#ef4444' : '#f1f5f9' }}>
                {typeof hrv.rmssd === 'number' ? hrv.rmssd.toFixed(1) : '--'} ms
              </Typography>
            </Box>
          </Grid>
          <Grid item xs={6}>
            <Box sx={{ p: 1, backgroundColor: '#1e293b', borderRadius: '6px' }}>
              <Typography variant="caption" sx={{ color: '#64748b', display: 'block' }}>pNN50</Typography>
              <Typography variant="body2" sx={{ fontFamily: 'Roboto Mono', fontWeight: 700, color: hrv.pnn50 > 30 ? '#ef4444' : '#f1f5f9' }}>
                {typeof hrv.pnn50 === 'number' ? hrv.pnn50.toFixed(1) : '--'} %
              </Typography>
            </Box>
          </Grid>
          <Grid item xs={6}>
            <Box sx={{ p: 1, backgroundColor: '#1e293b', borderRadius: '6px' }}>
              <Typography variant="caption" sx={{ color: '#64748b', display: 'block' }}>CV_RR</Typography>
              <Typography variant="body2" sx={{ fontFamily: 'Roboto Mono', fontWeight: 700, color: '#f1f5f9' }}>
                {typeof hrv.cv_rr === 'number' ? hrv.cv_rr.toFixed(3) : '--'}
              </Typography>
            </Box>
          </Grid>
          <Grid item xs={6}>
            <Box sx={{ p: 1, backgroundColor: '#1e293b', borderRadius: '6px' }}>
              <Typography variant="caption" sx={{ color: '#64748b', display: 'block' }}>Entropy</Typography>
              <Typography variant="body2" sx={{ fontFamily: 'Roboto Mono', fontWeight: 700, color: '#f1f5f9' }}>
                {typeof hrv.entropy === 'number' ? hrv.entropy.toFixed(2) : '--'}
              </Typography>
            </Box>
          </Grid>
        </Grid>
      </Box>

      {/* 4. Recommendation Alert Box */}
      {isAfibDetected ? (
        <Alert
          severity="error"
          variant="filled"
          sx={{
            borderRadius: '8px',
            backgroundColor: '#991b1b',
            color: '#ffffff',
            fontWeight: 600,
            fontSize: '0.8rem',
            animation: 'pulse-slow 2s infinite',
          }}
        >
          Phát hiện bất thường điện tim — Khuyến nghị tầm soát nguy cơ đột quỵ!
        </Alert>
      ) : (
        <Alert
          severity="success"
          variant="outlined"
          sx={{
            borderRadius: '8px',
            borderColor: 'rgba(16, 185, 129, 0.4)',
            color: '#10b981',
            fontSize: '0.78rem',
          }}
        >
          Điện tim đều, không có dấu hiệu rung nhĩ cấp.
        </Alert>
      )}

      {/* 5. Demo Tool Bar for Defense Presentation */}
      <Divider sx={{ borderColor: '#334155', my: 0.5 }} />
      <Box sx={{ mt: 'auto' }}>
        <Typography variant="caption" sx={{ color: '#94a3b8', fontWeight: 700, display: 'flex', alignItems: 'center', gap: 0.5, mb: 1 }}>
          <ScienceIcon sx={{ fontSize: 16, color: '#38bdf8' }} />
          CÔNG CỤ DEMO (DÀNH CHO BẢO VỆ ĐỒ ÁN)
        </Typography>

        <Button
          fullWidth
          variant="contained"
          color="warning"
          startIcon={isInjecting ? <CircularProgress size={16} color="inherit" /> : <PlayIcon />}
          onClick={handleInjectAfibDemo}
          disabled={isInjecting}
          sx={{
            fontWeight: 700,
            fontSize: '0.82rem',
            py: 1,
            backgroundColor: '#d97706',
            '&:hover': { backgroundColor: '#b45309' },
          }}
        >
          {isInjecting ? 'Đang nạp sóng AFib...' : 'Giả Lập Sóng Rung Nhĩ (Kịch bản 3)'}
        </Button>

        {injectStatus && (
          <Alert
            severity={injectStatus.type}
            sx={{ mt: 1, py: 0.2, fontSize: '0.75rem' }}
            onClose={() => setInjectStatus(null)}
          >
            {injectStatus.msg}
          </Alert>
        )}
      </Box>
    </Paper>
  );
};

export default AiDiagnosticPanel;
