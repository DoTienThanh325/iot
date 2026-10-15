# KẾ HOẠCH TRIỂN KHAI HỆ THỐNG FRONTEND (REACT DASHBOARD)
**Dự án:** Hệ thống IoT Giám sát Sinh hiệu & Cảnh báo Nguy cơ Đột quỵ[cite: 1]  
**Tầng kiến trúc:** Tầng 4 — PRESENTATION (HIỂN THỊ)[cite: 1]

---

## 1. Tổng Quan Kiến Trúc & Lựa Chọn Công Nghệ (Tech Stack)

Tầng **PRESENTATION — HIỂN THỊ** là giao diện trực ban dành cho bác sĩ và y tá, nhận dữ liệu từ tầng **PROCESSING — XỬ LÝ** qua 2 kênh giao tiếp song song[cite: 1]:
* **Nhánh `WebSocket — Realtime`:** Nhận luồng dữ liệu liên tục từ **WebSocket Manager** (gồm sóng điện tim ECG 125Hz, chỉ số sinh tồn 1Hz, tín hiệu **Cảnh báo đỏ nháy** từ **Alert Router** và **Kết quả AI**) để hiển thị tức thì trên **Trang Realtime**[cite: 1].
* **Nhánh `REST — API & lịch sử`:** Gọi các endpoint `/vitals`, `/alerts`, `/history` từ **REST API** để nạp dữ liệu khởi tạo cho **Trang Realtime** và truy vấn dữ liệu quá khứ cho **Trang Lịch sử**[cite: 1].

### Bộ công cụ & Thư viện đề xuất (Tech Stack)

| Nhóm chức năng | Thư viện / Công nghệ | Vai trò & Lý do lựa chọn trong dự án |
| :--- | :--- | :--- |
| **Core & Build Tool** | `React 18` + `Vite` | Khởi tạo dự án nhẹ, tốc độ Hot-Reload nhanh, tối ưu hiệu năng render. |
| **UI Component Library** | `Material UI (MUI v5)` + `@mui/icons-material` | Cung cấp sẵn hệ thống Grid, Card, DataGrid (Bảng lịch sử), Dialog (Modal cấp cứu), Chip, Alert chuẩn giao diện Y tế chuyên nghiệp. |
| **Routing** | `React Router DOM v6` | Điều hướng mượt mà giữa **Trang Realtime** (`/realtime`) và **Trang Lịch sử** (`/history`)[cite: 1]. |
| **State Management** | `Zustand` (hoặc `React Context`) | Quản lý trạng thái toàn cục cho danh sách thiết bị (`device_id`), trạng thái kết nối WebSocket và cờ kích hoạt **Cảnh báo đỏ nháy**[cite: 1]. |
| **HTTP Client** | `Axios` | Giao tiếp với **REST API** (`/vitals`, `/alerts`, `/history`), cấu hình sẵn Base URL và Interceptors xử lý lỗi[cite: 1]. |
| **Biểu đồ Sóng ECG (125Hz)** | `HTML5 Canvas API` (Custom Hook) hoặc `uPlot` | Sóng ECG từ **AD8232** đẩy về 125 điểm/giây[cite: 1]; dùng Canvas trực tiếp giúp vẽ sóng mượt ở tốc độ **60 FPS** mà không làm treo React DOM. |
| **Biểu đồ Sinh hiệu & Lịch sử** | `Recharts` (hoặc `@mui/x-charts`) | Vẽ biểu đồ đường (Line Chart) cho nhịp tim **BPM**, **SpO2**, **Nhiệt độ** trên cả **Trang Realtime** và **Trang Lịch sử**[cite: 1]. |
| **Âm thanh Cảnh báo** | `Web Audio API` | Phát âm thanh còi báo động trên trình duyệt của y tá ngay khi nhận tín hiệu cấp cứu từ **Alert Router**[cite: 1]. |

---

## 2. Cấu Trúc Thư Mục Dự Án (`frontend_react/`)

