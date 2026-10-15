import axiosClient from './axiosClient';

export const vitalsApi = {
  // Lấy danh sách vitals gần nhất (khởi tạo màn hình realtime)
  fetchInitialVitals: async (deviceId, limit = 60) => {
    return await axiosClient.get('/api/vitals', {
      params: { device_id: deviceId, limit },
    });
  },

  // Truy vấn lịch sử dữ liệu sinh hiệu & ECG
  fetchVitalsHistory: async (deviceId, startTs, endTs, limit = 500) => {
    const params = { device_id: deviceId, limit };
    if (startTs !== undefined && startTs !== null) params.start_ts = startTs;
    if (endTs !== undefined && endTs !== null) params.end_ts = endTs;
    return await axiosClient.get('/api/history', { params });
  },

  // Lấy lịch sử cảnh báo & nhật ký AI
  fetchAlertsAndAiLogs: async (deviceId, type = 'all', limit = 100) => {
    const params = { type, limit };
    if (deviceId) params.device_id = deviceId;
    return await axiosClient.get('/api/alerts', { params });
  },

  // Xác nhận xử lý cảnh báo (Acknowledge)
  acknowledgeAlert: async (alertId, acknowledgedBy = 'Y tá trực ban', note = 'Đã kiểm tra bệnh nhân') => {
    return await axiosClient.patch(`/api/alerts/${alertId}/ack`, {
      acknowledged_by: acknowledgedBy,
      note: note,
    });
  },

  // Kịch bản Demo 3: Nạp dữ liệu sóng Rung Nhĩ (AFib) giả lập vào Backend
  triggerAfibDemo: async (deviceId = 'esp32_01') => {
    return await axiosClient.post('/api/demo/inject-afib', {
      device_id: deviceId,
    });
  },

  // Kiểm tra sức khỏe dịch vụ Backend
  checkHealth: async () => {
    return await axiosClient.get('/health');
  },
};

export default vitalsApi;
