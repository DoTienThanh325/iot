import React, { useState, useEffect } from 'react';
import {
  AppBar,
  Toolbar,
  Typography,
  Box,
  IconButton,
  Chip,
  Tooltip,
  Badge,
} from '@mui/material';
import {
  VolumeUp as VolumeUpIcon,
  VolumeOff as VolumeOffIcon,
  NotificationsActive as AlertIcon,
  Sensors as SensorsIcon,
  SensorsOff as SensorsOffIcon,
  AccessTime as AccessTimeIcon,
} from '@mui/icons-material';
import useEmergencyStore from '../../store/useEmergencyStore';

export const Topbar = () => {
  const isWsConnected = useEmergencyStore((state) => state.isWsConnected);
  const isMuted = useEmergencyStore((state) => state.isMuted);
  const toggleMute = useEmergencyStore((state) => state.toggleMute);
  const unacknowledgedAlerts = useEmergencyStore((state) => state.unacknowledgedAlerts);
  const selectedDeviceId = useEmergencyStore((state) => state.selectedDeviceId);

  const [currentTime, setCurrentTime] = useState(new Date().toLocaleTimeString('vi-VN'));

  useEffect(() => {
    const timer = setInterval(() => {
      setCurrentTime(new Date().toLocaleTimeString('vi-VN'));
    }, 1000);
    return () => clearInterval(timer);
  }, []);

  return (
    <AppBar
      position="sticky"
      elevation={0}
      sx={{
        backgroundColor: '#0f172a',
        borderBottom: '1px solid #1e293b',
        color: '#f8fafc',
        zIndex: (theme) => theme.zIndex.drawer + 1,
      }}
    >
      <Toolbar sx={{ justifyContent: 'space-between', px: 3 }}>
        {/* Left: Project title and device tag */}
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
          <Typography variant="h6" sx={{ fontWeight: 700, letterSpacing: '0.5px', color: '#f1f5f9', fontSize: '1.05rem' }}>
            HỆ THỐNG GIÁM SÁT SINH HIỆU & CẢNH BÁO ĐỘT QUỴ
          </Typography>
          <Chip
            size="small"
            label={`Thiết bị: ${selectedDeviceId}`}
            sx={{
              backgroundColor: '#1e293b',
              color: '#38bdf8',
              border: '1px solid #334155',
              fontWeight: 600,
            }}
          />
        </Box>

        {/* Right: Status indicators, mute button, time */}
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
          {/* Real-time Clock */}
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.8, color: '#94a3b8', px: 1 }}>
            <AccessTimeIcon sx={{ fontSize: 18, color: '#64748b' }} />
            <Typography variant="body2" sx={{ fontFamily: 'Roboto Mono, monospace', fontWeight: 600, color: '#e2e8f0' }}>
              {currentTime}
            </Typography>
          </Box>

          {/* WebSocket Connection Status */}
          <Chip
            icon={isWsConnected ? <SensorsIcon sx={{ color: '#10b981 !important' }} /> : <SensorsOffIcon sx={{ color: '#ef4444 !important' }} />}
            label={isWsConnected ? 'WebSocket: Đang stream' : 'WebSocket: Mất tín hiệu'}
            variant="outlined"
            size="small"
            sx={{
              borderColor: isWsConnected ? 'rgba(16, 185, 129, 0.4)' : 'rgba(239, 68, 68, 0.4)',
              color: isWsConnected ? '#10b981' : '#ef4444',
              backgroundColor: isWsConnected ? 'rgba(16, 185, 129, 0.08)' : 'rgba(239, 68, 68, 0.08)',
              fontWeight: 600,
            }}
          />

          {/* Sound Mute Toggle */}
          <Tooltip title={isMuted ? 'Đang tắt còi báo động (Bấm để bật)' : 'Đang bật còi báo động (Bấm để tắt)'}>
            <IconButton
              onClick={toggleMute}
              sx={{
                bgcolor: isMuted ? 'rgba(239, 68, 68, 0.15)' : 'rgba(16, 185, 129, 0.15)',
                color: isMuted ? '#ef4444' : '#10b981',
                border: `1px solid ${isMuted ? 'rgba(239, 68, 68, 0.3)' : 'rgba(16, 185, 129, 0.3)'}`,
                '&:hover': {
                  bgcolor: isMuted ? 'rgba(239, 68, 68, 0.25)' : 'rgba(16, 185, 129, 0.25)',
                },
              }}
            >
              {isMuted ? <VolumeOffIcon fontSize="small" /> : <VolumeUpIcon fontSize="small" />}
            </IconButton>
          </Tooltip>

          {/* Active alerts counter badge */}
          <Tooltip title={`${unacknowledgedAlerts.length} cảnh báo chưa xác nhận`}>
            <Badge badgeContent={unacknowledgedAlerts.length} color="error" max={99}>
              <IconButton
                sx={{
                  bgcolor: unacknowledgedAlerts.length > 0 ? 'rgba(239, 68, 68, 0.2)' : '#1e293b',
                  color: unacknowledgedAlerts.length > 0 ? '#ef4444' : '#94a3b8',
                  border: '1px solid #334155',
                }}
              >
                <AlertIcon fontSize="small" />
              </IconButton>
            </Badge>
          </Tooltip>
        </Box>
      </Toolbar>
    </AppBar>
  );
};

export default Topbar;