```text
frontend_react/
├── package.json
├── vite.config.js
├── .env                                    # VITE_API_BASE_URL, VITE_WS_BASE_URL
└── src/
    ├── main.jsx
    ├── App.jsx                             # Cấu hình Theme MUI, Layout chung & React Router
    ├── api/
    │   ├── axiosClient.js                  # Cấu hình Axios kết nối Backend FastAPI
    │   └── vitalsApi.js                    # Các hàm gọi GET /vitals, /alerts, /history & POST /demo/inject-afib
    ├── hooks/
    │   ├── useRealtimeSocket.js            # Quản lý kết nối WebSocket, tự động reconnect & phân loại gói tin
    │   └── useAudioAlert.js                # Phát tiếng còi cảnh báo cấp cứu trên trình duyệt
    ├── store/
    │   └── useEmergencyStore.js            # Lưu trạng thái Cảnh báo đỏ nháy & danh sách Alert chưa xác nhận
    ├── components/
    │   ├── layout/
    │   │   ├── Sidebar.jsx                 # Menu chuyển đổi Trang Realtime / Trang Lịch sử & chọn Thiết bị
    │   │   └── Topbar.jsx                  # Hiển thị trạng thái kết nối MQTT/WebSocket & Nút tắt tiếng còi
    │   ├── realtime/                       # Các component thuộc TRANG REALTIME
    │   │   ├── VitalStatCards.jsx          # 4 thẻ hiển thị số to: BPM, SpO2, Nhiệt độ (°C), Trạng thái MPU6050
    │   │   ├── EcgWaveformCanvas.jsx       # Đồ thị vẽ sóng điện tim AD8232 thời gian thực (60fps)
    │   │   ├── BpmSpo2LiveChart.jsx        # Biểu đồ đường BPM & SpO2 trượt trong 60 giây gần nhất
    │   │   ├── AiDiagnosticPanel.jsx       # Khối hiển thị Kết quả AI (Context-aware, Fall Detect, AFib & HRV)
    │   │   └── CriticalAlertOverlay.jsx    # Khung viền nháy đỏ toàn màn hình & Popup cấp cứu khẩn cấp
    │   └── history/                        # Các component thuộc TRANG LỊCH SỬ
    │       ├── HistoryFilterBar.jsx        # Bộ lọc chọn ngày giờ (From - To), loại chỉ số, mức độ cảnh báo
    │       ├── HistoryTrendChart.jsx       # Biểu đồ tổng hợp lịch sử BPM, SpO2, Nhiệt độ
    │       └── AlertsAndAiTable.jsx        # Bảng dữ liệu (DataGrid) lịch sử cảnh báo & kết quả chẩn đoán AI
    └── pages/
        ├── RealtimePage.jsx                # Trang Realtime (Màn hình trực chính)
        └── HistoryPage.jsx                 # Trang Lịch sử (Tra cứu hồ sơ bệnh nhân)
```

---

## 3. Thiết Kế Chi Tiết 2 Phân Khu Giao Diện Chính

### 3.1. Trang Realtime (`/realtime`) — Giám sát & Cấp cứu Thời gian thực[cite: 1]

Giao diện được chia làm 4 khu vực trực quan trên cùng một màn hình (không cần cuộn trang) để y tá trực ban quan sát toàn diện[cite: 1]:

1. **Hàng 1 — Cụm Thẻ Chỉ Số Sinh Tồn (`VitalStatCards.jsx`):**
   * **Thẻ Nhịp tim (BPM - MAX30102):** Hiển thị con số BPM cỡ lớn kèm icon trái tim đập theo nhịp[cite: 1]. Đổi màu Cam khi `< 50` hoặc `> 100 BPM`, màu Đỏ khi `> 120 BPM`.
   * **Thẻ Nồng độ Oxy (SpO2 - MAX30102):** Hiển thị `%`[cite: 1]. Màu Xanh lá khi `>= 95%`, màu Vàng khi `92% - 94%`, màu Đỏ khi `< 92%`.
   * **Thẻ Nhiệt độ cơ thể (DS18B20):** Hiển thị `°C` (bình thường `36.1°C - 37.2°C`, cảnh báo sốt khi `> 37.5°C`)[cite: 1].
   * **Thẻ Vận động & Tư thế (MPU6050):** Hiển thị lực gia tốc tổng hợp `SVM (g)` và nhãn trạng thái (`Đang nằm yên`, `Đang vận động`, hoặc `Phát hiện va chạm`)[cite: 1].

2. **Hàng 2 (Cột Trái - 65% chiều rộng) — Cụm Biểu Đồ Thời Gian Thực[cite: 1]:**
   * **Đồ thị Dạng sóng ECG (`EcgWaveformCanvas.jsx`):** Nền lưới ô vuông chuẩn giấy đo điện tâm đồ y tế, vẽ đường sóng xanh lá cây chạy liên tục từ trái sang phải với tần số 125 mẫu/giây từ cảm biến **AD8232**[cite: 1].
   * **Biểu đồ BPM & SpO2 (`BpmSpo2LiveChart.jsx`):** Biểu đồ đường kép (`Recharts`) hiển thị biến thiên của BPM và SpO2 trong cửa sổ 60 giây gần nhất[cite: 1].

