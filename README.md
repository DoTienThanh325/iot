# HỆ THỐNG IoT GIÁM SÁT SINH HIỆU & CẢNH BÁO NGUY CƠ ĐỘT QUỴ
## TẦNG 4: PRESENTATION (FRONTEND REACT DASHBOARD)

> Giao diện trực ban thời gian thực chuẩn y tế dành cho y bác sĩ và điều dưỡng trong việc theo dõi liên tục bệnh nhân tại giường bệnh hoặc từ xa, phát hiện sớm nguy cơ đột quỵ và kích hoạt cấp cứu khẩn cấp.

---

## 1. Giới Thiệu Dự Án

Frontend là phân hệ hiển thị của đồ án **"Hệ Thống IoT Giám Sát Sinh Hiệu & Cảnh Báo Nguy Cơ Đột Quỵ"**. Giao diện nhận dữ liệu từ **Tầng 3 (Processing Backend)** thông qua 2 kênh giao tiếp song song:
1. **Kênh WebSocket Realtime (`/ws/realtime/{device_id}`):** Tiếp nhận dữ liệu truyền phát liên tục ở tần số cao:
   - Sóng điện tim ECG **125 Hz** từ cảm biến **AD8232**.
   - Chỉ số sinh tồn **1 Hz** từ cảm biến **MAX30102** (BPM, SpO2) và **DS18B20** (Thân nhiệt).
   - Dữ liệu gia tốc cử động & tư thế từ **MPU6050** (SVM).
   - Tín hiệu kích hoạt **Cảnh Báo Đỏ Nháy** từ **Alert Router**.
   - Kết quả chẩn đoán từ **AI Service** (Context-aware, Phân tích Rung nhĩ AFib & biến thiên nhịp tim HRV).
2. **Kênh REST API (`/api/vitals`, `/api/history`, `/api/alerts`, `/api/demo`):** Truy vấn dữ liệu khởi tạo, lịch sử chuỗi thời gian, nhật ký cảnh báo và kích hoạt các kịch bản demo phục vụ bảo vệ đồ án.

---

## 2. Công Nghệ Sử Dụng (Tech Stack)

| Nhóm công nghệ | Công cụ / Thư viện | Vai trò kỹ thuật trong hệ thống |
| :--- | :--- | :--- |
| **Core & Build Tool** | `React` + `Vite` | Khởi tạo siêu nhẹ, Hot Module Replacement (HMR) tức thì, build bundle tối ưu. |
| **Giao diện & Thành phần** | `Material UI (MUI v5)` + `@mui/icons-material` | Hệ thống Grid, Card, Dialog cấp cứu, Tabs, Chip theo phong cách Dark Medical chuyên nghiệp. |
| **Bảng Dữ Liệu Lịch Sử** | `@mui/x-data-grid` | Bảng dữ liệu y tế hiệu năng cao, hỗ trợ phân trang, lọc, sắp xếp và xử lý nhanh. |
| **Điều Hướng Trang** | `React Router DOM v6` | Chuyển đổi mượt mà giữa **Trang Realtime** (`/realtime`) và **Trang Lịch Sử** (`/history`). |
| **Quản Lý Trạng Thái Toàn Cục** | `Zustand` | Quản lý thiết bị (`device_id`), trạng thái kết nối WebSocket, cờ kích hoạt Cảnh báo đỏ nháy và danh sách cấp cứu chưa xử lý. |
| **HTTP Client** | `Axios` | Giao tiếp REST API với Backend FastAPI, cấu hình Base URL và xử lý lỗi tập trung. |
| **Vẽ Sóng ECG (125Hz @ 60 FPS)** | `HTML5 Canvas API` + `requestAnimationFrame` | Cơ chế **Ring Buffer ngoài React DOM (useRef)** giúp vẽ sóng điện tâm đồ mượt mà 60 FPS mà hoàn toàn không gây lag hay treo trình duyệt. |
| **Biểu Đồ Sinh Hiệu & Xu Hướng** | `Recharts` | Biểu đồ đường kép (Dual Y-Axis) cho BPM & SpO2 trượt 60 giây và biểu đồ vùng đa biến có thanh trượt Brush thu phóng thời gian. |
| **Âm Thanh Còi Cấp Cứu** | `Web Audio API` | Tự động tổng hợp âm thanh còi báo động cấp cứu trực tiếp trên trình duyệt mà không cần tải file MP3 phụ thuộc. |

