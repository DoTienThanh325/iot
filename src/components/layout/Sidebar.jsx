import React from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import {
  Box,
  Drawer,
  List,
  ListItem,
  ListItemButton,
  ListItemIcon,
  ListItemText,
  Typography,
  Divider,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Chip,
  Paper,
} from '@mui/material';
import {
  MonitorHeart as MonitorHeartIcon,
  History as HistoryIcon,
  Devices as DevicesIcon,
  LocalHospital as HospitalIcon,
  MedicalServices as MedicalServicesIcon,
} from '@mui/icons-material';
import useEmergencyStore from '../../store/useEmergencyStore';

const drawerWidth = 260;

export const Sidebar = () => {
  const navigate = useNavigate();
  const location = useLocation();

  const selectedDeviceId = useEmergencyStore((state) => state.selectedDeviceId);
  const setSelectedDeviceId = useEmergencyStore((state) => state.setSelectedDeviceId);
  const availableDevices = useEmergencyStore((state) => state.availableDevices);
  const isWsConnected = useEmergencyStore((state) => state.isWsConnected);

  const menuItems = [
    {
      text: 'Trang Realtime',
      path: '/realtime',
      icon: <MonitorHeartIcon sx={{ color: '#10b981' }} />,
      description: 'Giám sát trực ban 60 FPS',
    },
    {
      text: 'Trang Lịch Sử',
      path: '/history',
      icon: <HistoryIcon sx={{ color: '#3b82f6' }} />,
      description: 'Tra cứu & phân tích AI',
    },
  ];

  const isCurrentPath = (path) => {
    if (path === '/realtime' && (location.pathname === '/' || location.pathname === '/realtime')) {
      return true;
    }
    return location.pathname === path;
  };

  return (
    <Drawer
      variant="permanent"
      sx={{
        width: drawerWidth,
        flexShrink: 0,
        [`& .MuiDrawer-paper`]: {
          width: drawerWidth,
          boxSizing: 'border-box',
          backgroundColor: '#0f172a',
          color: '#f8fafc',
          borderRight: '1px solid #1e293b',
        },
      }}
    >
      {/* Brand Header */}
      <Box sx={{ p: 2.5, display: 'flex', alignItems: 'center', gap: 1.5 }}>
        <Box
          sx={{
            width: 42,
            height: 42,
            borderRadius: '10px',
            bgcolor: 'rgba(239, 68, 68, 0.15)',
            border: '1px solid rgba(239, 68, 68, 0.4)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
          }}
        >
          <HospitalIcon sx={{ color: '#ef4444', fontSize: 26 }} />
        </Box>
        <Box>
          <Typography variant="subtitle1" sx={{ fontWeight: 700, lineHeight: 1.2, letterSpacing: '0.5px' }}>
            STROKE MONITOR
          </Typography>
          <Typography variant="caption" sx={{ color: '#94a3b8' }}>
            ICU / Tele-Health Node
          </Typography>
        </Box>
      </Box>

      <Divider sx={{ borderColor: '#1e293b' }} />

      {/* Device Selector */}
      <Box sx={{ p: 2 }}>
        <Typography variant="caption" sx={{ color: '#64748b', fontWeight: 600, textTransform: 'uppercase', mb: 1, display: 'block' }}>
          Thiết Bị Đang Giám Sát
        </Typography>
        <Paper
          elevation={0}
          sx={{
            p: 1.5,
            backgroundColor: '#1e293b',
            borderRadius: '10px',
            border: '1px solid #334155',
          }}
        >
          <FormControl fullWidth size="small">
            <InputLabel id="device-select-label" sx={{ color: '#94a3b8' }}>
              Mã ESP32
            </InputLabel>
            <Select
              labelId="device-select-label"
              value={selectedDeviceId}
              label="Mã ESP32"
              onChange={(e) => setSelectedDeviceId(e.target.value)}
              sx={{
                color: '#f8fafc',
                '.MuiOutlinedInput-notchedOutline': { borderColor: '#475569' },
                '&:hover .MuiOutlinedInput-notchedOutline': { borderColor: '#3b82f6' },
                '&.Mui-focused .MuiOutlinedInput-notchedOutline': { borderColor: '#3b82f6' },
                '.MuiSvgIcon-root': { color: '#94a3b8' },
              }}
            >
              {availableDevices.map((devId) => (
                <MenuItem key={devId} value={devId}>
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                    <DevicesIcon fontSize="small" sx={{ color: '#38bdf8' }} />
                    <Typography variant="body2" sx={{ fontWeight: 600 }}>
                      {devId}
                    </Typography>
                  </Box>
                </MenuItem>
              ))}
            </Select>
          </FormControl>

          <Box sx={{ mt: 1.5, display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <Typography variant="caption" sx={{ color: '#94a3b8' }}>
              Trạng thái:
            </Typography>
            <Chip
              size="small"
              label={isWsConnected ? 'Trực tuyến' : 'Mất kết nối'}
              color={isWsConnected ? 'success' : 'error'}
              sx={{ height: 20, fontSize: '0.7rem', fontWeight: 600 }}
            />
          </Box>
        </Paper>
      </Box>

      <Divider sx={{ borderColor: '#1e293b' }} />

      {/* Navigation Menu */}
      <Box sx={{ px: 1.5, py: 2 }}>
        <Typography variant="caption" sx={{ color: '#64748b', fontWeight: 600, textTransform: 'uppercase', px: 1, mb: 1, display: 'block' }}>
          Phân Khu Chức Năng
        </Typography>
        <List sx={{ gap: 0.5, display: 'flex', flexDirection: 'column' }}>
          {menuItems.map((item) => {
            const active = isCurrentPath(item.path);
            return (
              <ListItem key={item.text} disablePadding>
                <ListItemButton
                  onClick={() => navigate(item.path)}
                  sx={{
                    borderRadius: '8px',
                    backgroundColor: active ? 'rgba(59, 130, 246, 0.15)' : 'transparent',
                    border: active ? '1px solid rgba(59, 130, 246, 0.4)' : '1px solid transparent',
                    '&:hover': {
                      backgroundColor: 'rgba(255, 255, 255, 0.05)',
                    },
                    py: 1.2,
                  }}
                >
                  <ListItemIcon sx={{ minWidth: 38 }}>
                    {item.icon}
                  </ListItemIcon>
                  <ListItemText
                    primary={
                      <Typography variant="body2" sx={{ fontWeight: active ? 700 : 500, color: active ? '#60a5fa' : '#e2e8f0' }}>
                        {item.text}
                      </Typography>
                    }
                    secondary={
                      <Typography variant="caption" sx={{ color: '#64748b', fontSize: '0.72rem' }}>
                        {item.description}
                      </Typography>
                    }
                  />
                </ListItemButton>
              </ListItem>
            );
          })}
        </List>
      </Box>

      {/* Bottom Info */}
      <Box sx={{ mt: 'auto', p: 2, borderTop: '1px solid #1e293b' }}>
        <Paper
          elevation={0}
          sx={{
            p: 1.5,
            backgroundColor: '#0b111e',
            borderRadius: '8px',
            border: '1px dashed #334155',
          }}
        >
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 0.5 }}>
            <MedicalServicesIcon sx={{ color: '#10b981', fontSize: 18 }} />
            <Typography variant="caption" sx={{ fontWeight: 600, color: '#e2e8f0' }}>
              Phòng Cấp Cứu A3 - Giường 04
            </Typography>
          </Box>
          <Typography variant="caption" sx={{ color: '#64748b', display: 'block', fontSize: '0.7rem' }}>
            Bác sĩ phụ trách: TS. Trần Văn A
          </Typography>
        </Paper>
      </Box>
    </Drawer>
  );
};

export default Sidebar;
