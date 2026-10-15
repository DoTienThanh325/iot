import React, { useState } from 'react';
import {
  Paper,
  Box,
  Typography,
  Tabs,
  Tab,
  Chip,
  Button,
  IconButton,
  Tooltip,
} from '@mui/material';
import { DataGrid } from '@mui/x-data-grid';
import {
  Download as DownloadIcon,
  CheckCircle as CheckCircleIcon,
  Warning as WarningIcon,
  Sos as SosIcon,
  Psychology as AiIcon,
} from '@mui/icons-material';
import vitalsApi from '../../api/vitalsApi';

export const AlertsAndAiTable = ({ alerts = [], aiResults = [], onRefresh }) => {
  const [tabIndex, setTabIndex] = useState(0);

  // Xử lý xác nhận nhanh cảnh báo ngay trong bảng
  const handleQuickAck = async (id) => {
    try {
      await vitalsApi.acknowledgeAlert(id, 'Bác sĩ / Y tá', 'Đã kiểm tra hồ sơ');
      if (onRefresh) onRefresh();
    } catch (err) {
      console.error('Error ack alert:', err);
    }
  };

  // Xuất file CSV
  const exportToCsv = (filename, rows) => {
    if (!rows || rows.length === 0) {
      alert('Không có dữ liệu để xuất file!');
      return;
    }
    const headers = Object.keys(rows[0]).join(',');
    const values = rows.map((r) =>
      Object.values(r)
        .map((v) => `"${(v ?? '').toString().replace(/"/g, '""')}"`)
        .join(',')
    );
    const csvContent = 'data:text/csv;charset=utf-8,\uFEFF' + [headers, ...values].join('\n');
    const encodedUri = encodeURI(csvContent);
    const link = document.createElement('a');
    link.setAttribute('href', encodedUri);
    link.setAttribute('download', filename);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  // Cột cho Tab 1: Cảnh Báo Khẩn Cấp
  const alertColumns = [
    {
      field: 'timestamp',
      headerName: 'Thời Gian',
      width: 180,
      renderCell: (params) => (
        <Typography variant="caption" sx={{ fontFamily: 'Roboto Mono', color: '#e2e8f0' }}>
          {params.value ? new Date(params.value).toLocaleString('vi-VN') : '--'}
        </Typography>
      ),
    },
    {
      field: 'alert_type',
      headerName: 'Loại Cảnh Báo',
      width: 190,
      renderCell: (params) => {
        const type = params.value;
        let color = 'default';
        let label = type;
        if (type === 'SOS_PRESSED') {
          color = 'error';
          label = 'Nút Khẩn SOS';
        } else if (type === 'FALL_CONFIRMED' || type === 'EDGE_FALL_DETECTED') {
          color = 'error';
          label = 'Phát hiện Ngã';
        } else if (type === 'RESPIRATORY_RISK') {
          color = 'warning';
          label = 'Suy Hô Hấp (SpO2)';
        } else if (type === 'AFIB_HIGH_RISK') {
          color = 'error';
          label = 'Rung Nhĩ (AFib)';
        }
        return <Chip size="small" label={label} color={color} sx={{ fontWeight: 600 }} />;
      },
    },
    {
      field: 'vitals_snapshot',
      headerName: 'Chỉ Số Khi Xảy Ra',
      width: 220,
      valueGetter: (value, row) => `BPM: ${row.bpm ?? '--'} | SpO2: ${row.spo2 ? `${row.spo2}%` : '--'} | SVM: ${row.max_svm ? `${row.max_svm.toFixed(2)}g` : '--'}`,
      renderCell: (params) => (
        <Typography variant="caption" sx={{ fontFamily: 'Roboto Mono', color: '#94a3b8' }}>
          {params.value}
        </Typography>
      ),
    },
    {
      field: 'message',
      headerName: 'Nội Dung Chi Tiết',
      flex: 1,
      minWidth: 240,
    },
    {
      field: 'is_acknowledged',
      headerName: 'Trạng Thái',
      width: 140,
      renderCell: (params) => (
        <Chip
          size="small"
          label={params.value ? 'Đã Xử Lý' : 'Chưa Xử Lý'}
          color={params.value ? 'success' : 'error'}
          variant={params.value ? 'outlined' : 'filled'}
          sx={{ fontWeight: 600, height: 22 }}
        />
      ),
    },
    {
      field: 'actions',
      headerName: 'Thao Tác',
      width: 120,
      renderCell: (params) => {
        if (params.row.is_acknowledged) return null;
        return (
          <Button
            size="small"
            variant="contained"
            color="success"
            onClick={() => handleQuickAck(params.row.id)}
            sx={{ fontSize: '0.7rem', py: 0.2 }}
          >
            Xử Lý
          </Button>
        );
      },
    },
  ];

  // Chuẩn hóa dữ liệu Alerts
  const alertRows = alerts.map((item, idx) => ({
    id: item._id || `alt_${idx}`,
    timestamp: item.timestamp,
    alert_type: item.alert_type,
    bpm: item.bpm,
    spo2: item.spo2,
    max_svm: item.max_svm,
    message: item.message,
    is_acknowledged: item.is_acknowledged || false,
  }));

  // Cột cho Tab 2: Nhật Ký AI
  const aiColumns = [
    {
      field: 'timestamp',
      headerName: 'Thời Gian',
      width: 180,
      renderCell: (params) => (
        <Typography variant="caption" sx={{ fontFamily: 'Roboto Mono', color: '#e2e8f0' }}>
          {params.value ? new Date(params.value).toLocaleString('vi-VN') : '--'}
        </Typography>
      ),
    },
    {
      field: 'context_status',
      headerName: 'Bộ Lọc Ngữ Cảnh',
      width: 200,
      renderCell: (params) => {
        const val = params.value;
        let color = 'success';
        let text = 'Tin cậy (Bình thường)';
        if (val === 'MOTION_ARTIFACT') {
          color = 'warning';
          text = 'Nhiễu do cử động';
        } else if (val === 'RESPIRATORY_RISK') {
          color = 'error';
          text = 'Nguy cơ suy hô hấp';
        }
        return <Chip size="small" label={text} color={color} sx={{ fontWeight: 600 }} />;
      },
    },
    {
      field: 'afib_probability',
      headerName: 'Xác Suất AFib',
      width: 140,
      renderCell: (params) => {
        const val = typeof params.value === 'number' ? Math.round(params.value * 100) : 0;
        const color = val >= 70 ? '#ef4444' : val >= 40 ? '#f59e0b' : '#10b981';
        return (
          <Typography variant="body2" sx={{ fontFamily: 'Roboto Mono', fontWeight: 700, color }}>
            {val}%
          </Typography>
        );
      },
    },
    {
      field: 'rmssd',
      headerName: 'RMSSD (ms)',
      width: 120,
      valueGetter: (value, row) => (row.hrv_metrics?.rmssd ? row.hrv_metrics.rmssd.toFixed(1) : '--'),
    },
    {
      field: 'pnn50',
      headerName: 'pNN50 (%)',
      width: 110,
      valueGetter: (value, row) => (row.hrv_metrics?.pnn50 ? row.hrv_metrics.pnn50.toFixed(1) : '--'),
    },
    {
      field: 'recommendation',
      headerName: 'Khuyến Nghị Y Khoa Của AI',
      flex: 1,
      minWidth: 260,
    },
  ];

  // Chuẩn hóa dữ liệu AI
  const aiRows = aiResults.map((item, idx) => ({
    id: item._id || `ai_${idx}`,
    timestamp: item.timestamp,
    context_status: item.context_status || 'RELIABLE_NORMAL',
    afib_probability: item.afib_probability,
    afib_detected: item.afib_detected,
    hrv_metrics: item.hrv_metrics,
    recommendation: item.recommendation || (item.afib_detected ? 'Phát hiện bất thường điện tim - Khuyến nghị tầm soát nguy cơ đột quỵ' : 'Bình thường'),
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
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 1 }}>
        <Tabs
          value={tabIndex}
          onChange={(e, val) => setTabIndex(val)}
          sx={{
            minHeight: 36,
            '& .MuiTab-root': {
              minHeight: 36,
              py: 0.5,
              fontWeight: 700,
              fontSize: '0.85rem',
              color: '#94a3b8',
              '&.Mui-selected': { color: '#38bdf8' },
            },
          }}
        >
          <Tab
            icon={<WarningIcon sx={{ fontSize: 18 }} />}
            iconPosition="start"
            label={`Lịch Sử Cảnh Báo Khẩn Cấp (${alertRows.length})`}
          />
          <Tab
            icon={<AiIcon sx={{ fontSize: 18 }} />}
            iconPosition="start"
            label={`Nhật Ký Phân Tích AI (${aiRows.length})`}
          />
        </Tabs>

        <Button
          variant="outlined"
          size="small"
          startIcon={<DownloadIcon />}
          onClick={() => {
            if (tabIndex === 0) {
              exportToCsv('lich_su_canh_bao_cap_cuu.csv', alertRows);
            } else {
              exportToCsv('nhat_ky_ai_chan_doan.csv', aiRows);
            }
          }}
          sx={{
            borderColor: '#475569',
            color: '#38bdf8',
            '&:hover': { borderColor: '#38bdf8', backgroundColor: 'rgba(56, 189, 248, 0.1)' },
          }}
        >
          Xuất Báo Cáo CSV
        </Button>
      </Box>

      {/* DataGrid Container */}
      <Box sx={{ height: 380, width: '100%' }}>
        <DataGrid
          rows={tabIndex === 0 ? alertRows : aiRows}
          columns={tabIndex === 0 ? alertColumns : aiColumns}
          pageSize={10}
          rowsPerPageOptions={[10, 25, 50]}
          disableSelectionOnClick
          sx={{
            border: 'none',
            color: '#f8fafc',
            '& .MuiDataGrid-columnHeaders': {
              backgroundColor: '#0f172a',
              color: '#94a3b8',
              fontWeight: 700,
              borderBottom: '1px solid #334155',
            },
            '& .MuiDataGrid-row': {
              borderBottom: '1px solid #334155',
              '&:hover': {
                backgroundColor: 'rgba(255, 255, 255, 0.03)',
              },
            },
            '& .MuiDataGrid-cell': {
              borderBottom: '1px solid #334155',
            },
            '& .MuiDataGrid-footerContainer': {
              backgroundColor: '#0f172a',
              borderTop: '1px solid #334155',
              color: '#94a3b8',
            },
            '& .MuiTablePagination-root': {
              color: '#94a3b8',
            },
          }}
        />
      </Box>
    </Paper>
  );
};

export default AlertsAndAiTable;