3. **Hàng 2 (Cột Phải - 35% chiều rộng) — Bảng Điều Khiển Kết Quả AI (`AiDiagnosticPanel.jsx`)[cite: 1]:**
   * **Trạng thái Bộ lọc Ngữ cảnh (`Context-aware`):** Hiển thị kết quả đối chiếu chéo giữa **MAX30102** và **MPU6050**[cite: 1]:
     * Nhãn xanh: `Tín hiệu tin cậy (Bình thường)`.
     * Nhãn xám/vàng: `Lỏng cảm biến SpO2 do cử động tay (Đã chặn báo động giả)`.
     * Nhãn đỏ: `Nguy cơ suy hô hấp cấp (SpO2 tụt khi bệnh nhân bất động)`.
   * **Trạng thái Tầm soát Đột quỵ (`ECG Analysis` & `AFib Detect`):**[cite: 1]
     * Thanh đo xác suất Rung nhĩ `P(AFib)` từ `0%` đến `100%`.
     * Bảng hiển thị trực tiếp 4 chỉ số biến thiên nhịp tim vừa tính từ **AI Service**: `RMSSD (ms)`, `pNN50 (%)`, `CV_RR`, `Shannon Entropy`.
     * Hộp khuyến nghị y khoa: Hiển thị thông báo *"Phát hiện bất thường điện tim - Khuyến nghị tầm soát nguy cơ đột quỵ"* khi phát hiện Rung nhĩ.
   * **Thanh Công cụ Demo (Dành riêng khi bảo vệ đồ án):** Gồm nút bấm **"Giả lập Nạp Sóng Rung Nhĩ (Kịch bản 3)"** gọi thẳng API `POST /api/demo/inject-afib` để hội đồng quan sát AI phản ứng tức thì.

4. **Lớp Phủ Khẩn Cấp — Cảnh Báo Đỏ Nháy (`CriticalAlertOverlay.jsx`)[cite: 1]:**
   * Khi nhận sự kiện ưu tiên cao từ **Alert Router** (`SOS_PRESSED`, `EDGE_FALL_DETECTED`, `FALL_CONFIRMED`, hoặc `RESPIRATORY_RISK`)[cite: 1]:
     * Toàn bộ viền màn hình **Trang Realtime** nháy đỏ liên tục bằng CSS Keyframe (`animation: pulse-red 0.8s infinite`)[cite: 1].
     * Hiển thị Modal cảnh báo chính giữa màn hình: **"CẢNH BÁO KHẨN CẤP: BỆNH NHÂN NGÃ / MẤT Ý THỨC"** (hoặc bấm nút SOS) kèm thời gian và nhịp tim hiện tại[cite: 1].
     * Nút **"Xác nhận đã xử lý (Acknowledge)"**: Khi y tá bấm nút này, Frontend gọi `PATCH /api/alerts/{id}/ack` để tắt còi và tắt hiệu ứng nháy đỏ.

---

### 3.2. Trang Lịch sử (`/history`) — Truy vấn & Phân tích Dữ liệu Quá khứ[cite: 1]

Phục vụ nhu cầu tra cứu lại diễn biến sinh hiệu và lịch sử cảnh báo thông qua nhánh **REST — API & lịch sử**[cite: 1]:

1. **Thanh Bộ Lọc Truy Vấn (`HistoryFilterBar.jsx` — Query REST API)[cite: 1]:**
   * Chọn mã thiết bị / bệnh nhân (`device_id`).
   * Chọn khoảng thời gian nhanh (`15 phút trước`, `1 giờ trước`, `24 giờ qua`) hoặc chọn `DateTimePicker` tùy chỉnh (`start_ts`, `end_ts`).
   * Nút **"Truy vấn dữ liệu"** gọi đồng thời `GET /api/history` và `GET /api/alerts`[cite: 1].

2. **Khu vực Biểu Đồ Lịch Sử (`HistoryTrendChart.jsx`)[cite: 1]:**
   * Biểu đồ vùng/đường (`AreaChart` / `LineChart` của Recharts) có thanh trượt phóng to/thu nhỏ (`Brush`) hiển thị lịch sử **BPM**, **SpO2** và **Nhiệt độ** theo mốc thời gian đã chọn[cite: 1].
   * Cho phép bấm vào một sự kiện cảnh báo trong bảng để xem lại đoạn sóng **ECG** đã lưu tại đúng thời điểm xảy ra bất thường[cite: 1].

