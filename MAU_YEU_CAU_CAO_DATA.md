# 📝 HƯỚNG DẪN CUNG CẤP THÔNG TIN ĐẦU VÀO CHO CÁC DỰ ÁN CÀO DỮ LIỆU (SCRAPING)
*Tài liệu kỹ thuật chuẩn hóa quy trình cung cấp thông tin đầu vào nhằm tối ưu hiệu năng xử lý, giảm thiểu chi phí tài nguyên hệ thống (token) và tăng tốc độ triển khai.*

---

## 📌 DANH SÁCH ĐẦU VÀO CỤ THỂ GIÚP TIẾT KIỆM TOKEN VÀ TỐI ƯU HÓA CODE NHẤT
Khi phát triển mã nguồn cào dữ liệu bằng AI, hai giai đoạn tiêu tốn nhiều token đầu vào (Input Tokens) nhất của AI là:
1. **Phân tích DOM/HTML quá lớn:** Các file HTML gốc chứa quá nhiều mã rác (scripts, styles, SVG...) làm tràn ngữ cảnh (context window).
2. **Thử và sai Selector (Trial and Error):** Việc AI phải tự đoán và thử nghiệm các CSS Selector/XPath để lấy dữ liệu.

Để giải quyết triệt để vấn đề này, dưới đây là danh sách các dữ liệu đầu vào chi tiết, sạch và tối ưu nhất mà kỹ sư hệ thống nên chuẩn bị:

### 1. File HTML đã được lọc sạch mã rác (Cleaned HTML)
* **Nguyên lý:** File HTML gốc của một trang web thường nặng từ 500KB - 2MB chứa đầy các đoạn mã CSS, Javascript nội dòng và mã nhúng rác. AI sẽ phải đọc toàn bộ các dữ liệu rác này, dẫn đến tiêu tốn hàng nghìn token vô ích.
* **Cách thực hiện:** Thay vì gửi toàn bộ file `.html`, hãy lọc sạch hoặc chỉ copy vùng dữ liệu cốt lõi:
  * **Cách 1 (Thủ công):** Chỉ copy thẻ `<div class="content">` hoặc thẻ `<table>` chứa bảng dữ liệu thực tế.
  * **Cách 2 (Sử dụng Console):** Nhấn `F12` -> chọn tab **Console** -> gõ lệnh sau để lấy cấu trúc selector đã test sẵn và gửi kết quả cho AI:
    ```javascript
    // Kiểm tra xem selector có trả về đúng số lượng phần tử dữ liệu không
    document.querySelectorAll('.ten-class-bai-hoc').length 
    ```
    Nếu lệnh trên trả về đúng số lượng phần tử (ví dụ: 20 bài học), hãy cung cấp selector `.ten-class-bai-hoc` cho AI. AI sẽ viết code chính xác ngay lập tức mà không cần đọc DOM HTML.

---

### 2. Danh sách liên kết định dạng chuẩn (URL Sitemap / Patterns)
* **Nguyên lý:** Nếu AI phải tự viết code để quét trang chủ, tìm nút "Trang sau", bấm tiếp rồi mới lấy được link chi tiết (Crawler), chương trình sẽ rất phức tạp và tốn nhiều token chạy thử nghiệm.
* **Cách thực hiện:** Cung cấp quy luật sinh URL hoặc danh sách URL cụ thể dưới dạng file `.txt` (mỗi dòng một link):
  * **Công thức sinh URL (Pattern):**
    * Trang danh mục: `https://example.com/products?page={page_number}` (chạy từ page 1 đến 50).
    * Trang chi tiết: `https://example.com/item/{item_id}`.
  * **File chứa danh sách URL tĩnh:** Gửi trực tiếp file `urls.txt` chứa danh sách 1000 đường dẫn cần cào. AI chỉ cần viết đúng 1 vòng lặp để duyệt qua file này, giảm thiểu 50% khối lượng code.

---

### 3. File Response JSON hoặc File HAR (HTTP Archive) từ tab Network
* **Nguyên lý:** Cào dữ liệu từ API ẩn trả về định dạng JSON là phương án sạch nhất. File JSON không chứa thẻ HTML, định dạng rõ ràng, giúp AI hiểu cấu trúc dữ liệu trong 1 giây mà không tốn token phân tích giao diện.
* **Cách thực hiện:**
  * **Cách 1 (Response JSON):** Tại tab **Network** -> chọn request API -> copy toàn bộ nội dung trong tab **Response** lưu thành file `.json` và gửi cho AI.
  * **Cách 2 (File HAR):** Tại tab **Network** -> click vào biểu tượng mũi tên tải xuống có chữ **"Export HAR..."** (hoặc chuột phải chọn *Save all as HAR with content*). Gửi file `.har` này cho AI. File này chứa toàn bộ lịch sử kết nối mạng của trình duyệt, giúp AI tự trích xuất ra các API ẩn.

---

### 4. Chuỗi Xác Thực Session (Active Cookies & User-Agent Headers)
* **Nguyên lý:** Các trang web yêu cầu đăng nhập hoặc sử dụng Cloudflare bảo mật sẽ chặn các request thông thường. Nếu AI phải tự viết code giải mã captcha, vượt Cloudflare, hoặc giả lập đăng nhập bằng Selenium, mã nguồn sẽ cực kỳ cồng kềnh, dễ lỗi và tiêu tốn lượng token khổng lồ khi debug.
* **Cách thực hiện:** Cung cấp thông tin phiên làm việc đã xác thực thành công từ trình duyệt của người dùng:
  * Nhấn `F12` -> tab **Network** -> click vào một request bất kỳ -> nhìn xuống phần **Request Headers**.
  * Copy giá trị của trường `Cookie` và trường `User-Agent`.
  * Gửi hai chuỗi text này cho AI để nhúng thẳng vào cấu hình HTTP Headers của thư viện `requests` / `httpx`. Phương pháp này giúp bypass (vượt qua) 99% các cơ chế chặn của web tĩnh mà không cần dùng trình duyệt ảo.

---

## 📌 BIỂU MẪU CUNG CẤP ĐẦU VÀO TỐI ƯU (Copy khi tạo yêu cầu cào dữ liệu mới)

```text
=========================================
YÊU CẦU CÀO DỮ LIỆU MỚI (TỐI ƯU TOKEN)
=========================================
1. URL mục tiêu chính: [URL]
2. Quy luật sinh URL hoặc danh sách URL cần cào: 
   - [Định dạng sinh link hoặc đính kèm file urls.txt]
3. CSS Selector đã xác minh trên Console (nếu có):
   - Thẻ bao ngoài sản phẩm: [Ví dụ: div.product-item]
   - Thẻ chứa tên: [Ví dụ: h3.title a]
   - Thẻ chứa giá: [Ví dụ: span.price]
4. Đặc tả API ẩn (nếu có):
   - Đính kèm file response.json hoặc file network.har
5. Thông tin HTTP Headers để vượt tường lửa (nếu cần):
   - Cookie: [Dán chuỗi cookie tại đây]
   - User-Agent: [Dán chuỗi User-Agent tại đây]
6. Định dạng JSON đầu ra mong muốn:
   - [Dán cấu trúc JSON đích mẫu]
=========================================
```
