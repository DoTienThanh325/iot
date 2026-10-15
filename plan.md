# KẾ HOẠCH TRIỂN KHAI HỆ THỐNG PROCESSING BACKEND & AI SERVICE (FASTAPI)
**Dự án:** Hệ thống IoT Giám sát Sinh hiệu & Cảnh báo Nguy cơ Đột quỵ[cite: 1]

---

## 1. Tổng Quan Kiến Trúc & Luồng Dữ Liệu

Hệ thống tầng **PROCESSING — XỬ LÝ** đóng vai trò trung tâm kết nối giữa tầng **MESSAGING — TRUNG CHUYỂN** (**Mosquitto MQTT Broker**) và tầng **PRESENTATION — HIỂN THỊ** (**React Dashboard**), bao gồm 3 khối dịch vụ độc lập[cite: 1]:

1. **BACKEND (FastAPI)[cite: 1]:**
   * **MQTT Consumer:** Đăng ký nhận dữ liệu thời gian thực từ 3 nhánh topic `device/{id}/vitals`, `device/{id}/ecg`, và `device/{id}/alert`[cite: 1].
   * **Alert Router (Ưu tiên cao):** Bắt các tín hiệu khẩn cấp (nút bấm SOS hoặc ngã từ tầng Edge) và chuyển thẳng tới **WebSocket Manager** không qua hàng đợi trễ[cite: 1].
   * **Buffer + Batch:** Gom dữ liệu sinh hiệu định kỳ trong bộ nhớ đệm trước khi ghi hàng loạt vào cơ sở dữ liệu[cite: 1].
   * **REST API (`/vitals`, `/alerts`, `/history`):** Cung cấp dữ liệu lịch sử và danh sách cảnh báo cho **Trang Lịch sử** và **Trang Realtime**[cite: 1].
   * **AI Client (`httpx`):** Đóng gói dữ liệu theo cửa sổ trượt (Sliding Window) gửi sang **AI Service** để phân tích bất đồng bộ[cite: 1].
   * **WebSocket Manager:** Duy trì kết nối thời gian thực đẩy sóng ECG, chỉ số BPM/SpO2, cảnh báo đỏ nháy và kết quả AI xuống **Trang Realtime**[cite: 1].
2. **MongoDB (Cơ sở dữ liệu)[cite: 1]:**
   * **Time-Series Collections:** `vitals (TS)`, `ecg (TS)`, `accel (TS)` lưu trữ chuỗi thời gian tốc độ cao[cite: 1].
   * **Standard Collections:** `alerts` (lịch sử cấp cứu) và `ai_results` (lưu trực tiếp kết quả chẩn đoán từ **AI Service**)[cite: 1].
3. **AI Service (FastAPI)[cite: 1]:**
   * Chứa 4 module xử lý chuyên biệt: **Context-aware** (lọc báo động giả), **Fall Detect** (xác nhận ngã đa biến), **ECG Analysis** (xử lý tín hiệu sóng điện tim) và **AFib Detect** (phát hiện Rung nhĩ cảnh báo đột quỵ)[cite: 1].

---

## 2. Cấu Trúc Thư Mục Dự Án (Monorepo)