3. **Khu vực Bảng Dữ Liệu (`AlertsAndAiTable.jsx`)[cite: 1]:**
   * Chia làm 2 Tab sử dụng `MUI DataGrid` (hỗ trợ phân trang, sắp xếp, xuất CSV):
     * **Tab 1 — Lịch sử Cảnh báo Khẩn cấp (từ collection `alerts`):** Cột Thời gian, Loại cảnh báo (`Nút SOS`, `Ngã`, `Suy hô hấp`), Chỉ số lúc xảy ra, Trạng thái xử lý[cite: 1].
     * **Tab 2 — Nhật ký Phân tích AI (từ collection `ai_results`):** Cột Thời gian, Kết quả Context-aware, Chỉ số `RMSSD`, `pNN50`, `CV_RR`, Xác suất Rung nhĩ `P(AFib)` và Khuyến nghị của AI[cite: 1].

---

## 4. Giải Pháp Kỹ Thuật Cốt Lõi Tại Frontend

### 4.1. Kỹ thuật vẽ sóng ECG 125Hz mượt 60 FPS không gây đơ React
* **Vấn đề:** Cảm biến **AD8232** gửi 125 mẫu/giây (5 gói MQTT/giây, mỗi gói 25 điểm)[cite: 1]. Nếu mỗi khi nhận gói WebSocket ta đều gọi `setEcgData([...prev, ...newSamples])`, React sẽ phải re-render toàn bộ cây DOM liên tục gây giật lag trình duyệt chỉ sau 1–2 phút.
* **Giải pháp triển khai trong `EcgWaveformCanvas.jsx`:**
  * Dùng `useRef` để lưu một mảng vòng (`ecgRingBufferRef.current` có kích thước cố định 625 điểm = 5 giây sóng ECG) nằm ngoài chu kỳ render của React.
  * Khi WebSocket nhận gói `ECG_CHUNK`, chỉ cần đẩy (`push`) các điểm mới vào `ecgRingBufferRef.current` (không gọi `useState`).
  * Dùng vòng lặp `requestAnimationFrame` của trình duyệt kết hợp thẻ `<canvas>` HTML5 để quét và vẽ lại mảng `ecgRingBufferRef.current` ở tốc độ 60 khung hình/giây.

### 4.2. Định dạng gói tin WebSocket thống nhất giữa Backend và React
Để một kết nối WebSocket duy nhất (`ws://localhost:8000/ws/realtime/{device_id}`) gánh được cả 4 luồng dữ liệu trên sơ đồ[cite: 1], **WebSocket Manager** tại Backend sẽ gửi JSON có trường `event_type` để hook `useRealtimeSocket.js` ở React tự động phân luồng:

```javascript
// Cấu trúc phân luồng trong src/hooks/useRealtimeSocket.js
socket.onmessage = (event) => {
  const packet = JSON.parse(event.data);

  switch (packet.event_type) {
    case "VITALS_UPDATE":
      // Cập nhật mỗi 1 giây: BPM, SpO2, Nhiệt độ, Gia tốc MPU6050
      setLatestVitals(packet.data);
      appendLiveChart(packet.data);
      break;

    case "ECG_CHUNK":
      // Cập nhật mỗi 200ms (25 mẫu): Đẩy thẳng vào useRef của Canvas, KHÔNG re-render React
      ecgBufferRef.current.push(...packet.samples);
      break;

    case "CRITICAL_ALERT":
      // Từ Alert Router (Ưu tiên cao): Kích hoạt Cảnh báo đỏ nháy & Còi báo động tức thì
      triggerEmergencyAlert(packet.alert);
      playAlarmSound();
      break;

    case "AI_RESULT":
      // Từ AI Service (mỗi 5-10 giây): Cập nhật bảng Kết quả AI & thông báo nguy cơ đột quỵ
      setAiAnalysis(packet.result);
      break;
  }
};
```

---

## 5. Đặc Tả Tích Hợp REST API (`src/api/vitalsApi.js`)

