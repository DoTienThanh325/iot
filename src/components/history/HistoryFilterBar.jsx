import React from 'react';
import {
  Paper,
  Box,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Button,
  ButtonGroup,
  Typography,
  CircularProgress,
} from '@mui/material';
import {
  Search as SearchIcon,
  Refresh as RefreshIcon,
  FilterAlt as FilterIcon,
} from '@mui/icons-material';
import useEmergencyStore from '../../store/useEmergencyStore';

export const HistoryFilterBar = ({
  timePreset,
  setTimePreset,
  onQuery,
  isLoading,
}) => {
  const selectedDeviceId = useEmergencyStore((state) => state.selectedDeviceId);
  const setSelectedDeviceId = useEmergencyStore((state) => state.setSelectedDeviceId);
  const availableDevices = useEmergencyStore((state) => state.availableDevices);

  const presets = [
    { label: '15 phút trước', value: '15m' },
    { label: '1 giờ trước', value: '1h' },
    { label: '6 giờ trước', value: '6h' },
    { label: '24 giờ qua', value: '24h' },
  ];

  return (
    <Paper
      elevation={0}
      sx={{
        p: 2,
        backgroundColor: '#1e293b',
        borderRadius: '12px',
        border: '1px solid #334155',
        display: 'flex',
        flexWrap: 'wrap',
        alignItems: 'center',
        justifyContent: 'space-between',
        gap: 2,
      }}
    >
      {/* Device Selector */}
      <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          <FilterIcon sx={{ color: '#38bdf8', fontSize: 22 }} />
          <Typography variant="subtitle2" sx={{ fontWeight: 700, color: '#f1f5f9' }}>
            Bộ Lọc Hồ Sơ
          </Typography>
        </Box>

        <FormControl size="small" sx={{ minWidth: 160 }}>
          <InputLabel id="history-device-label" sx={{ color: '#94a3b8' }}>
            Mã Thiết Bị
          </InputLabel>
          <Select
            labelId="history-device-label"
            value={selectedDeviceId}
            label="Mã Thiết Bị"
            onChange={(e) => setSelectedDeviceId(e.target.value)}
            sx={{
              color: '#f8fafc',
              '.MuiOutlinedInput-notchedOutline': { borderColor: '#475569' },
              '&:hover .MuiOutlinedInput-notchedOutline': { borderColor: '#3b82f6' },
              '.MuiSvgIcon-root': { color: '#94a3b8' },
            }}
          >
            {availableDevices.map((id) => (
              <MenuItem key={id} value={id}>
                {id}
              </MenuItem>
            ))}
          </Select>
        </FormControl>
      </Box>

      {/* Time Presets */}
      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
        <Typography variant="caption" sx={{ color: '#94a3b8', fontWeight: 600 }}>
          Khoảng thời gian:
        </Typography>
        <ButtonGroup size="small" variant="outlined">
          {presets.map((p) => {
            const isSelected = timePreset === p.value;
            return (
              <Button
                key={p.value}
                onClick={() => setTimePreset(p.value)}
                sx={{
                  backgroundColor: isSelected ? 'rgba(59, 130, 246, 0.2)' : 'transparent',
                  borderColor: isSelected ? '#3b82f6' : '#475569',
                  color: isSelected ? '#60a5fa' : '#94a3b8',
                  fontWeight: isSelected ? 700 : 500,
                  '&:hover': {
                    borderColor: '#3b82f6',
                    backgroundColor: 'rgba(59, 130, 246, 0.1)',
                  },
                }}
              >
                {p.label}
              </Button>
            );
          })}
        </ButtonGroup>
      </Box>

      {/* Query Button */}
      <Box sx={{ display: 'flex', gap: 1 }}>
        <Button
          variant="contained"
          color="primary"
          size="medium"
          startIcon={isLoading ? <CircularProgress size={18} color="inherit" /> : <SearchIcon />}
          onClick={onQuery}
          disabled={isLoading}
          sx={{
            fontWeight: 700,
            backgroundColor: '#2563eb',
            '&:hover': { backgroundColor: '#1d4ed8' },
            px: 2.5,
          }}
        >
          {isLoading ? 'Đang tải...' : 'Truy Vấn Dữ Liệu'}
        </Button>
      </Box>
    </Paper>
  );
};

export default HistoryFilterBar;