---

## 3. Cấu Trúc Thư Mục Dự Án

```text
frontend/
├── package.json               # Cấu hình dự án, scripts & dependencies
├── vite.config.js             # Cấu hình Vite & tối ưu tách nhỏ gói bundle (code-splitting)
├── .env                       # Biến môi trường API & WebSocket URL
├── index.html                 # Entrypoint HTML & font chữ y tế Roboto
├── plan.md                    # Bản kế hoạch triển khai kiến trúc chi tiết
├── README.md                  # Hướng dẫn dự án và tài liệu vận hành
└── src/
    ├── main.jsx               # Điểm khởi tạo ứng dụng React
    ├── App.jsx                # Cấu hình Theme MUI Dark Medical, Router & Layout chính
    ├── api/
    │   ├── axiosClient.js     # Axios instance với baseURL và Interceptor
    │   └── vitalsApi.js       # Gọi các API: /vitals, /history, /alerts, /demo/inject-afib
    ├── hooks/
    │   ├── useRealtimeSocket.js # Quản lý WebSocket, tự reconnect & điều phối gói tin
    │   └── useAudioAlert.js     # Bộ phát âm thanh còi cấp cứu bằng Web Audio API
    ├── store/
    │   └── useEmergencyStore.js # Zustand store quản lý cảnh báo đỏ nháy & thiết bị
    ├── components/
    │   ├── layout/
    │   │   ├── Sidebar.jsx    # Menu điều hướng, chọn mã thiết bị ESP32, phòng bệnh
    │   │   └── Topbar.jsx     # Đồng hồ thời gian thực, trạng thái kết nối & nút tắt còi
    │   ├── realtime/          # Các thành phần TRANG REALTIME
    │   │   ├── VitalStatCards.jsx       # 4 thẻ chỉ số lớn (BPM, SpO2, Thân nhiệt, MPU6050)
    │   │   ├── EcgWaveformCanvas.jsx    # Lưới điện tim y tế & đồ thị ECG 125Hz 60 FPS
    │   │   ├── BpmSpo2LiveChart.jsx     # Biểu đồ trượt 60s nhịp tim & nồng độ oxy
    │   │   ├── AiDiagnosticPanel.jsx    # Panel AI: Context-aware, AFib meter, HRV & Demo tool
    │   │   └── CriticalAlertOverlay.jsx # Viền nháy đỏ toàn màn hình & Popup cấp cứu
    │   └── history/           # Các thành phần TRANG LỊCH SỬ
    │       ├── HistoryFilterBar.jsx     # Bộ lọc theo thiết bị và khoảng thời gian (15m, 1h, 6h, 24h)
    │       ├── HistoryTrendChart.jsx    # Biểu đồ lịch sử đa chỉ số (có Brush) & xem lại sóng ECG
    │       └── AlertsAndAiTable.jsx     # Bảng DataGrid lịch sử cảnh báo & nhật ký AI, xuất CSV
    └── pages/
        ├── RealtimePage.jsx   # Màn hình trực ban giám sát thời gian thực
        └── HistoryPage.jsx    # Màn hình tra cứu hồ sơ & lịch sử bệnh nhân
```

---

## 4. Các Tính Năng Chi Tiết

### 4.1. Trang Giám Sát Thời Gian Thực (`/realtime`)
- **4 Thẻ Chỉ Số Sinh Tồn Cỡ Lớn:**
  - **Nhịp tim (BPM):** Cảm biến MAX30102, biểu tượng trái tim đập nhịp nhàng theo nhịp tim thực; đổi màu Cam khi `< 50` hoặc `> 100 BPM`, chuyển Đỏ khi `> 120 BPM`.
  - **Nồng độ Oxy (SpO2 %):** MAX30102, Xanh lá khi `>= 95%`, Vàng khi `92% - 94%`, Đỏ nguy cấp khi `< 92%`.
  - **Thân nhiệt (°C):** Cảm biến DS18B20 với ngưỡng sốt cảnh báo (`> 37.5°C`).
  - **Vận động & Tư thế (MPU6050):** Đo gia tốc tổng hợp `SVM (g)` kèm phân loại trạng thái: *Đang nằm yên*, *Đang vận động*, hoặc *Phát hiện va chạm*.
