# AI Sensor Analysis Service

Dịch vụ FastAPI phân tích SpO₂, gia tốc và ECG. API v1 được giữ để tương thích; API v2 bổ sung dữ liệu có kiểu, trạng thái chất lượng, thuật toán theo thời gian, nguồn suy luận và lưu trạng thái/kết quả nguyên tử.

Đây là phần mềm nghiên cứu. Ngưỡng mặc định và dataset tổng hợp đi kèm chưa được kiểm định trên người dùng hoặc thiết bị thực tế. Phân loại AFib không phải mô hình dự báo đột quỵ.

## Chạy thử nhanh

Yêu cầu Python 3.12. Cài dependency bằng lockfile để train/inference dùng cùng phiên bản:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-dev.lock.txt
AI_STORAGE_MODE=memory uvicorn app.main:app --host 0.0.0.0 --port 8001 --workers 1
```

Chế độ `memory` chỉ dành cho một process chạy thử: mất kết quả và trạng thái khi restart, không chia sẻ giữa worker. Response trả `persistence_status: memory_only`. Khi đầy dung lượng cấu hình, dịch vụ từ chối cửa sổ mới thay vì xóa ledger làm mất tính idempotent.

Các địa chỉ:

- `GET /health/live`: tiến trình đang chạy.
- `GET /health/ready`: phụ thuộc v2 sẵn sàng; cho biết chế độ suy giảm.
- `GET /health`: endpoint legacy, không phải readiness.
- `POST /api/v1/analyze`: hợp đồng cũ; logic thuật toán và chính sách lưu v1 vẫn có hạn chế trong tài liệu phân tích.
- `POST /api/v2/analyze`: pipeline mới.
- `/docs`: schema và giao diện thử API.

`.env.example` mô tả biến môi trường. Ứng dụng đọc biến được export, không tự đọc `.env`; Uvicorn có thể được cấu hình đọc file bằng `--env-file` nếu muốn.

## Gửi dữ liệu v2

```bash
curl -X POST http://localhost:8001/api/v2/analyze \
  -H 'Content-Type: application/json' \
  --data-binary @examples/analyze_v2.json
