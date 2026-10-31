# Dataset mẫu tổng hợp

**Chỉ để thử pipeline, không phải ECG bệnh nhân hoặc bằng chứng hiệu quả phát hiện AFib.** Nhãn do bộ sinh xác định kiểu nhịp mô phỏng; hình dạng tín hiệu không đại diện đầy đủ sinh lý AFib.

| File | Nội dung |
| --- | --- |
| `features.csv` | 96 cửa sổ, mỗi cửa sổ 20 giây ở 125 Hz; 5 đặc trưng từ extractor v2 |
| `manifest.csv` | ID nhóm, nhãn, split, tần số và khoảng mẫu |
| `sample_ecg.csv` | Một tín hiệu tổng hợp 2500 mẫu, cột `ecg`, đơn vị mô phỏng mV |

Có 24 nhóm giả lập, mỗi nhóm 4 cửa sổ gồm hai nhãn 0 và hai nhãn 1. Train có 12 nhóm; calibration, validation và test mỗi tập có 4 nhóm. ID giả chỉ dùng để minh họa cơ chế split, không phải 24 người thật.

Đặc trưng: `HR_mean`, `RMSSD`, `pNN50`, `CV_RR`, `Shannon_H`; định nghĩa được phiên bản hóa bằng cột `extractor_version`. Histogram entropy v2 dùng 10 bins cố định trong [300, 2000] ms, khác extractor v1.

Manifest mặc định để trống `signal_path` vì không đưa toàn bộ 96 waveform vào repository. Tái tạo waveform đầy đủ bằng:

```bash
python -m training.generate_sample_data --output /tmp/ai-sample --seed 42 --save-waveforms
```

Seed mặc định 42. Các giá trị đặc trưng được tính từ tín hiệu đã sinh bằng chính extractor dùng trong API, không lấy trực tiếp từ quy tắc phân loại. Giá trị `data_origin=synthetic` được giữ trong bảng và truyền vào artifact. Công cụ huấn luyện yêu cầu `--allow-synthetic`; API yêu cầu `AI_ALLOW_SYNTHETIC_MODEL=true` để thử model đó.

Không dùng điểm số hoặc khoảng tin cậy trên tập này để kết luận chất lượng model trên người thật. Không thay đổi `data_origin` thành dữ liệu thật để vượt cơ chế kiểm tra.
