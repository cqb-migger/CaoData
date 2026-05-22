# 🚀 Alokiddy Data Scraper & Downloader

Hệ thống cào dữ liệu và tải tài nguyên học tập (Video, Audio, Hình ảnh) tự động từ trang web **alokiddy.com.vn** dành cho giáo trình Cambridge (Pre-Starters → Flyers) và khóa Phonics.

Hệ thống được thiết kế tối ưu, kết hợp cào dữ liệu động bằng **Selenium (Chrome Headless)** và tải tài nguyên song song cực nhanh qua **ThreadPoolExecutor**, tự động kiểm tra và ghi nhận các liên kết lỗi 404 từ phía máy chủ Alokiddy.

---

## 🛠️ Cài đặt môi trường

Yêu cầu máy tính có cài đặt **Google Chrome** và phiên bản **Python 3.8+**.

```bash
# 1. Tạo môi trường ảo Python
python -m venv .venv

# 2. Kích hoạt môi trường ảo
# Trên Windows (PowerShell):
.\.venv\Scripts\activate
# Trên Windows (CMD):
.\.venv\Scripts\activate.bat
# Trên macOS/Linux:
source .venv/bin/activate

# 3. Cài đặt các thư viện phụ thuộc
pip install -r requirements.txt
```

---

## ⚡ Hướng dẫn chạy (Một bước duy nhất)

Giờ đây, bạn không cần phải chạy cào dữ liệu rồi mới chạy tải file thủ công. Hệ thống đã được tích hợp toàn bộ: **Cào dữ liệu xong sẽ tự động kích hoạt bộ tải tài nguyên để tải trực tiếp các file media về máy và cập nhật lại đường dẫn nội bộ vào tệp JSON.**

### 1. Cào chương trình Cambridge (Pre-Starters → Flyers)

Bạn có hai lựa chọn tùy thuộc vào cấu hình phần cứng của máy tính:

*   **Chạy song song (Khuyên dùng cho máy RAM ≥ 8GB - Rất nhanh):**
    ```bash
    python scraper_parallel.py
    ```
    *Mỗi khóa học sẽ được mở trên một trình duyệt Chrome độc lập (tối đa 6 luồng) giúp rút ngắn thời gian cào tối đa.*

*   **Chạy tuần tự (Phù hợp cho máy yếu hoặc kết nối mạng không ổn định):**
    ```bash
    python scraper.py
    ```
    *Sử dụng một trình duyệt duy nhất để quét tuần tự các bài học.*

### 2. Cào riêng khóa học Phonics (Đánh vần)

Vì cấu trúc trang Phonics khác biệt hoàn toàn với Cambridge, vui lòng chạy tệp chuyên biệt:
```bash
python scraper_phonics.py
```
*Tự động quét toàn bộ bài học Phonics và tải về các file video bài giảng, hình ảnh từ vựng, audio bài tập.*

---

## 📂 Cấu trúc thư mục dự án

```text
CaoData/
├── scraper.py              # Bộ cào Cambridge đơn luồng (tuần tự) - an toàn nhất
├── scraper_parallel.py     # Bộ cào Cambridge đa luồng (tối đa 6 Chrome) - nhanh nhất
├── scraper_phonics.py      # Bộ cào riêng khóa Phonics đa luồng (4 Chrome)
├── requirements.txt        # Thư viện Python phụ thuộc
├── README.md               # Hướng dẫn triển khai và vận hành nhanh (tệp hiện tại)
├── DOCUMENTATION.md        # Tài liệu kỹ thuật chi tiết
├── HUONG_DAN_CAO_DATA.md   # Hướng dẫn quy trình cào dữ liệu cho các dự án tương lai
├── 404_not_found.log       # Nhật ký lưu các liên kết tài nguyên lỗi 404 từ server
├── json/
│   ├── alokiddy_cambridge.json   # Kết quả dữ liệu Cambridge dạng JSON (snake_case keys)
│   └── alokiddy_phonics.json     # Dữ liệu khóa học Phonics dạng JSON (snake_case keys)
├── downloads/              # Thư mục lưu trữ tất cả tài nguyên đã tải về cục bộ
│   ├── cambridge/          # Tài nguyên giáo trình Cambridge
│   │   └── tieng_anh_lop_1/
│   │       └── [FREE]_unit_1_this_is_his_face/  # Tiền tố [FREE]_ cho bài học miễn phí
│   │           ├── thumbnail.jpg
│   │           └── bai_hoc/
│   │               └── media/    # Chứa video chính (.mp4)
│   └── phonics/            # Tài nguyên khóa Phonics
│       └── phonics_for_starters/
│           └── [FREE]_unit_1_aa/
│               └── ...
└── src/
    ├── __init__.py         # Khởi tạo module src
    └── downloader.py       # Công cụ tải tài nguyên tích hợp & độc lập
```

---

## 🔍 Tính năng đặc biệt của hệ thống

1.  **Chạy Một Bước (Unified Flow):** Tích hợp chạy cào và tải file song song ngay lập tức, tự động cập nhật `"local": "downloads/..."` trực tiếp vào file JSON kết quả.
2.  **Tránh cào trùng lặp:** Hệ thống lưu trạng thái trực tiếp vào JSON. Nếu chạy lại, các file đã tải thành công sẽ được tự động bỏ qua để tiết kiệm băng thông.
3.  **Tự động ghi nhận lỗi 404:** Mọi liên kết tài nguyên bị lỗi hoặc viết sai chính tả từ phía server Alokiddy (ví dụ: `CHEECK.mp4` thay vì `CHEEK.mp4`, hay một số audio bài nghe bị thiếu) sẽ được tự động bỏ qua và ghi nhận chi tiết vào tệp `404_not_found.log` để bạn dễ dàng theo dõi.
4.  **Bóc tách game Cocos:** Trình cào có khả năng "chui" vào các iframe trò chơi tương tác để tìm danh sách playlist video từ vựng ẩn dưới mã JavaScript mà các bộ cào thông thường không thể thấy.

*Để xem tài liệu kỹ thuật chi tiết hơn về cấu trúc dữ liệu JSON, thuật toán xử lý DOM và các điểm mù của trang web Alokiddy, vui lòng tham khảo tệp [DOCUMENTATION.md](file:///c:/Users/ADMIN/Desktop/CaoData/DOCUMENTATION.md).*