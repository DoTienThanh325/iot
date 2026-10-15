import { useEffect, useRef, useState, useCallback } from 'react';
import useEmergencyStore from '../store/useEmergencyStore';

const WS_BASE_URL = import.meta.env.VITE_WS_BASE_URL || 'ws://localhost:8000';

export const useRealtimeSocket = (deviceId, initialVitals = []) => {
  const wsRef = useRef(null);
  const reconnectTimeoutRef = useRef(null);

  // Lưu trữ ring buffer cho ECG bằng Ref để không gây giật re-render
  // Kích thước buffer 125 * 6 = 750 mẫu (khoảng 6 giây)
  const ecgBufferRef = useRef([]);

  // Store actions
  const setWsConnected = useEmergencyStore((state) => state.setWsConnected);
  const triggerEmergencyAlert = useEmergencyStore((state) => state.triggerEmergencyAlert);

  // States hiển thị trên React DOM (cập nhật 1Hz hoặc khi có kết quả AI)
  const [latestVitals, setLatestVitals] = useState({
    bpm: 75,
    spo2: 98,
    temperature: 36.8,
    svm: 1.02,
    timestamp: new Date().toISOString(),
    posture: 'Đang nằm yên',
  });

  const [liveVitalsHistory, setLiveVitalsHistory] = useState(initialVitals);
  const [aiAnalysis, setAiAnalysis] = useState(null);

  // Cập nhật khi initialVitals thay đổi (ví dụ nạp từ REST API lúc khởi tạo)
  useEffect(() => {
    if (initialVitals && initialVitals.length > 0) {
      setLiveVitalsHistory(initialVitals);
      const last = initialVitals[initialVitals.length - 1];
      if (last) {
        setLatestVitals((prev) => ({
          ...prev,
          bpm: last.bpm ?? prev.bpm,
          spo2: last.spo2 ?? prev.spo2,
          temperature: last.temperature ?? prev.temperature,
          svm: last.svm ?? prev.svm,
          timestamp: last.timestamp || prev.timestamp,
        }));
      }
    }
  }, [initialVitals]);

  const connect = useCallback(() => {
    if (!deviceId) return;

    if (wsRef.current && (wsRef.current.readyState === WebSocket.OPEN || wsRef.current.readyState === WebSocket.CONNECTING)) {
      return;
    }

    const wsUrl = `${WS_BASE_URL}/ws/realtime/${deviceId}`;
    console.log(`Connecting to WebSocket: ${wsUrl}`);

    try {
      const socket = new WebSocket(wsUrl);
      wsRef.current = socket;

      socket.onopen = () => {
        console.log(`WebSocket connected for device ${deviceId}`);
        setWsConnected(true);
      };

      socket.onclose = () => {
        console.warn(`WebSocket disconnected for device ${deviceId}. Reconnecting in 3s...`);
        setWsConnected(false);
        wsRef.current = null;
        reconnectTimeoutRef.current = setTimeout(connect, 3000);
      };

      socket.onerror = (err) => {
        console.error('WebSocket encountered error:', err);
        socket.close();
      };

      socket.onmessage = (event) => {
        try {
          const packet = JSON.parse(event.data);
          const eventType = packet.event_type;
          const payload = packet.data || packet.alert || packet.result || packet;

          switch (eventType) {
            case 'VITALS':
            case 'VITALS_UPDATE': {
              const vitalsData = {
                bpm: payload.bpm ?? 75,
                spo2: payload.spo2 ?? 98,
                temperature: payload.temperature ?? 36.8,
                svm: payload.svm !== undefined ? payload.svm : (payload.max_svm ?? 1.0),
                timestamp: payload.timestamp || new Date().toISOString(),
                posture:
                  payload.svm > 2.5
                    ? 'Phát hiện va chạm'
                    : payload.svm > 1.3
                    ? 'Đang vận động'
                    : 'Đang nằm yên',
              };

              setLatestVitals(vitalsData);

              // Cập nhật biểu đồ trượt 60 giây (tối đa 60 điểm)
              setLiveVitalsHistory((prev) => {
                const updated = [...prev, vitalsData];
                return updated.length > 60 ? updated.slice(updated.length - 60) : updated;
              });
              break;
            }

            case 'ECG':
            case 'ECG_CHUNK': {
              // ECG từ AD8232 (125Hz, thường 25 điểm mỗi gói)
              // Đẩy thẳng vào Ref buffer để Canvas render ở 60fps mà không gọi re-render React!
              const samples = payload.samples || packet.samples || (Array.isArray(payload) ? payload : []);
              if (Array.isArray(samples) && samples.length > 0) {
                // Giữ tối đa 1250 mẫu (~10s) trong buffer để tránh rò rỉ bộ nhớ
                if (ecgBufferRef.current.length > 1250) {
                  ecgBufferRef.current = ecgBufferRef.current.slice(-625);
                }
                ecgBufferRef.current.push(...samples);
              }
              break;
            }

            case 'CRITICAL_ALERT':
            case 'EMERGENCY_ALERT': {
              const alertDoc = {
                _id: payload._id || `alert_${Date.now()}`,
                device_id: payload.device_id || deviceId,
                alert_type: payload.alert_type || 'EMERGENCY',
                severity: payload.severity || 'CRITICAL',
                bpm: payload.bpm,
                spo2: payload.spo2,
                max_svm: payload.max_svm,
                message: payload.message || 'Cảnh báo khẩn cấp từ hệ thống giám sát!',
                timestamp: payload.timestamp || new Date().toISOString(),
                is_acknowledged: false,
              };
              triggerEmergencyAlert(alertDoc);
              break;
            }

            case 'AI_RESULT': {
              setAiAnalysis(payload);
              break;
            }

            default:
              console.debug('Unknown WS event:', packet);
          }
        } catch (e) {
          console.error('Failed to parse WebSocket packet:', e);
        }
      };
    } catch (e) {
      console.error('Failed to create WebSocket instance:', e);
      reconnectTimeoutRef.current = setTimeout(connect, 3000);
    }
  }, [deviceId, setWsConnected, triggerEmergencyAlert]);

  useEffect(() => {
    connect();

    return () => {
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
      }
      if (wsRef.current) {
        wsRef.current.close();
        wsRef.current = null;
      }
      setWsConnected(false);
    };
  }, [connect, setWsConnected]);

  return {
    latestVitals,
    liveVitalsHistory,
    aiAnalysis,
    ecgBufferRef,
  };
};

export default useRealtimeSocket;