| Tên hàm trong React | Phương thức & Endpoint Backend[cite: 1] | Tham số truyền vào | Mục đích sử dụng trên Giao diện[cite: 1] |
| :--- | :--- | :--- | :--- |
| `fetchInitialVitals()` | `GET /api/vitals`[cite: 1] | `{ device_id, limit: 60 }` | Nạp 60 giây dữ liệu BPM, SpO2 gần nhất ngay khi người dùng vừa mở **Trang Realtime**[cite: 1]. |
| `fetchVitalsHistory()` | `GET /api/history`[cite: 1] | `{ device_id, start_ts, end_ts }` | Lấy chuỗi dữ liệu `vitals`, `ecg`, `accel` từ **MongoDB** để vẽ biểu đồ trên **Trang Lịch sử**[cite: 1]. |
| `fetchAlertsAndAiLogs()` | `GET /api/alerts`[cite: 1] | `{ device_id, limit: 100 }` | Lấy danh sách bản ghi từ collection `alerts` và `ai_results` hiển thị lên bảng ở **Trang Lịch sử**[cite: 1]. |
| `acknowledgeAlert()` | `PATCH /api/alerts/{id}/ack`[cite: 1] | `alert_id` | Xác nhận đã xử lý cấp cứu, tắt trạng thái **Cảnh báo đỏ nháy** trên **Trang Realtime**[cite: 1]. |
| `triggerAfibDemo()` | `POST /api/demo/inject-afib` | `{ device_id }` | Nút bấm phục vụ **Kịch bản Demo 3**: Nạp sóng ECG Rung nhĩ để test hiển thị **Kết quả AI**[cite: 1]. |

---

## 6. Lộ Trình Triển Khai Frontend (3 Tuần) & Kịch Bản Nghiệm Thu

### Lộ trình thực hiện theo tuần
* **Tuần 1 — Dựng Khung Dự Án, Layout & Trang Lịch Sử (`REST API`):**
  * Khởi tạo Vite + React + Material UI, cấu hình `React Router` cho 2 trang `/realtime` và `/history`[cite: 1].
  * Xây dựng `axiosClient.js` và hoàn thiện **Trang Lịch sử** (`HistoryFilterBar`, `HistoryTrendChart`, `AlertsAndAiTable`) sử dụng dữ liệu mẫu hoặc kết nối vào **REST API** (`/vitals`, `/alerts`, `/history`)[cite: 1].
* **Tuần 2 — Xây dựng Trang Realtime & Đồ thị Sóng ECG (`WebSocket`):**
  * Viết custom hook `useRealtimeSocket.js` kết nối vào **WebSocket Manager** của Backend FastAPI[cite: 1].
  * Xây dựng `VitalStatCards.jsx`, `BpmSpo2LiveChart.jsx` và đặc biệt là `EcgWaveformCanvas.jsx` vẽ sóng điện tim **AD8232** mượt ở tốc độ 60 FPS[cite: 1].
* **Tuần 3 — Tích hợp Cảnh Báo Đỏ Nháy, Kết Quả AI & Ghép Nối Demo:**
  * Xây dựng `CriticalAlertOverlay.jsx` (hiệu ứng nháy đỏ toàn màn hình + âm thanh còi báo động) và `AiDiagnosticPanel.jsx` hiển thị kết quả từ **AI Service**[cite: 1].
  * Khớp nối toàn trình với Backend và mạch **ESP32** để chạy thử nghiệm 3 kịch bản Demo[cite: 1].

### Bảng Tiêu Chí Nghiệm Thu Giao Diện Theo 3 Kịch Bản Demo

| Kịch bản Demo | Thao tác thực hiện | Phản ứng kỳ vọng trên React Dashboard[cite: 1] |
| :--- | :--- | :--- |
| **1. Trạng thái Ổn định** | Mở **Trang Realtime**, bệnh nhân đeo cảm biến nghỉ ngơi bình thường[cite: 1]. | 4 thẻ chỉ số hiển thị màu xanh ổn định; đường sóng ECG trên Canvas chạy mượt không giật lag; khung **Kết quả AI** báo `NORMAL_SINUS`[cite: 1]. |
| **2. Cấp cứu Tự động (Real-time)** | Thả rơi/vung mạnh cảm biến **MPU6050** hoặc bấm **Nút SOS** trên mạch ESP32[cite: 1]. | Trong vòng `< 200ms`, màn hình **Trang Realtime** chuyển sang **Cảnh báo đỏ nháy** toàn viền, phát tiếng còi báo động và bật Popup *"Bệnh nhân ngã / Mất ý thức"*[cite: 1]. |
| **3. Phát hiện Nguy cơ Đột quỵ (AI)** | Bấm nút nạp dữ liệu giả lập Rung nhĩ (hoặc truyền sóng AFib qua MQTT). | Khung **Kết quả AI** cập nhật các chỉ số `RMSSD >= 100ms`, `pNN50 >= 50%`, thanh xác suất `P(AFib)` vọt lên màu đỏ (`> 70%`) và hiển thị hộp cảnh báo: *"Phát hiện bất thường điện tim - Khuyến nghị tầm soát nguy cơ đột quỵ"*; đồng thời bản ghi mới xuất hiện ngay bên bảng của **Trang Lịch sử**[cite: 1]. |