import { create } from 'zustand';

export const useEmergencyStore = create((set, get) => ({
  // Thiết bị hiện tại đang quan sát
  selectedDeviceId: 'esp32_01',
  availableDevices: ['esp32_01', 'esp32_02', 'esp32_03'],

  // Trạng thái kết nối
  isWsConnected: false,
  isBackendHealthy: true,

  // Trạng thái cảnh báo khẩn cấp (Cảnh báo đỏ nháy)
  isCriticalActive: false,
  activeAlert: null, // Gói alert khẩn cấp hiện tại
  unacknowledgedAlerts: [],

  // Tùy chọn âm thanh
  isMuted: false,

  // Actions
  setSelectedDeviceId: (deviceId) => set({ selectedDeviceId: deviceId }),

  setWsConnected: (status) => set({ isWsConnected: status }),
  setBackendHealthy: (status) => set({ isBackendHealthy: status }),

  toggleMute: () => set((state) => ({ isMuted: !state.isMuted })),
  setMuted: (muted) => set({ isMuted: muted }),

  triggerEmergencyAlert: (alert) => {
    set((state) => {
      const exists = state.unacknowledgedAlerts.some((a) => a._id === alert._id);
      const updatedList = exists
        ? state.unacknowledgedAlerts
        : [alert, ...state.unacknowledgedAlerts];
      return {
        isCriticalActive: true,
        activeAlert: alert,
        unacknowledgedAlerts: updatedList,
      };
    });
  },

  dismissActiveModal: () => {
    set({ isCriticalActive: false, activeAlert: null });
  },

  acknowledgeAlertInStore: (alertId) => {
    set((state) => {
      const remaining = state.unacknowledgedAlerts.filter(
        (a) => a._id !== alertId && a.id !== alertId
      );
      const stillActive = remaining.length > 0;
      return {
        unacknowledgedAlerts: remaining,
        isCriticalActive: stillActive,
        activeAlert: stillActive ? remaining[0] : null,
      };
    });
  },
}));

export default useEmergencyStore;
