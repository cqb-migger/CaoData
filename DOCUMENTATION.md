# 📚 DOCUMENTATION - Alokiddy Data Scraper

> Tài liệu kỹ thuật đầy đủ cho dự án cào dữ liệu học tiếng Anh tự động từ [alokiddy.com.vn](https://alokiddy.com.vn)

---

## Mục Lục

1. [Tổng quan dự án](#1-tổng-quan-dự-án)
2. [Cấu trúc thư mục](#2-cấu-trúc-thư-mục)
3. [Cài đặt môi trường](#3-cài-đặt-môi-trường)
4. [Ba file scraper và khi nào dùng cái nào](#4-ba-file-scraper-và-khi-nào-dùng-cái-nào)
5. [Luồng hoạt động chi tiết](#5-luồng-hoạt-động-chi-tiết)
6. [Cấu trúc dữ liệu đầu ra JSON](#6-cấu-trúc-dữ-liệu-đầu-ra-json)
7. [Các kỹ thuật đặc biệt quan trọng](#7-các-kỹ-thuật-đặc-biệt-quan-trọng)
8. [Điểm mù và giới hạn hiện tại](#8-điểm-mù-và-giới-hạn-hiện-tại)
9. [Hướng dẫn chạy](#9-hướng-dẫn-chạy)
10. [Ghi chú nhanh tra cứu](#10-ghi-chú-nhanh-tra-cứu)

---

## 1. Tổng quan dự án

**Mục tiêu:** Tự động thu thập (cào) toàn bộ tài nguyên học liệu tiếng Anh dành cho trẻ em từ trang web `alokiddy.com.vn` và lưu dưới dạng file JSON có cấu trúc để xử lý tiếp.

**Trang web mục tiêu:** `https://alokiddy.com.vn`  
**Phạm vi cào:** Khóa học Cambridge (Pre-Starters → Flyers) + Khóa Phonics (đánh vần)

**Dữ liệu thu thập được cho mỗi bài học MIỄN PHÍ:**
| Loại tài nguyên | Mô tả | Định dạng |
|---|---|---|
| **Media** | Video bài giảng, clip phát âm từ vựng, file audio bài tập | `.mp4`, `.mp3` |
| **Hình ảnh** | Ảnh minh họa từ vựng (đã lọc icon/rác) | URL `.jpg`, `.png` |
| **Văn bản** | Nội dung câu hỏi, đáp án, lời thoại bài học | String thuần |

> **Lưu ý quan trọng:** Chỉ các bài học được đánh dấu miễn phí (có nhãn `.lb_free`) mới được cào sâu tài nguyên. Bài có phí chỉ lưu thông tin cơ bản (tên, link, ảnh thumbnail).

---

## 2. Cấu trúc thư mục

```
CaoData/
├── scraper.py              # Cào Cambridge, đơn luồng (tuần tự) - an toàn nhất
├── scraper_parallel.py     # Cào Cambridge, đa luồng (tối đa 6 Chrome) - nhanh nhất
├── scraper_phonics.py      # Cào riêng khóa Phonics, đa luồng (4 Chrome)
├── requirements.txt        # Danh sách thư viện cần cài
├── README.md               # Hướng dẫn setup ngắn gọn
├── DOCUMENTATION.md        # File này - tài liệu kỹ thuật đầy đủ
└── json/
    ├── alokiddy_cambridge.json   # Output của scraper.py / scraper_parallel.py (~356 KB)
    └── alokiddy_phonics.json     # Output của scraper_phonics.py (~22 KB)
```

---

## 3. Cài đặt môi trường

```bash
# Tạo môi trường ảo Python
python -m venv .venv

# Kích hoạt (Windows)
.\.venv\Scripts\activate

# Cài thư viện
pip install -r requirements.txt
```

**Thư viện sử dụng:**
| Thư viện | Vai trò |
|---|---|
| `selenium` | Điều khiển Chrome ẩn, click nút, nhận DOM sau khi JS chạy xong |
| `webdriver-manager` | Tự động tải ChromeDriver đúng phiên bản với Chrome hiện tại |
| `beautifulsoup4` | Parse HTML nhanh sau khi đã lấy `page_source` từ Selenium |
| `pandas` | Có trong requirements nhưng **chưa được dùng** trong code hiện tại |
| `openpyxl` | Có trong requirements nhưng **chưa được dùng** trong code hiện tại |

> **Yêu cầu hệ thống:** Cần cài sẵn Google Chrome. ChromeDriver sẽ tự tải về tương thích.

---

## 4. Ba file scraper và khi nào dùng cái nào

### `scraper.py` — Đơn luồng, an toàn

- **Dùng khi:** Máy yếu (RAM < 8GB), muốn test ổn định, hoặc cào 1 link đơn lẻ
- **Cách chạy:**
  ```bash
  # Cào tự động toàn bộ Cambridge
  python scraper.py
  
  # Cào 1 link cụ thể
  python scraper.py "https://alokiddy.com.vn/tieng-anh-moi/..."
  ```
- **Đặc điểm:** Dùng 1 trình duyệt Chrome duy nhất cho toàn bộ chương trình, tiết kiệm RAM
- **Output:** `json/alokiddy_cambridge.json`

---

### `scraper_parallel.py` — Đa luồng, nhanh nhất

- **Dùng khi:** Máy mạnh (RAM ≥ 8GB), muốn cào toàn bộ Cambridge nhanh nhất có thể
- **Cách chạy:**
  ```bash
  # Cào tự động toàn bộ Cambridge song song
  python scraper_parallel.py
  
  # Cào 1 link cụ thể
  python scraper_parallel.py "https://alokiddy.com.vn/tieng-anh-moi/..."
  ```
- **Đặc điểm:**
  - Mỗi khóa học chạy trên 1 Thread Chrome riêng (tối đa `MAX_WORKERS = 6`)
  - Bảo toàn thứ tự khóa học trong JSON cuối dù hoàn thành không theo thứ tự
- **Output:** `json/alokiddy_cambridge.json` (cùng format với scraper.py)

---

### `scraper_phonics.py` — Riêng cho Phonics

- **Dùng khi:** Muốn cào khóa học đánh vần Phonics (cấu trúc trang khác hẳn Cambridge)
- **Cách chạy:**
  ```bash
  python scraper_phonics.py
  ```
- **Đặc điểm:**
  - URL riêng: `https://alokiddy.com.vn/Phonics28`
  - Dùng đa luồng (`MAX_WORKERS = 4`)
  - Mỗi bài học Phonics có 4 tab hoạt động (Bài học, Từ vựng, Luyện tập, Bài hát)
- **Output:** `json/alokiddy_phonics.json`

> **Tại sao tách riêng Phonics?** Vì cấu trúc HTML của trang Phonics hoàn toàn khác với Cambridge: không có `.item_box` và `.mn-item-bongbay` mà thay bằng `a.image[href*="/Phonics/"]` và `a.floating`. Hai `scraper.py` và `scraper_parallel.py` đều có logic skip Phonics để tránh trùng lặp.

---

## 5. Luồng hoạt động chi tiết

### 5A. Luồng Cambridge (`scraper.py` / `scraper_parallel.py`)

```
START
  │
  ▼
[Bước 0] Tải trang listing Cambridge
  URL: alokiddy.com.vn/gioi-thieu-ve-cambridge-n/...
  Quét: div.list > div.item > a[href]
  Lọc: bỏ qua nếu "phonics" trong href
  Kết quả: List[{name, url}] các khóa học
  │
  ▼
[Bước 1 - mỗi khóa học] Tải trang listing bài học
  Click liên tục nút ".btn_more" cho đến khi hết
  (nút này lazy-load thêm bài học)
  │
  ▼
[Bước 1.5] Xác định loại khóa học
  - Nếu có a.image[href*="/Phonics/"] → khóa Phonics (xử lý riêng)
  - Nếu không → khóa Cambridge thông thường
  │
  ▼
[Bước 2 - mỗi bài học trong khóa]
  Quét: .item_box → lấy tên, link, ảnh thumbnail, mô tả, trạng thái miễn phí
  Chỉ bài có .lb_free mới đưa vào danh sách cào sâu
  │
  ▼
[Bước 3 - mỗi bài miễn phí]
  Tải trang bài học → tìm các "bong bóng" hoạt động (.mn-item-bongbay)
  Mỗi bong bóng là 1 tab: Bài học, Từ vựng, Luyện đọc, Luyện phát âm,
                           Nghe hiểu, Luyện nói, Mẫu câu, Trò chơi, Bài hát...
  Lưu trước info (name, link, icon) để tránh mất DOM khi navigate
  │
  ▼
[Bước 4 - mỗi tab hoạt động]
  Gọi get_all_resources(driver, link_tab)
  → Xử lý 2 trường hợp (xem mục 5C)
  → Trả về {media: [...], images: [...], text: "..."}
  │
  ▼
[Bước 5] Gộp dữ liệu + ghi JSON
  json/alokiddy_cambridge.json
```

---

### 5B. Luồng Phonics (`scraper_phonics.py`)

```
START
  │
  ▼
[Bước 0] Tải trang listing Phonics
  URL: alokiddy.com.vn/Phonics28
  Quét: a.image[href*="/Phonics/"] → lấy các bài học
  Nhận diện bài miễn phí: có .lb_free bên trong
  │
  ▼
[Bước 1] Khởi chạy ThreadPoolExecutor (4 workers)
  Mỗi thread xử lý 1 bài Phonics miễn phí
  │
  ▼
[Bước 2 - mỗi thread, mỗi bài Phonics]
  Tải trang bài học
  Đếm số nút "tên lửa" (a.floating)
  Thường là 4 nút: cl-1 (Bài học), cl-2 (Từ vựng), cl-3 (Luyện tập), cl-6 (Bài hát)
  │
  ▼
[Bước 3 - mỗi nút tên lửa]
  QUAN TRỌNG: Tải lại URL gốc trước khi click (tránh lỗi DOM stale)
  Click bằng JavaScript: driver.execute_script("arguments[0].click();", btn)
  Server Alokiddy redirect sang URL mới (tạo session mới cho tab)
  │
  ▼
[Bước 4]
  Gọi get_all_resources(driver, driver.current_url)
  Ghi nhận tài nguyên tab vừa click
  │
  ▼
[Bước 5] Gộp kết quả + ghi JSON
  json/alokiddy_phonics.json
```

---

### 5C. Hàm `get_all_resources()` — Lõi bóc tách tài nguyên

Hàm này xử lý **2 trường hợp trang bài học** khác nhau hoàn toàn:

#### Trường hợp A: Trang HTML thường (Bài học video/audio trực tiếp)

Áp dụng cho: Tab "Bài học", "Luyện đọc", "Bài hát", "Mẫu câu"

```
Quét thẻ <video>, <source>, <audio> → lấy src
Dò regex loadModalVideo('/Uploads/...mp4') trong HTML → ghép URL
Dò regex các chuỗi '/Uploads/...mp3' trong JS → ghép URL
Dò regex '/Uploads/...mp3|mp4' bọc trong dấu ngoặc → ghép URL
Lấy <img> trong #LessonContent + lọc từ khóa rác
Lấy ảnh nền CSS background-image: url(...)
Lấy text thuần trong #LessonContent, dọn dẹp các từ điều hướng UI
```

#### Trường hợp B: Trang có IFRAME game (Game Cocos tương tác)

Áp dụng cho: Tab "Từ vựng", "Nghe hiểu", "Luyện nói", "Trò chơi"

```
Phát hiện: tìm <iframe> có src chứa "cdngame" / "uploads" / "vocab" / "cocos" / "game" / "lesson"
Bỏ qua: iframe của Google Tag Manager, Facebook Pixel, Doubleclick, YouTube

→ driver.get(iframe_src)   ← Robot chui thẳng vào trong iframe!

Trong iframe:
  Dò regex (N)|path/  → ghép N links video từ vựng
  (Ví dụ: "19|vocabs/Pre2/U03/" → tạo ra 19 link cdngame.../1.mp4, .../2.mp4, ...)
  
  Dò regex https://...mp3|mp4|ogg|wav trong toàn bộ HTML
  Quét thẻ <source>, <video>, <audio>
  Lấy ảnh (lọc: logo, btn_, play, load, sprite, trans...)
```

> **Tối ưu quan trọng:** Trước khi gọi `driver.get()`, hàm kiểm tra `driver.current_url != page_url`. Nếu browser đang đứng đúng trang cần lấy rồi (do vừa click xong), thì **không gọi lại** — tiết kiệm đáng kể thời gian.

---

## 6. Cấu trúc dữ liệu đầu ra JSON

### `alokiddy_cambridge.json`

```json
{
  "TÊN KHÓA HỌC": [
    {
      "Tên Bài Học": "Unit 3: Drinks",
      "Miễn phí": "Có",
      "Link Hình Ảnh (Gốc)": "https://image.alokiddy.com.vn//.../Pre2_3.jpg",
      "Nội Dung Chi Tiết": "Qua bài Unit 3: Drinks - Pre-Starters 2...",
      "Link Bài Học": "https://alokiddy.com.vn/.../unit-3-drinks-ctm6677",
      "Chi tiết tài nguyên": [
        {
          "Bài học": "Bài học",
          "Link Icon": "https://image.alokiddy.com.vn/.../icon_baihoc_act.png",
          "Link gốc": "https://alokiddy.com.vn/.../unit-3-drinks-6677?t=0",
          "Tài nguyên Media": [
            "https://file.alokiddy.com.vn//Uploads/files/video_CAM_2019/baihocchinh/Pre2/Pre2_03.mp4"
          ],
          "Tài nguyên Hình ảnh": [],
          "Nội dung văn bản": ""
        },
        {
          "Bài học": "Từ vựng",
          "Link Icon": "...",
          "Link gốc": "...?t=1",
          "Tài nguyên Media": [
            "https://cdngame.alokiddy.com.vn/cocos/Video/vocabs/Pre2/U03/1.mp4",
            "https://cdngame.alokiddy.com.vn/cocos/Video/vocabs/Pre2/U03/2.mp4",
            "... (đến 19.mp4)"
          ],
          "Tài nguyên Hình ảnh": ["https://cdngame.alokiddy.com.vn/icon/next.png"],
          "Nội dung văn bản": "alokidy"
        },
        {
          "Bài học": "Nghe hiểu",
          "Link gốc": "...?t=4",
          "Tài nguyên Media": [
            "https://file.alokiddy.com.vn//Uploads/.../U03/L6.mp3",
            "https://file.alokiddy.com.vn//Uploads/.../U03/L7.mp3"
          ],
          "Nội dung văn bản": "Câu 1\nCon hãy nghe và chọn tranh đúng nhé...\nCâu trả lời đúng là:\nTranh số 1\nCoke.\n(Coca)..."
        }
      ]
    },
    {
      "Tên Bài Học": "Unit 4: Actions",
      "Miễn phí": "Không",
      "Chi tiết tài nguyên": []    ← bài trả phí: mảng rỗng
    }
  ]
}
```

**Các khóa học trong `alokiddy_cambridge.json` (thứ tự ghi):**
- `TIẾNG ANH MẪU GIÁO LỚN` (Pre-Starters 2)
- `TIẾNG ANH LỚP 1` (Starters 1)
- ... (tương ứng các cấp độ Cambridge: Starters → Movers → Flyers)

**Các tab hoạt động thường gặp (`"Bài học"` trong `Chi tiết tài nguyên`):**

| Tab | Tham số URL | Loại media |
|---|---|---|
| Bài học (video chính) | `?t=0` | `.mp4` (video bài giảng chính) |
| Từ vựng | `?t=1` | `.mp4` (clip từ vựng từ Cocos game) |
| Luyện đọc | `?t=2` | `.mp4` (video luyện đọc) |
| Luyện phát âm | `?t=3` | `.mp4` hoặc `.mp3` |
| Nghe hiểu | `?t=4` | `.mp3` (nhiều file audio câu hỏi) + text đầy đủ đáp án |
| Luyện nói | `?t=5` | `.mp3` + text câu cần luyện |
| Mẫu câu | `?t=4` hoặc khác | `.mp4` |
| Trò chơi 1, 2 | `?t=6`, `?t=7` | Thường rỗng (game Flash/HTML5 phức tạp) |
| Bài hát | `?t=8` | `.mp4` (video bài hát) |

---

### `alokiddy_phonics.json`

Cùng cấu trúc nhưng `Chi tiết tài nguyên` chứa tối đa 4 tab:

| Tab | Class CSS nút tên lửa |
|---|---|
| `"Bài học"` | `cl-1` |
| `"Từ vựng"` | `cl-2` |
| `"Luyện tập"` | `cl-3` |
| `"Bài hát"` | `cl-6` |

> **Lưu ý:** `"Link Icon": ""` — Phonics dùng CSS sprite class, không có file icon ảnh riêng.

---

## 7. Các kỹ thuật đặc biệt quan trọng

### 7.1 Regex bóc tách playlist video Cocos

Đây là kỹ thuật quan trọng nhất để lấy toàn bộ video từ vựng từ iframe game.

```python
# HTML của game Cocos chứa chuỗi dạng: "19|vocabs/Pre2/U03/"
match = re.search(r'(\d+)\|([a-zA-Z0-9_\-/]+)', html)
if match:
    count = int(match.group(1))  # 19
    path = match.group(2)        # "vocabs/Pre2/U03/"
    for i in range(1, count + 1):
        links.append(f"https://cdngame.alokiddy.com.vn/cocos/Video/{path}{i}.mp4")
        # → cdngame.../cocos/Video/vocabs/Pre2/U03/1.mp4
        # → cdngame.../cocos/Video/vocabs/Pre2/U03/2.mp4
        # → ... đến 19.mp4
```

Nếu không có kỹ thuật này, toàn bộ video từ vựng (thường 10-31 video/bài) sẽ bị bỏ sót.

---

### 7.2 Lọc iframe tracker vs iframe game thật

```python
TRACKER_KEYWORDS = ["googletagmanager", "google", "facebook", "doubleclick", "youtube"]
GAME_KEYWORDS = ["cdngame", "uploads", "vocab", "cocos", "game", "lesson"]

for iframe in driver.find_elements(By.TAG_NAME, "iframe"):
    src = iframe.get_attribute("src") or ""
    if not src:
        continue
    if any(t in src.lower() for t in TRACKER_KEYWORDS):
        continue   # ← bỏ qua tracker quảng cáo
    if any(k in src.lower() for k in GAME_KEYWORDS):
        valid_iframes.append(iframe)  # ← giữ lại game thật
```

Tại sao cần: Mỗi trang bài học Alokiddy chứa hàng chục iframe của Google Tag Manager, Facebook Pixel, Ads... chen lẫn với iframe game học thật. Nếu không lọc sẽ bị chui vào sai iframe.

---

### 7.3 Click "Xem thêm bài học" để lazy-load đầy đủ danh sách

```python
while True:
    try:
        btn = driver.find_element(By.CSS_SELECTOR, ".btn_more")
        if btn.is_displayed():
            driver.execute_script("arguments[0].click();", btn)
            time.sleep(0.8)
        else:
            break
    except:
        break
```

Tại sao dùng JS click thay vì `.click()` thông thường: Để tránh lỗi `ElementClickInterceptedException` khi nút bị che phủ bởi các element khác (popup, overlay, banner quảng cáo).

---

### 7.4 Refresh DOM trước khi click nút Phonics (chống stale element)

```python
for i in range(floatings_count):
    driver.get(lesson['link'])   # ← Tải lại trang TRƯỚC MỖI LẦN click
    time.sleep(1.5)
    
    floatings = driver.find_elements(By.CSS_SELECTOR, "a.floating")
    btn = floatings[i]
    driver.execute_script("arguments[0].click();", btn)
```

Tại sao phải reload: Sau khi click nút tên lửa, server redirect sang URL mới. Nếu click lần 2 mà không reload, DOM cũ đã bị hủy → `StaleElementReferenceException`. Cách giải quyết: reload URL gốc rồi tìm lại element từ đầu.

---

### 7.5 Tối ưu tốc độ trình duyệt

```python
# 1. Không tải ảnh thật (tiết kiệm băng thông, tăng tốc 3x)
opts.add_experimental_option("prefs", {
    "profile.managed_default_content_settings.images": 2
})

# 2. Tải trang ở chế độ "eager" - trả về ngay khi DOM sẵn sàng
# (không chờ CSS, font, tracker quảng cáo load xong)
opts.page_load_strategy = 'eager'
```

---

### 7.6 Khởi tạo ChromeDriver một lần duy nhất (scraper.py)

```python
# Module-level — chỉ chạy 1 lần khi import
CHROME_DRIVER_PATH = ChromeDriverManager().install()

# Tất cả browser đều dùng lại path này
return webdriver.Chrome(service=Service(CHROME_DRIVER_PATH), options=opts)
```

Trong `scraper_phonics.py`: Mỗi thread gọi `ChromeDriverManager().install()` riêng — gây overhead nhỏ nhưng không ảnh hưởng nhiều do ChromeDriverManager có cache.

---

### 7.7 Lấy ảnh nền CSS (background-image)

```python
for tag in lesson_content.find_all(lambda t: t.has_attr('style')):
    style = tag.get('style')
    bg_match = re.search(
        r'background-image\s*:\s*url\([\'"]?([^\'")\s]+)[\'"]?\)',
        style
    )
    if bg_match:
        src = bg_match.group(1)
        # ... chuẩn hóa URL + lọc từ khóa rác
```

Tại sao cần: Nhiều hình ảnh minh họa từ vựng trong Alokiddy được nhúng bằng CSS `background-image` thay vì thẻ `<img>` thông thường.

---

### 7.8 Bảo toàn thứ tự khóa học trong đa luồng (scraper_parallel.py)

```python
# Khi thread hoàn thành: lưu theo URL key (không theo thứ tự hoàn thành)
url_to_result[course['url']] = (title, data)

# Sau khi tất cả thread xong: sắp xếp lại theo thứ tự ban đầu
for course in courses:               # courses: list theo thứ tự gốc
    if course['url'] in url_to_result:
        title, data = url_to_result[course['url']]
        master_data[title] = data    # ghi vào dict theo đúng thứ tự
```

---

## 8. Điểm mù và giới hạn hiện tại

### ❌ Bài trả phí bị bỏ qua tài nguyên

`Chi tiết tài nguyên` = `[]` với mọi bài có `"Miễn phí": "Không"`. Không có cơ chế bypass paywall.

### ❌ Tab "Trò chơi" thường rỗng

Các game HTML5/Flash trong tab Trò chơi 1, Trò chơi 2 có cơ chế load động phức tạp → scraper không bóc tách được media.

```json
{
  "Bài học": "Trò chơi 1",
  "Tài nguyên Media": [],    ← thường rỗng
  "Tài nguyên Hình ảnh": [],
  "Nội dung văn bản": ""
}
```

### ❌ Tab "Luyện phát âm" đôi khi rỗng

Tính năng thu âm giọng nói của học viên — không có media để cào. Tab chỉ chứa giao diện microphone.

### ⚠️ Văn bản game Cocos thô

Khi cào trong iframe game, `text_content` thường là `"alokidy"` (watermark game) thay vì nội dung thật. Văn bản thật thường chỉ lấy được ở tab Nghe hiểu và Luyện nói (trang HTML thường có `#LessonContent`).

### ⚠️ Ảnh "rác" đôi khi lọt qua

Tab Từ vựng thường lấy được 2 ảnh `next.png` và `pre.png` (nút điều hướng game Cocos). Chúng không bị lọc vì không nằm trong danh sách `EXCLUDE_IMAGE_KEYWORDS`.

### ⚠️ `pandas` và `openpyxl` trong requirements nhưng chưa dùng

Có thể đây là kế hoạch xuất Excel trong tương lai, hoặc code cũ chưa dọn.

### ⚠️ `time.sleep()` cứng nhắc

Thời gian chờ cố định (`1.5s`, `2s`) không thích ứng với tốc độ mạng. Mạng chậm có thể gây thiếu dữ liệu, mạng nhanh gây lãng phí thời gian. Giải pháp tốt hơn là dùng `WebDriverWait` với `until(EC.presence_of_element_located(...))`.

---

## 9. Hướng dẫn chạy

Hệ thống hỗ trợ cơ chế **chạy 1 bước (Unified Flow)** vô cùng tiện lợi: khi bạn chạy bất kỳ file cào (scraper) nào, sau khi quét xong nó sẽ tự động kích hoạt thư viện `src/downloader.py` để tải song song các file media về máy và ghi nhận lại đường dẫn local vào file JSON.

### 9.1 Chạy tích hợp (Khuyên dùng)

```bash
# Lựa chọn 1: Cào & Tải toàn bộ Cambridge (đa luồng, cực nhanh - Máy RAM >= 8GB)
python scraper_parallel.py

# Lựa chọn 2: Cào & Tải toàn bộ Cambridge (đơn luồng, an toàn/tiết kiệm tài nguyên)
python scraper.py

# Lựa chọn 3: Cào & Tải toàn bộ khóa học Phonics (đánh vần)
python scraper_phonics.py
```

### 9.2 Chạy bộ tải độc lập (src/downloader.py)

Mặc dù các scraper đã tự động gọi bộ tải, bạn vẫn có thể chạy `src/downloader.py` riêng lẻ để thực hiện tải lại tài nguyên, đổi thư mục lưu trữ, hoặc chạy thử nghiệm nâng cao:

```bash
# Xem hướng dẫn đầy đủ và tất cả các tùy chọn tham số
python src/downloader.py --help

# Chạy thử nghiệm xem sẽ tải bao nhiêu file (DRY-RUN - không tải thật, không sửa JSON)
python src/downloader.py --dry-run

# Tải tài nguyên cho riêng khóa Phonics (sử dụng 4 luồng tải song song)
python src/downloader.py --source phonics --workers 4

# Tải tài nguyên cho riêng khóa Cambridge
python src/downloader.py --source cambridge --workers 4

# Tải và lưu tài nguyên sang một ổ đĩa hoặc thư mục tùy chọn khác
python src/downloader.py --dest "D:/AlokiddyResources"
```

### Cấu trúc kết quả thư mục sau khi tải

Khi tải tài nguyên, hệ thống sẽ tự động chuyển đổi tên tiếng Việt và các khoảng trắng thành chuỗi không dấu, an toàn trên Windows (`slugify`).

```
CaoData/
├── json/
│   ├── alokiddy_cambridge.json   # JSON đã được cập nhật đường dẫn local
│   └── alokiddy_phonics.json     # JSON đã được cập nhật đường dẫn local
└── downloads/
    ├── cambridge/
    │   └── tieng_anh_mau_giao_lon/
    │       └── unit_3_drinks/
    │           ├── thumbnail.jpg  # Ảnh cover bài học
    │           ├── bai_hoc/
    │           │   └── media/     # Chứa các file video chính .mp4
    │           ├── luyen_phat_am/
    │           │   └── media/     # Chứa các file audio .mp3
    │           └── ...
    └── phonics/
        └── phonics_for_starters/
            └── unit_1_aa/
                ├── thumbnail.png
                ├── bai_hoc/
                │   └── media/
                └── ...
```

---

## 10. Ghi chú nhanh tra cứu

| Câu hỏi | Trả lời |
|---|---|
| Khóa học được tìm ở đâu? | Trang `alokiddy.com.vn/gioi-thieu-ve-cambridge-n/...`, CSS `div.list > div.item` |
| Bài học miễn phí nhận diện như thế nào? | Element `.lb_free` tồn tại bên trong `.item_box` |
| Tab hoạt động được điều hướng như thế nào? | Thêm `?t=0`, `?t=1`, `?t=2`... vào link bài học (Cambridge); hoặc click `a.floating` (Phonics) |
| Video từ vựng ở đâu? | `cdngame.alokiddy.com.vn/cocos/Video/vocabs/[khóa]/U[xx]/[n].mp4` |
| Video bài học chính ở đâu? | `file.alokiddy.com.vn/Uploads/files/video_CAM_2019/baihocchinh/[khóa]/...mp4` |
| Audio nghe hiểu/luyện nói? | `file.alokiddy.com.vn/Uploads/files/CAM_new_051118/[khóa]/Audio/...mp3` |
| Tại sao có scraper.py và scraper_parallel.py? | Cùng mục tiêu, khác chiến lược: đơn luồng (an toàn/tiết kiệm RAM) vs đa luồng (nhanh/tốn RAM) |
| Tại sao Phonics tách riêng? | Cấu trúc HTML khác hoàn toàn, cần logic nhận diện và điều hướng riêng |
| `pandas` trong requirements để làm gì? | Chưa được dùng — có thể dự phòng cho tính năng xuất Excel tương lai |
| Dừng chương trình giữa chừng? | Ctrl+C → được bắt bởi `except KeyboardInterrupt`, driver tắt sạch trong `finally` |
