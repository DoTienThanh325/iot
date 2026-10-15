import React, { useEffect, useState } from 'react';
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  Typography,
  Box,
  Divider,
  CircularProgress,
} from '@mui/material';
import {
  Warning as WarningIcon,
  Sos as SosIcon,
  CheckCircle as CheckCircleIcon,
  NotificationsActive as AlarmIcon,
} from '@mui/icons-material';
import useEmergencyStore from '../../store/useEmergencyStore';
import useAudioAlert from '../../hooks/useAudioAlert';
import vitalsApi from '../../api/vitalsApi';

export const CriticalAlertOverlay = () => {
  const isCriticalActive = useEmergencyStore((state) => state.isCriticalActive);
  const activeAlert = useEmergencyStore((state) => state.activeAlert);
  const acknowledgeAlertInStore = useEmergencyStore((state) => state.acknowledgeAlertInStore);
  const dismissActiveModal = useEmergencyStore((state) => state.dismissActiveModal);

  const { startAlarm, stopAlarm } = useAudioAlert();
  const [isSubmitting, setIsSubmitting] = useState(false);

  // Kích hoạt còi báo động khi có cảnh báo đỏ
  useEffect(() => {
    if (isCriticalActive) {
      startAlarm();
    } else {
      stopAlarm();
    }
    return () => {
      stopAlarm();
    };
  }, [isCriticalActive, startAlarm, stopAlarm]);

  if (!isCriticalActive || !activeAlert) {
    return null;
  }

  const handleAcknowledge = async () => {
    setIsSubmitting(true);
    try {
      if (activeAlert._id) {
        await vitalsApi.acknowledgeAlert(activeAlert._id, 'Y tá trực ban', 'Đã tiếp cận bệnh nhân');
      }
      stopAlarm();
      acknowledgeAlertInStore(activeAlert._id);
    } catch (e) {
      console.error('Failed to acknowledge alert:', e);
      // Vẫn cho phép tắt tại client
      stopAlarm();
      acknowledgeAlertInStore(activeAlert._id);
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleDismiss = () => {
    stopAlarm();
    dismissActiveModal();
  };

  // Xác định tiêu đề theo loại cảnh báo
  let alertTitle = 'CẢNH BÁO CẤP CỨU KHẨN CẤP';
  if (activeAlert.alert_type === 'SOS_PRESSED') {
    alertTitle = 'BỆNH NHÂN BẤM NÚT KHẨN CẤP (SOS)!';
  } else if (activeAlert.alert_type === 'FALL_CONFIRMED' || activeAlert.alert_type === 'EDGE_FALL_DETECTED') {
    alertTitle = 'PHÁT HIỆN BỆNH NHÂN BỊ NGÃ / MẤT Ý THỨC!';
  } else if (activeAlert.alert_type === 'RESPIRATORY_RISK') {
    alertTitle = 'NGUY CƠ SUY HÔ HẤP CẤP (SpO2 TỤT SÂU)!';
  } else if (activeAlert.alert_type === 'AFIB_HIGH_RISK') {
    alertTitle = 'NGUY CƠ ĐỘT QUỴ CẤP (RUNG NHĨ BẤT THƯỜNG)!';
  }

  return (
    <>
      {/* 1. Hiệu ứng viền nháy đỏ toàn màn hình (Keyframes pulse-red) */}
      <Box
        sx={{
          position: 'fixed',
          top: 0,
          left: 0,
          right: 0,
          bottom: 0,
          pointerEvents: 'none',
          zIndex: 9998,
          boxShadow: 'inset 0 0 80px 30px rgba(239, 68, 68, 0.85)',
          animation: 'pulse-red 0.8s infinite',
          '@keyframes pulse-red': {
            '0%': {
              boxShadow: 'inset 0 0 50px 20px rgba(239, 68, 68, 0.5)',
              border: '6px solid rgba(239, 68, 68, 0.6)',
            },
            '50%': {
              boxShadow: 'inset 0 0 120px 45px rgba(239, 68, 68, 0.95)',
              border: '8px solid rgba(239, 68, 68, 1)',
            },
            '100%': {
              boxShadow: 'inset 0 0 50px 20px rgba(239, 68, 68, 0.5)',
              border: '6px solid rgba(239, 68, 68, 0.6)',
            },
          },
        }}
      />

      {/* 2. Dialog Modal Cấp Cứu ở trung tâm màn hình */}
      <Dialog
        open={true}
        onClose={handleDismiss}
        maxWidth="sm"
        fullWidth
        PaperProps={{
          sx: {
            backgroundColor: '#0f172a',
            color: '#f8fafc',
            border: '2px solid #ef4444',
            borderRadius: '16px',
            boxShadow: '0 0 50px rgba(239, 68, 68, 0.5)',
            zIndex: 9999,
          },
        }}
      >
        <DialogTitle
          sx={{
            backgroundColor: '#7f1d1d',
            display: 'flex',
            alignItems: 'center',
            gap: 1.5,
            py: 2,
          }}
        >
          <AlarmIcon sx={{ color: '#fef2f2', fontSize: 32, animation: 'heartBeat 0.8s infinite' }} />
          <Typography variant="h6" sx={{ fontWeight: 800, color: '#fef2f2', letterSpacing: '0.5px' }}>
            {alertTitle}
          </Typography>
        </DialogTitle>

        <DialogContent sx={{ p: 3 }}>
          <Typography variant="body1" sx={{ color: '#fca5a5', fontWeight: 600, mb: 2, mt: 1 }}>
            {activeAlert.message || 'Hệ thống phát hiện tín hiệu bất thường nguy hiểm tính mạng từ bệnh nhân.'}
          </Typography>

          <Box
            sx={{
              p: 2,
              backgroundColor: '#1e293b',
              borderRadius: '10px',
              border: '1px solid #334155',
              display: 'flex',
              flexDirection: 'column',
              gap: 1.2,
            }}
          >
            <Box sx={{ display: 'flex', justifyContent: 'space-between' }}>
              <Typography variant="body2" sx={{ color: '#94a3b8' }}>Mã Thiết bị:</Typography>
              <Typography variant="body2" sx={{ fontWeight: 700, color: '#38bdf8' }}>{activeAlert.device_id}</Typography>
            </Box>
            <Divider sx={{ borderColor: '#334155' }} />

            <Box sx={{ display: 'flex', justifyContent: 'space-between' }}>
              <Typography variant="body2" sx={{ color: '#94a3b8' }}>Thời điểm xảy ra:</Typography>
              <Typography variant="body2" sx={{ fontWeight: 600, fontFamily: 'Roboto Mono' }}>
                {activeAlert.timestamp ? new Date(activeAlert.timestamp).toLocaleString('vi-VN') : 'Vừa xong'}
              </Typography>
            </Box>
            <Divider sx={{ borderColor: '#334155' }} />

            <Box sx={{ display: 'flex', justifyContent: 'space-between' }}>
              <Typography variant="body2" sx={{ color: '#94a3b8' }}>Chỉ số ghi nhận:</Typography>
              <Typography variant="body2" sx={{ fontWeight: 700, color: '#ef4444' }}>
                BPM: {activeAlert.bpm ?? '--'} | SpO2: {activeAlert.spo2 ? `${activeAlert.spo2}%` : '--'} | SVM: {activeAlert.max_svm ? `${activeAlert.max_svm.toFixed(2)}g` : '--'}
              </Typography>
            </Box>
          </Box>
        </DialogContent>

        <DialogActions sx={{ p: 2.5, backgroundColor: '#1e293b', display: 'flex', justifyContent: 'space-between' }}>
          <Button
            onClick={handleDismiss}
            variant="outlined"
            sx={{ color: '#94a3b8', borderColor: '#475569' }}
          >
            Tạm ẩn cửa sổ
          </Button>

          <Button
            onClick={handleAcknowledge}
            variant="contained"
            color="error"
            size="large"
            disabled={isSubmitting}
            startIcon={isSubmitting ? <CircularProgress size={20} color="inherit" /> : <CheckCircleIcon />}
            sx={{
              fontWeight: 800,
              fontSize: '0.95rem',
              px: 3,
              backgroundColor: '#ef4444',
              '&:hover': { backgroundColor: '#dc2626' },
            }}
          >
            {isSubmitting ? 'Đang gửi xác nhận...' : 'Xác Nhận Đã Xử Lý (Acknowledge)'}
          </Button>
        </DialogActions>
      </Dialog>
    </>
  );
};

export default CriticalAlertOverlay;