```text
iot-stroke-system/
├── docker-compose.yml                  # Khởi chạy Mosquitto, MongoDB, Backend, AI Service
├── mosquitto/
│   └── config/mosquitto.conf           # Cấu hình cổng 1883 và QoS 0/1/2
├── backend_fastapi/                    # Khối BACKEND (FastAPI)
│   ├── Dockerfile
│   ├── requirements.txt                # fastapi, uvicorn, aiomqtt, motor, httpx, pydantic
│   └── app/
│       ├── main.py                     # Khởi tạo app & Lifespan chạy MQTT Consumer + Batch Worker
│       ├── config.py                   # Biến môi trường (Mongo URI, MQTT Host, AI Service URL)
│       ├── database.py                 # Khởi tạo kết nối Motor & Time-Series Collections
│       ├── schemas.py                  # Pydantic models kiểm duyệt JSON đầu vào/đầu ra
│       ├── services/
│       │   ├── mqtt_consumer.py        # Lắng nghe device/+/vitals, ecg, alert
│       │   ├── buffer_batch.py         # Hàng đợi asyncio.Queue gom dữ liệu ghi MongoDB
│       │   ├── alert_router.py         # Xử lý luồng cảnh báo ưu tiên cao
│       │   ├── websocket_manager.py    # Broadcast dữ liệu xuống React Dashboard
│       │   └── ai_client.py            # Gọi POST bất đồng bộ bằng httpx sang AI Service
│       └── routers/
│           ├── vitals.py               # GET /vitals
│           ├── alerts.py               # GET /alerts, PATCH /alerts/{id}/ack
│           └── history.py              # GET /history
├── ai_service_fastapi/                 # Khối AI SERVICE (FastAPI)
│   ├── Dockerfile
│   ├── requirements.txt                # fastapi, uvicorn, numpy, scipy, neurokit2, scikit-learn, motor
│   └── app/
│       ├── main.py                     # Endpoint POST /api/v1/analyze
│       ├── database.py                 # Ghi trực tiếp vào collection ai_results
│       ├── models/
│       │   └── afib_rf_model.pkl       # Mô hình Random Forest đã huấn luyện sẵn
│       └── modules/
│           ├── context_aware.py        # Module 1: Đối chiếu SpO2 (MAX30102) & Gia tốc (MPU6050)
│           ├── fall_detect.py          # Module 2: Xác nhận ngã 3 pha (MPU6050 + BPM)
│           ├── ecg_analysis.py         # Module 3: Lọc nhiễu AD8232 & trích xuất đặc trưng HRV
│           └── afib_detect.py          # Module 4: Phân loại Rung nhĩ & đánh giá nguy cơ đột quỵ
└── scripts/
    ├── train_afib_model.py             # Script huấn luyện model từ bộ dữ liệu MIT-BIH
    └── esp32_simulator.py              # Giả lập ESP32 bắn MQTT cho 3 kịch bản Demo
```

---

## 3. Đặc Tả Giao Tiếp MQTT & Schema MongoDB

### 3.1. Định dạng gói tin MQTT (Từ ESP32 gửi lên Broker)

| MQTT Topic | Tần suất gửi | QoS | Cấu trúc JSON Payload mẫu |
| :--- | :--- | :--- | :--- |
| `device/{id}/vitals`[cite: 1] | 1 gói / giây (1 Hz) | QoS 0 / 1[cite: 1] | `{"device_id": "esp32_01", "ts": 1760420000, "bpm": 78.0, "spo2": 98.0, "temp": 36.6, "ax": 0.02, "ay": -0.05, "az": 0.99}`[cite: 1] |
| `device/{id}/ecg`[cite: 1] | 5 gói / giây (Mỗi gói 25 mẫu @ 125 Hz) | QoS 0[cite: 1] | `{"device_id": "esp32_01", "ts": 1760420000, "fs": 125, "samples": [512, 518, 540, 690, 480, ...]}`[cite: 1] |
| `device/{id}/alert`[cite: 1] | Gửi tức thì khi có sự kiện | QoS 1 / 2[cite: 1] | `{"device_id": "esp32_01", "ts": 1760420000, "alert_type": "SOS_PRESSED" \| "EDGE_FALL_DETECTED", "bpm": 118.0, "max_svm": 3.1}`[cite: 1] |

### 3.2. Thiết kế 5 Collections trong MongoDB

* **`vitals` (Time-Series Collection):** `timeField: "timestamp"`, `metaField: "device_id"`, lưu `bpm`, `spo2`, `temp`[cite: 1].
* **`ecg` (Time-Series Collection):** `timeField: "timestamp"`, `metaField: "device_id"`, lưu mảng `samples` và tần số lấy mẫu `fs`[cite: 1].
* **`accel` (Time-Series Collection):** `timeField: "timestamp"`, `metaField: "device_id"`, lưu gia tốc 3 trục `ax`, `ay`, `az` và giá trị tổng hợp `svm`[cite: 1].
* **`alerts` (Standard Collection):** Lưu cảnh báo khẩn cấp từ **Alert Router** (`device_id`, `timestamp`, `alert_type`, `severity`, `is_acknowledged`)[cite: 1].
* **`ai_results` (Standard Collection):** Nhận kết quả trực tiếp từ **AI Service** (`device_id`, `timestamp`, `context_status`, `fall_status`, `afib_detected`, `afib_probability`, `hrv_metrics`, `recommendation`)[cite: 1].

---

## 4. Đặc Tả Chi Tiết Các Module AI & Bảng Chỉ Số Điều Kiện

Cứ mỗi **10 giây** (cửa sổ trượt cập nhật mỗi 5 giây), **AI Client (`httpx`)** tại Backend sẽ gom dữ liệu của 10 giây gần nhất gửi sang **AI Service (FastAPI)**[cite: 1].