- **Đồ Thị Sóng Điện Tâm Đồ ECG (60 FPS):**
  - Vẽ trực tiếp trên thẻ Canvas với tần số 125 mẫu/giây từ cảm biến AD8232.
  - Nền lưới chuẩn giấy đo điện tim y tế với vạch 1mm và 5mm.
  - Con trỏ quét tia sáng (Sweep Line) và cơ chế bộ nhớ đệm vòng (Ring Buffer) triệt tiêu hoàn toàn hiện tượng nghẽn giao diện.
  - Nút thu phóng biên độ sóng (Zoom Gain) và làm mới đường quét.
- **Biểu Đồ Trượt 60 Giây BPM & SpO2:**
  - Biểu đồ đường kép (Dual Axis) hiển thị rõ mối tương quan giữa biến thiên nhịp tim và nồng độ oxy máu.
- **Bảng Điều Khiển Kết Quả Phân Tích AI:**
  - **Bộ lọc Ngữ cảnh (Context-aware):** Đối chiếu chéo giữa SpO2 và MPU6050 để loại bỏ báo động giả khi cử động tay (`MOTION_ARTIFACT`) và phát hiện nguy cơ suy hô hấp khi bệnh nhân bất động (`RESPIRATORY_RISK`).
  - **Thanh Đo Xác Suất Rung Nhĩ $P(\text{AFib})$:** Thước đo trực quan từ 0% đến 100% kèm nhãn cảnh báo nguy cơ đột quỵ màu đỏ khi $P \ge 70\%$.
  - **Bảng Chỉ Số Biến Thiên Nhịp Tim (HRV Metrics):** Cập nhật liên tục `RMSSD (ms)`, `pNN50 (%)`, `CV_RR` và `Shannon Entropy`.
  - **Hộp Khuyến Nghị Y Khoa:** Đưa ra chỉ định y tế tức thì khi phát hiện sóng bất thường.
  - **Nút Bấm Demo:** Nút *"Giả Lập Sóng Rung Nhĩ (Kịch bản 3)"* kích hoạt API nạp sóng bất thường để hội đồng nghiệm thu quan sát phản xạ của AI trong vòng 1-2 giây.
- **Lớp Phủ Cấp Cứu Khẩn Cấp (Critical Alert Overlay):**
  - Viền nháy đỏ toàn màn hình (`animation: pulse-red 0.8s infinite`) khi có tín hiệu cấp cứu (`SOS_PRESSED`, `FALL_CONFIRMED`, `RESPIRATORY_RISK`, `AFIB_HIGH_RISK`).
  - Còi báo động y tế tự động hú qua Web Audio API (có nút tắt nhanh âm thanh trên Topbar).
  - Cửa sổ Popup trung tâm hiển thị thời điểm, loại nguy hiểm, chỉ số khi xảy ra và nút **"Xác Nhận Đã Xử Lý (Acknowledge)"** để gửi phản hồi lên Backend.

### 4.2. Trang Lịch Sử & Tra Cứu (`/history`)
- **Thanh Bộ Lọc Nhanh:** Chọn mã thiết bị (`esp32_01`, `esp32_02`, ...) và chọn khoảng thời gian (`15m`, `1h`, `6h`, `24h`) để truy vấn từ MongoDB.
- **Biểu Đồ Xu Hướng Lịch Sử Đa Biến:** Cho phép xem lại diễn biến nhịp tim, oxy máu và thân nhiệt xuyên suốt khoảng thời gian điều trị; hỗ trợ thanh trượt Brush để phóng to chi tiết từng phút.
- **Xem Lại Đoạn Sóng ECG Đã Lưu:** Cho phép xem lại đồ thị sóng ECG 125Hz nguyên bản tại các thời điểm xảy ra sự cố.
- **Bảng Dữ Liệu Phân Tách 2 Tab (MUI DataGrid):**
  - **Tab 1: Lịch sử Cảnh báo Khẩn cấp:** Theo dõi các lần bấm nút SOS, ngã hoặc suy hô hấp; hỗ trợ nút xử lý nhanh từng ca trực.
  - **Tab 2: Nhật ký Phân tích AI:** Theo dõi lịch sử đánh giá của AI Service theo từng cửa sổ trượt.
  - **Xuất Báo Cáo CSV:** Nút tải file báo cáo dữ liệu định dạng `.csv` hỗ trợ lưu trữ hồ sơ bệnh án.