```

File ví dụ gửi SpO₂ thấp với ECG vắng mặt để kiểm tra cảnh báo vẫn được giữ. Không có dữ liệu cảm biến thì kết quả là `NO_DATA`/`UNDETERMINED`, không tạo số đo SpO₂ giả hoặc khẳng định không AFib.

Quy ước đầu vào:

- `start_time`, `end_time` có timezone và được chuẩn hóa UTC; khoảng thời gian là `[start_time, end_time)`.
- Với ECG/gia tốc: `end_time - start_time = số mẫu / fs`, có dung sai tối đa nửa chu kỳ mẫu.
- Gia tốc có `unit: g` hoặc `m/s2`, ba trục cùng số mẫu. ECG có `unit: mV` hoặc `adc`, `fs > 80` với dải lọc mặc định.
- SpO₂/BPM gồm các cặp `timestamp`, `value`, timestamp tăng dần và thuộc cửa sổ.
- Không chấp nhận chuỗi thay số, boolean thay số, NaN/Inf hoặc trường không khai báo.
- `device_id`, `session_id`, `window_id` nhận chữ/số và các ký tự `_ . : -`, tối đa 128 ký tự.

Cùng `(device_id, session_id, window_id)` với cùng payload chuẩn hóa trả kết quả đã lưu. Cùng khóa khác nội dung trả 409. Cửa sổ mới phải bổ sung thời gian mới; có thể chồng lấn, nhưng phần đã xử lý không được cộng lại vào state. Nếu đổi policy/model khi dùng state cũ, dùng `session_id` mới. Khi một va chạm đang được theo dõi, đổi tần số gia tốc cũng yêu cầu phiên mới.

JSON v2 bị giới hạn dung lượng trước khi parse; giới hạn mẫu/thời lượng được kiểm tra trước xử lý NumPy. Khi hết năng lực xử lý trả 429. Dữ liệu sai schema trả 422; xung đột thứ tự/nội dung trả 409; không xác nhận lưu được trả 503. Retry bằng đúng khóa và nội dung ban đầu.

## Lưu MongoDB

Mặc định `AI_STORAGE_MODE=mongo`. V2 yêu cầu replica set hoặc mongos để ghi `ai_sessions_v2` và `ai_results_v2` trong cùng transaction. MongoDB standalone vẫn dùng được cho đường legacy, nhưng v2 báo chưa sẵn sàng và trả 503. Không tự chuyển v2 sang RAM khi database lỗi.

```bash
export MONGO_URI='mongodb://localhost:27017/?replicaSet=rs0'
export MONGO_DB='iot_stroke_db'
export AI_STORAGE_MODE=mongo
uvicorn app.main:app --host 0.0.0.0 --port 8001
```

Thiết lập replica set theo hạ tầng của bạn; ứng dụng không tự thay cấu hình MongoDB có sẵn. State và kết quả cùng commit, callback xử lý có thể được chạy lại khi transaction xung đột. Unique index ngăn ghi trùng; không tuyên bố giao nhận mạng exactly-once. Cửa sổ khác nhau cùng phiên có thể nhận 409 nếu đến ngược thứ tự.

Collection v1 `ai_results` không bị migrate hoặc áp index v2. Chưa áp TTL để tránh tự xóa dữ liệu hoặc mất khả năng nhận diện retry. Theo dõi dung lượng và thiết kế chính sách lưu theo sản phẩm trước khi vận hành dài hạn.

## Dataset mẫu và huấn luyện

Dataset ở [datasets/sample](datasets/sample/README.md): 96 cửa sổ đặc trưng từ ECG tổng hợp, 24 ID nhóm giả lập, chia sẵn train/calibration/validation/test không trùng nhóm. Có file ECG mẫu và script tái tạo từ seed.

```bash
python -m training.train_baseline datasets/sample/features.csv \
  --output artifacts/synthetic-demo-v2 \
  --allow-synthetic --model-version synthetic-demo-v2
```

Lệnh thực hiện group CV trong train, fit sigmoid calibrator trên calibration độc lập, chọn ngưỡng bằng validation và báo test một lần. Model xuất ra là predictor đã hiệu chuẩn, có cùng giao diện `predict_proba`. Việc đóng băng estimator trước calibration dùng [FrozenEstimator của scikit-learn](https://scikit-learn.org/stable/modules/generated/sklearn.frozen.FrozenEstimator.html).

Artifact gồm model, metadata, schema đặc trưng, cấu hình tiền xử lý, manifest split, dependency, báo cáo và checksum. Không tự cài model vào API đang chạy. Điểm số trên dataset tổng hợp chỉ chứng minh quy trình chạy được.

Để tạo đầy đủ waveform và kiểm tra lại trích xuất:

```bash
python -m training.generate_sample_data --output /tmp/ai-sample --save-waveforms
python -m training.extract_features /tmp/ai-sample/manifest.csv --output /tmp/ai-features.csv
```

Để đánh giá lại một artifact đã khóa:

```bash
python -m training.evaluate datasets/sample/features.csv artifacts/synthetic-demo-v2 \
  --output /tmp/ai-evaluation.json --allow-synthetic