### 4.1. Module 1: `Context-aware` (Bộ lọc Báo động giả SpO2 & Chuyển động)

* **Mục tiêu:** Đối chiếu chéo nồng độ oxy trong máu (`SpO2` từ **MAX30102**) với cường độ rung lắc cổ tay (từ **MPU6050**) để phân biệt tình trạng tụt oxy máu thật với nhiễu do lỏng kẹp cảm biến khi bệnh nhân cử động[cite: 1].
* **Cửa sổ dữ liệu đầu vào:** 5 giây gần nhất (gồm mảng `spo2` và mảng gia tốc 3 trục $a_x, a_y, a_z$ đơn vị $g$)[cite: 1].

#### Công thức tính các chỉ số:
1. **Trung bình nồng độ Oxy máu ($\mu_{\text{SpO}_2}$, đơn vị: %):**
   $$\mu_{\text{SpO}_2} = \frac{1}{N} \sum_{i=1}^{N} \text{SpO}_{2,i}$$
2. **Độ lớn Vector Gia tốc tổng hợp ($SVM_i$, đơn vị: $g$, với $1g \approx 9.8\text{ m/s}^2$):**
   $$SVM_i = \sqrt{a_{x,i}^2 + a_{y,i}^2 + a_{z,i}^2}$$
3. **Độ lệch chuẩn chuyển động ($\sigma_{SVM}$, đơn vị: $g$):**
   $$\sigma_{SVM} = \sqrt{\frac{1}{N} \sum_{i=1}^{N} (SVM_i - \overline{SVM})^2}$$

#### Bảng điều kiện phân loại của Module `Context-aware`:

| Điều kiện $\mu_{\text{SpO}_2}$ (MAX30102)[cite: 1] | Điều kiện $\sigma_{SVM}$ (MPU6050)[cite: 1] | Nhãn đầu ra (`context_status`) | Mức độ (`severity`) | Hành động xử lý tại Backend & Dashboard |
| :--- | :--- | :--- | :--- | :--- |
| $\ge 95\%$ | Bất kỳ | `NORMAL` | `INFO` | Hiển thị chỉ số bình thường trên **Trang Realtime**[cite: 1]. |
| $92\% \le \mu_{\text{SpO}_2} < 95\%$ | $\le 0.15g$ (Nằm yên) | `MILD_HYPOXIA` | `WARNING` | Cảnh báo vàng: *"SpO2 giảm nhẹ, cần theo dõi hô hấp"*. |
| $< 92\%$ | $> 0.15g$ (Tay đang lắc mạnh) | `SENSOR_LOOSE` | `NOISE` | **Chặn báo động đỏ.** Hiển thị thông báo: *"Nhiễu tín hiệu / Lỏng cảm biến SpO2 do chuyển động"*. |
| $< 92\%$ | $\le 0.15g$ (Bệnh nhân bất động) | `RESPIRATORY_RISK` | `CRITICAL` | **Kích hoạt Cảnh báo đỏ nháy:** *"Nguy cơ suy hô hấp cấp (SpO2 < 92% khi bất động)"*[cite: 1]. |

---

### 4.2. Module 2: `Fall Detect` (Thuật toán Xác nhận Ngã 3 Pha)

* **Mục tiêu:** Xác minh sự kiện ngã từ **MPU6050** kết hợp biến thiên nhịp tim từ **MAX30102** để loại bỏ các trường hợp vung tay hoặc làm rơi thiết bị giả tạo[cite: 1].
* **Cửa sổ dữ liệu đầu vào:** 10 giây (Trước va chạm $\rightarrow$ Đỉnh va chạm $\rightarrow$ Sau va chạm 3–5 giây).

#### Bảng chỉ số & Ngưỡng điều kiện xác nhận ngã:

| Thứ tự Pha | Tên chỉ số | Công thức / Cách tính | Ngưỡng điều kiện kích hoạt | Ý nghĩa thực tế |
| :--- | :--- | :--- | :--- | :--- |
| **Pha 1: Va chạm** | Đỉnh gia tốc (`max_svm`) | $SVM_{\max} = \max(SVM_i)$ | $SVM_{\max} \ge 2.5g$ | Phát hiện cơ thể hoặc thiết bị đập mạnh xuống mặt sàn. |
| **Pha 2: Tư thế** | Góc nghiêng thay đổi ($\Delta\theta$) | $\theta = \arccos\left(\frac{a_z}{SVM}\right) \times \frac{180}{\pi}$ | $\Delta\theta \ge 55^\circ$ | Trục cơ thể chuyển đột ngột từ tư thế đứng/ngồi sang nằm ngang. |
| **Pha 3: Bất động** | Độ rung sau ngã ($\sigma_{\text{post}}$) | Độ lệch chuẩn $SVM$ trong 3 giây sau đỉnh va chạm | $\sigma_{\text{post}} \le 0.06g$ | Sau cú đập mạnh, bệnh nhân nằm im lìm (mất ý thức / không tự đứng dậy được). |
| **Pha 4: Sinh hiệu** | Độ lệch nhịp tim ($\Delta\text{BPM}$) | $\|\text{BPM}_{\text{sau}} - \text{BPM}_{\text{trước}}\|$ | $\Delta\text{BPM} \ge 15\text{ BPM}$ hoặc $\text{BPM}_{\text{sau}} > 120$ hoặc $< 45$ | Phản xạ sinh lý: tim đập vọt lên do sốc/hoảng loạn hoặc tụt nhịp do ngất. |

* **Quy tắc hợp nhất (`Decision Logic`):**
  * Thỏa mãn **Pha 1 + Pha 2 + Pha 3** $\rightarrow$ Trả về `FALL_CONFIRMED` $\rightarrow$ Kích hoạt **Cảnh báo đỏ nháy** *"Bệnh nhân ngã / Mất ý thức"*[cite: 1].
  * Chỉ thỏa mãn **Pha 1** ($SVM_{\max} \ge 2.5g$) nhưng $\sigma_{\text{post}} > 0.15g$ $\rightarrow$ Trả về `FALSE_IMPACT` (Chỉ là va quệt tay, hủy cảnh báo ngã).

---

### 4.3. Module 3 & 4: `ECG Analysis` & `AFib Detect` (Phát hiện Rung nhĩ & Nguy cơ Đột quỵ)

* **Mục tiêu:** Phân tích chuỗi sóng điện tim từ cảm biến **AD8232** để tìm dấu hiệu **Rung nhĩ (Atrial Fibrillation - AFib)**[cite: 1].
* **Cửa sổ dữ liệu đầu vào:** 10 giây sóng ECG liên tục ở tần số lấy mẫu $f_s = 125\text{ Hz}$ (mảng **1250 mẫu**)[cite: 1].

#### Bước 1: Tiền xử lý & Kiểm tra chất lượng sóng (`ECG Analysis`)
1. **Lọc nhiễu Bandpass Butterworth:** Bậc 4, dải tần $0.5\text{ Hz} - 40\text{ Hz}$ (khử trôi đường nền và nhiễu điện lưới 50 Hz).
2. **Tìm đỉnh sóng R (`R-peaks`) và tính chuỗi khoảng cách $RR$ (mili-giây - `ms`):**
   $$RR_i = \frac{\text{index}(R_{i+1}) - \text{index}(R_i)}{125} \times 1000 \quad (\text{ms})$$
   * Loại bỏ các khoảng nhiễu vật lý $RR_i < 300\text{ ms}$ hoặc $RR_i > 2000\text{ ms}$. Nếu số đỉnh R hợp lệ trong 10 giây $< 6$ đỉnh $\rightarrow$ trả về `ECG_LEAD_OFF` (*"Tuột điện cực AD8232"*).

#### Bước 2: Trích xuất 5 Chỉ số Biến thiên Nhịp tim (HRV Features) & Bảng Ngưỡng Y Khoa

Đặt $\Delta RR_i = |RR_{i+1} - RR_i|$ là độ chênh lệch thời gian giữa 2 nhịp tim kế tiếp nhau.