---

## 5. Hướng Dẫn Cài Đặt & Chạy Ứng Dụng

### 5.1. Yêu cầu hệ thống
- **Node.js:** Phiên bản `>= 18.0.0` (Khuyến nghị Node.js v20 LTS).
- **Trình duyệt:** Chrome, Edge, Firefox, Brave (hỗ trợ Web Audio API & HTML5 Canvas).
- **Backend FastAPI:** Đang chạy tại `http://localhost:8000` (hoặc cấu hình lại trong file `.env`).

### 5.2. Cài đặt các gói phụ thuộc
Tại thư mục `frontend`:
```bash
npm install
```

### 5.3. Cấu hình biến môi trường
File cấu hình `.env` mặc định:
```env
VITE_API_BASE_URL=http://localhost:8000
VITE_WS_BASE_URL=ws://localhost:8000
```
> Nếu chạy Backend trên máy chủ khác trong mạng LAN/Internet, hãy thay `localhost` bằng địa chỉ IP máy chủ (ví dụ `http://192.168.1.50:8000`).

### 5.4. Chạy chế độ Phát triển (Development Mode)
```bash
npm run dev
```
Sau khi chạy, giao diện sẽ sẵn sàng tại địa chỉ:
👉 **`http://localhost:3000`**

### 5.5. Đóng gói cho Môi trường Triển khai Thực tế (Production Build)
```bash
npm run build
```
Kết quả đóng gói nằm trong thư mục `dist/`. Bạn có thể kiểm tra bản build bằng:
```bash
npm run preview
```

---

## 6. Kịch Bản Nghiệm Thu & Demo (3 Scenarios)

Dự án được thiết kế để vượt qua đầy đủ 3 kịch bản kiểm thử trực quan:

| Kịch bản Demo | Thao tác thực hiện | Hiện tượng hiển thị trên Dashboard |
| :--- | :--- | :--- |
| **Kịch bản 1: Trạng thái Ổn Định** | Mở trang `/realtime`, thiết bị ESP32 truyền dữ liệu bình thường. | 4 thẻ chỉ số hiển thị màu xanh lá; sóng ECG trên Canvas quét đều đặn 60 FPS không giật lag; panel AI hiển thị nhãn `Tín hiệu tin cậy`, xác suất Rung nhĩ $< 10\%$. |
| **Kịch bản 2: Cấp cứu Tự Động (Real-time)** | Bấm nút **SOS** trên mạch ESP32 hoặc làm rơi cảm biến **MPU6050** ($SVM > 2.5g$). | Trong vòng **$< 200\text{ms}$**, viền màn hình nháy đỏ liên tục, còi báo động y tế vang lên, Popup cấp cứu khẩn cấp bật mở; y tá bấm nút **"Xác nhận đã xử lý"** để tắt còi và ghi nhận hồ sơ. |
| **Kịch bản 3: Tầm soát Nguy cơ Đột quỵ (AI)** | Bấm nút **"Giả Lập Sóng Rung Nhĩ (Kịch bản 3)"** trên panel AI. | Thanh đo xác suất $P(\text{AFib})$ lập tức vọt lên **$\ge 70\%$** (chuyển sang màu đỏ); chỉ số `RMSSD` và `pNN50` tăng cao; hộp khuyến nghị chuyển sang thông báo nguy cơ đột quỵ cấp và dữ liệu được lưu tức thì vào bảng Lịch sử. |

---

## 7. Giấy Phép & Bản Quyền
Dự án được phát triển phục vụ mục đích nghiên cứu, học tập và triển khai đồ án giải pháp IoT Y Tế thông minh.