```

Để thử API bằng model tổng hợp phải bật rõ hai biến dưới; mặc định API từ chối artifact gắn cờ dữ liệu tổng hợp:

```bash
AI_STORAGE_MODE=memory \
AI_MODEL_DIR=artifacts/synthetic-demo-v2 \
AI_ALLOW_SYNTHETIC_MODEL=true \
AI_MODEL_REQUIRED=true \
uvicorn app.main:app --port 8001 --workers 1
```

Chỉ nạp Joblib từ nguồn tin cậy. Loader đối chiếu checksum, phiên bản package, extractor, cấu hình lọc, thứ tự đặc trưng và nhãn. Không có model thì v2 dùng heuristic có truy vết, trừ khi `AI_MODEL_REQUIRED=true`; điểm heuristic không được điền vào trường xác suất.

Với dữ liệu thật: đọc hướng dẫn dataset, chuyển tín hiệu và annotation đã kiểm tra thành manifest, chia theo người trước phân đoạn, ghi `data_origin=reference_labeled` và chạy cùng extractor v2. Không chỉ đổi nhãn provenance của dataset mẫu. Hướng dẫn nguồn, gán nhãn và kiểm định nằm trong [kế hoạch huấn luyện](KE_HOACH_CAI_THIEN_VA_HUAN_LUYEN_MODEL.md).

## Kiểm thử

```bash
python -m pytest -q
```

Test tích hợp MongoDB mặc định bỏ qua, chỉ chạy khi cung cấp URI thử nghiệm rõ ràng:

```bash
AI_TEST_MONGO_URI='mongodb://localhost:27181/?replicaSet=aiTest' \
python -m pytest tests/test_mongo_integration.py -q
```

Test này tạo database tên ngẫu nhiên `ai_service_test_*`, kiểm tra commit nguyên tử, retry đồng thời và rollback khi ghi kết quả lỗi, rồi xóa đúng database thử nghiệm đó.

Benchmark trên một API chạy thử riêng, với payload đại diện cho dữ liệu cần đo:

```bash
python scripts/benchmark_api.py --requests 50 --concurrency 2 --input examples/analyze_v2.json
```

Mỗi request dùng phiên mới để đo xử lý và lưu thật thay vì nhận lại cache. Công cụ in phân bố mã HTTP, throughput thành công và p50/p95/p99. Nó tạo kết quả/state mới trong kho của API được chỉ định; chỉ chạy trên môi trường thử nghiệm. Payload mặc định chỉ có SpO₂; cung cấp payload ECG/gia tốc để đo tải tương ứng. Log v2 có request ID, thời gian xử lý, nguồn suy luận và trạng thái lưu, không in mảng tín hiệu.

## Docker

Image dùng Python 3.12, runtime lockfile, user riêng và readiness probe:

```bash
docker build -t ai-sensor-service .
docker run --rm -p 8001:8001 -e AI_STORAGE_MODE=memory ai-sensor-service
```

Chế độ MongoDB cần `MONGO_URI` truy cập được từ container; `localhost` trong container là chính container. Artifact không được tự copy từ thư mục `artifacts/` vào image; mount thư mục model được duyệt và đặt `AI_MODEL_DIR` khi cần.

## Giới hạn triển khai hiện tại

- Detector QRS và đánh giá chất lượng ECG là baseline nghiên cứu, chưa phải đánh giá chất lượng đầy đủ. Bộ lọc là offline theo cửa sổ, không phải bộ lọc streaming nhân quả.
- Ngưỡng thuật toán theo thời gian cấu hình được nhưng chưa chọn trên dataset thực tế. Gyroscope/PPG thô chưa được xử lý vì hợp đồng dữ liệu chưa có chúng.
- Huấn luyện hỗ trợ bảng đặc trưng và manifest CSV ECG; chưa tự tải/diễn giải WFDB hoặc annotation từ PhysioNet. Phải chuẩn bị và kiểm tra nhãn nguồn riêng.
- Báo cáo model áp dụng trên cửa sổ qua quality gate. Chưa có bộ benchmark nhãn sự kiện thực để đo báo giả/giờ hoặc độ trễ trên thiết bị; cần đánh giá thêm trước phát hành.
- Có log vận hành cơ bản và giới hạn xử lý, chưa có exporter dashboard/metrics hoặc hạ tầng phát hành model tự động.

Thiết kế đầy đủ được mô tả trong [hướng dẫn chỉnh sửa](HUONG_DAN_CHINH_SUA_SRC_CODE.md). Các tài liệu kế hoạch là định hướng, không phải xác nhận mọi đầu việc nghiên cứu/vận hành đã hoàn tất.