| Ký hiệu Chỉ số | Tên gọi & Công thức Toán học | Ý nghĩa trực quan | Ngưỡng Bình thường (Nhịp xoang đều) | Ngưỡng Nghi ngờ (Loạn nhịp nhẹ) | Ngưỡng Rung Nhĩ - Nguy cơ Đột quỵ (`AFib`)[cite: 1] |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **`HR_mean`** | **Nhịp tim trung bình (BPM):** $\text{HR} = \frac{60000}{\overline{RR}}$ | Số nhịp đập trung bình trong 1 phút tính từ sóng ECG. | $60 - 100\text{ BPM}$ | $50 - 59\text{ BPM}$ hoặc $101 - 119\text{ BPM}$ | Thường kèm đáp ứng thất nhanh $> 110\text{ BPM}$ |
| **`RMSSD`** | **Căn bậc hai trung bình bình phương hiệu số $RR$ liên tiếp (ms):** $RMSSD = \sqrt{\frac{1}{M-1}\sum_{i=1}^{M-1} (RR_{i+1} - RR_i)^2}$ | Đo **độ giật cục** giữa nhịp trước và nhịp ngay sau nó. | $15 - 65\text{ ms}$ | $66 - 99\text{ ms}$ | **$\ge 100\text{ ms}$** (Các nhịp nhảy loạn xạ không đều) |
| **`pNN50`** | **Tỷ lệ cặp nhịp lệch nhau quá 50 ms (%):** $pNN50 = \frac{\text{Số lần } (\Delta RR_i > 50\text{ ms})}{M-1} \times 100\%$ | Phần trăm số cặp nhịp kế tiếp bị lệch nhau quá $50\text{ ms}$. | $< 25\%$ | $25\% - 49\%$ | **$\ge 50\%$** (Đa số các nhịp lệch mạnh so với nhịp trước) |
| **`CV_RR`** | **Hệ số biến thiên khoảng $RR$ (Tỷ lệ):** $CV_{RR} = \frac{\sigma_{RR}}{\overline{RR}}$ | Độ phân tán của khoảng cách nhịp tim so với mức trung bình. | $< 0.08$ | $0.08 - 0.11$ | **$\ge 0.12$** (Độ phân tán nhịp cực lớn) |
| **`Shannon_H`** | **Entropy Shannon của chuỗi $RR$:** $H = -\sum_{k} p_k \log_2(p_k)$ | Đo **mức độ hỗn loạn (vô trật tự)** của chuỗi nhịp tim. | $< 1.40$ | $1.40 - 1.79$ | **$\ge 1.80$** (Mất hoàn toàn quy luật nhịp xoang) |

#### Bước 3: Cơ chế Kết hợp Mô hình AI (`Random Forest`) & Luật Y Khoa (`Hybrid Decision`)

1. **Vector đặc trưng đầu vào:** $\mathbf{x} = [\text{HR\_mean}, RMSSD, pNN50, CV_{RR}, \text{Shannon\_H}]$.
2. **Đầu ra mô hình Random Forest:** Xác suất $P(\text{AFib}) \in [0.0, 1.0]$.
3. **Điều kiện chốt kết quả (`AFib Detect`)[cite: 1]:**
   * **`AFIB_HIGH_RISK` (Cảnh báo nguy cơ đột quỵ):** Khi $P(\text{AFib}) \ge 0.70$ **HOẶC** ($RMSSD \ge 100\text{ ms}$ **VÀ** $pNN50 \ge 50\%$ **VÀ** $CV_{RR} \ge 0.12$) $\rightarrow$ Sinh cảnh báo: *"Phát hiện bất thường điện tim (Rung nhĩ - AFib) - Khuyến nghị tầm soát nguy cơ đột quỵ"*.
   * **`ARRHYTHMIA_WARNING` (Theo dõi loạn nhịp nhẹ):** Khi $0.45 \le P(\text{AFib}) < 0.70$ hoặc có ít nhất 1 chỉ số nằm ở vùng Nghi ngờ.
   * **`NORMAL_SINUS` (Nhịp xoang bình thường):** Khi $P(\text{AFib}) < 0.45$ và cả 3 chỉ số $RMSSD < 65\text{ ms}$, $pNN50 < 25\%$, $CV_{RR} < 0.08$.

---

## 5. Thiết Kế Luồng Xử Lý Bất Đồng Bộ Trong `BACKEND (FastAPI)`

### 5.1. Cơ chế `Buffer + Batch` (Chống nghẽn MongoDB)
* Khởi tạo 3 hàng đợi `asyncio.Queue` cho `vitals`, `ecg`, và `accel`[cite: 1].
* Worker chạy ngầm mỗi **3 giây/lần** (hoặc khi đủ **50 bản ghi**) rút toàn bộ dữ liệu trong Queue để gọi `insert_many` vào **MongoDB**[cite: 1].
* Duy trì `RingBuffer` (`collections.deque`) lưu **10 giây dữ liệu mới nhất** trên RAM cho từng `device_id` để **AI Client (`httpx`)** lấy gửi sang **AI Service** ngay lập tức[cite: 1].

### 5.2. Danh sách Endpoints của `REST API` và `WebSocket`

| Giao thức | Đường dẫn (Endpoint) | Tham số (Params / Body) | Chức năng phục vụ React Dashboard[cite: 1] |
| :--- | :--- | :--- | :--- |
| **WebSocket** | `ws://host:8000/ws/realtime/{device_id}` | `device_id` trên URL | Đẩy gói tin `vitals`, sóng `ecg`, cảnh báo đỏ từ **Alert Router** và kết quả từ **AI Service** xuống **Trang Realtime**[cite: 1]. |
| **REST (`GET`)** | `/api/vitals`[cite: 1] | `?device_id=esp32_01&limit=60` | Lấy 60 bản ghi sinh hiệu gần nhất khi vừa mở **Trang Realtime**[cite: 1]. |
| **REST (`GET`)** | `/api/history`[cite: 1] | `?device_id=esp32_01&start_ts=...&end_ts=...` | Truy vấn lịch sử BPM, SpO2, nhiệt độ và sóng ECG cho **Trang Lịch sử**[cite: 1]. |
| **REST (`GET`)** | `/api/alerts`[cite: 1] | `?device_id=esp32_01&type=all` | Lấy danh sách cảnh báo cấp cứu (`alerts`) và lịch sử chẩn đoán AI (`ai_results`)[cite: 1]. |
| **REST (`POST`)** | `/api/demo/inject-afib` | `{"device_id": "esp32_01"}` | Phục vụ **Kịch bản Demo 3**: Nạp chuỗi sóng ECG Rung nhĩ mẫu để kích hoạt **AI Service** phân tích tức thì[cite: 1]. |

---

## 6. Lộ Trình Triển Khai (4 Tuần) & Kịch Bản Nghiệm Thu

* **Tuần 1 — Hạ tầng & MQTT Consumer:** Dựng `docker-compose.yml` (**Mosquitto**, **MongoDB**), viết **MQTT Consumer** và **WebSocket Manager** trong **BACKEND (FastAPI)**[cite: 1].
* **Tuần 2 — Lưu trữ Time-Series & REST API:** Cài đặt **Buffer + Batch**, **Alert Router** ưu tiên cao và 3 cụm **REST API** (`/vitals`, `/alerts`, `/history`)[cite: 1].
* **Tuần 3 — Xây dựng AI Service (FastAPI):** Cài đặt 4 module `context_aware.py`, `fall_detect.py`, `ecg_analysis.py`, `afib_detect.py` và kết nối qua **AI Client (`httpx`)**[cite: 1].
* **Tuần 4 — Simulator & Kiểm thử Demo:** Viết `esp32_simulator.py` và ghép nối toàn trình với **React Dashboard**[cite: 1].

### Bảng thông số nghiệm thu 3 Kịch bản Demo Đồ án

| Kịch bản Demo | Đầu vào giả lập / Phần cứng thực tế | Chỉ số đo được tại AI Service / Backend | Kết quả kỳ vọng trên React Dashboard[cite: 1] |
| :--- | :--- | :--- | :--- |
| **1. Trạng thái Ổn định** | Đeo cảm biến nghỉ ngơi: $\text{BPM} = 75$, $\text{SpO}_2 = 98\%$, $T = 36.6^\circ\text{C}$, sóng ECG nhịp xoang đều. | $\sigma_{SVM} = 0.02g$, $RMSSD = 28\text{ ms}$, $pNN50 = 8\%$, $CV_{RR} = 0.04$, $P(\text{AFib}) = 0.05$. | Đồ thị sóng ECG và chỉ số chạy mượt qua WebSocket; trạng thái `NORMAL`[cite: 1]. |
| **2. Cấp cứu Tự động (Real-time)** | Vung mạnh / thả rơi cụm **MPU6050** rồi để nằm yên trên bàn (hoặc bấm **Nút SOS**)[cite: 1]. | $SVM_{\max} = 3.2g \ge 2.5g$, $\sigma_{\text{post}} = 0.01g \le 0.06g$, đi qua **Alert Router**[cite: 1]. | **Buzzer** kêu tại giường; **Trang Realtime** nháy đỏ dưới $200\text{ ms}$ báo *"Bệnh nhân ngã / Mất ý thức"*[cite: 1]. |
| **3. Phát hiện Nguy cơ Đột quỵ (AI)** | Gọi API nạp chuỗi sóng ECG Rung nhĩ (khoảng $RR$: $490, 880, 530, 920\text{ ms}$). | $RMSSD = 165\text{ ms}$, $pNN50 = 78\%$, $CV_{RR} = 0.21$, $P(\text{AFib}) = 0.91$. | Collection `ai_results` lưu bản ghi mới; Dashboard bật cảnh báo: *"Phát hiện bất thường điện tim - Khuyến nghị tầm soát nguy cơ đột quỵ"*[cite: 1]. |