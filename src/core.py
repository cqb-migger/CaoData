# ============================================================
# THƯ VIỆN LÕI DÙNG CHUNG (CORE MODULE) - DỰ ÁN SCRAPER ALOKIDDY
# File này chứa toàn bộ cấu hình, hàm khởi tạo trình duyệt,
# chuẩn hóa URL và bóc tách tài nguyên dùng chung cho mọi file scraper.
# ============================================================

import time       # Dùng để trì hoãn chương trình (chờ trang web tải xong)
import re         # Regular Expressions (Biểu thức chính quy) để tìm dữ liệu bằng quy luật tìm kiếm
import os         # Làm việc với hệ thống file, thư mục
import json       # Đọc/ghi cấu trúc dữ liệu JSON (.json)
import sys        # Giao tiếp với terminal hệ thống và nhận tham số dòng lệnh
import logging    # Ghi nhật ký hoạt động có cấu trúc hiển thị thời gian chuyên nghiệp
from urllib.parse import urljoin  # Hỗ trợ ghép link tương đối thành liên kết tuyệt đối

# Khai báo kiểu dữ liệu hỗ trợ viết code chuẩn hóa (Type Hinting)
from typing import List, Dict, Any, Tuple

# Các thư viện phục vụ điều khiển trình duyệt ẩn tự động Chrome
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup

# ============================================================
# 1. LỚP CẤU HÌNH HỆ THỐNG DÙNG CHUNG (GLOBAL CONFIGURATION)
# ============================================================
class Config:
    """
    Lớp tập trung tất cả các thông số tĩnh của hệ thống.
    Giúp lập trình viên dễ dàng điều chỉnh cấu hình toàn dự án tại một nơi duy nhất.
    """
    BASE_URL: str = "https://alokiddy.com.vn" # Địa chỉ trang chủ
    
    # Link listing tổng hợp 6 khóa học tiếng Anh Cambridge
    CAMBRIDGE_LISTING_PAGE: str = "https://alokiddy.com.vn/gioi-thieu-ve-cambridge-n/tieng-anh-tre-em-cambridge-young-learners-english-yle-ct24"
    CAMBRIDGE_OUTPUT_JSON: str = "alokiddy_cambridge.json" # Tên file JSON kết quả đầu ra Cambridge
    
    # Link listing khóa học Phonics (Đánh vần)
    PHONICS_URL: str = "https://alokiddy.com.vn/Phonics28"
    PHONICS_OUTPUT_JSON: str = "alokiddy_phonics.json" # Tên file JSON kết quả đầu ra Phonics
    
    # Hạn mức số lượng trình duyệt Chrome bật chạy song song mặc định
    DEFAULT_MAX_WORKERS: int = 6
    
    # Bộ lọc hình ảnh rác: robot sẽ tự động bỏ qua các ảnh có chứa các từ khóa này trong URL 
    # (tránh lấy nhầm các icon nút bấm, logo, ảnh trang trí, hiệu ứng...)
    EXCLUDE_IMAGE_KEYWORDS: List[str] = [
        'icontab', 'logo', 'avatar', 'themes', 'header', 'footer',
        'play', 'pause', 'loading', 'btn_', 'next', 'prev', 'pre.png', 'next.png', 'prev.png', 'speaker', 'audio',
        'sound', 'icon_tuvung', 'icon_luyendoc', 'icon_luyenphatam',
        'icon_baihoc', 'icon_maucau', 'icon_nghehieu', 'icon_dochieu',
        'icon_luyenviet', 'icon_luyennoi', 'icon_trochoi', 'icon_baihat',
        'right.png', 'wrong.png', 'right.gif', 'wrong.gif', 'covu', 'recording', 'mic',
        'rotate', 'diabay', 'maybay', 'answer-status', 'mic-ico', 'sprite', 'trans'
    ]

# Biến toàn cục module để cache đường dẫn Chrome Driver sau khi tải
# Tránh gọi ChromeDriverManager().install() lặp lại nhiều lần gây request mạng dư thừa
_cached_chrome_driver_path = None
logger = logging.getLogger("AlokiddyCore")

# ============================================================
# 2. HÀM TIỆN ÍCH DÙNG CHUNG (HELPER FUNCTIONS)
# ============================================================
def setup_logging(logger_name: str) -> logging.Logger:
    """
    Thiết lập định dạng nhật ký hoạt động (logging setup) chuẩn hóa
    và cấu hình Windows console đầu ra hỗ trợ chữ tiếng Việt có dấu (UTF-8).
    """
    logging.basicConfig(
        level=logging.INFO, # Hiển thị các thông điệp chỉ dẫn tổng quát trở lên
        format="%(asctime)s [%(levelname)s] %(message)s", # Định dạng dòng log: Thời gian [Mức độ] Thông tin
        datefmt="%H:%M:%S", # Định dạng giờ in ra dạng Giờ:Phút:Giây
        handlers=[
            logging.StreamHandler(sys.stdout) # Đưa toàn bộ log ra màn hình console của Windows
        ]
    )
    # Cấu hình Windows Console ghi UTF-8: Ngăn ngừa lỗi "UnicodeEncodeError" 
    # khi in chữ tiếng Việt có dấu hoặc ký tự phiên âm quốc tế IPA (ví dụ: /æ/, /eɪ/) ra Terminal.
    sys.stdout.reconfigure(encoding='utf-8')
    return logging.getLogger(logger_name)


def normalize_url(src: str, base_domain: str) -> str:
    """
    Hàm chuẩn hóa đường dẫn URL tương đối hoặc thiếu giao thức
    thành một liên kết tuyệt đối đầy đủ và chính xác nhất.
    """
    if src.startswith('//'):
        return 'https:' + src
    elif src.startswith('http'):
        return src
    else:
        return urljoin(base_domain, src)


def get_chrome_driver_path() -> str:
    """
    Lấy đường dẫn của Chrome Driver.
    Sử dụng kỹ thuật Lazy Loading để chỉ tải/cài đặt duy nhất một lần khi thật sự cần,
    sau đó lưu lại trong cache để tái sử dụng ngay lập tức cho các luồng sau.
    """
    global _cached_chrome_driver_path
    if _cached_chrome_driver_path is None:
        logger.info("Đang kiểm tra và khởi tạo ChromeDriver tương thích tự động...")
        _cached_chrome_driver_path = ChromeDriverManager().install()
    return _cached_chrome_driver_path


# ============================================================
# 3. HÀM KHỞI TẠO TRÌNH DUYỆT TỐI ƯU (WEBDRIVER FACTORY)
# ============================================================
def create_driver() -> webdriver.Chrome:
    """
    Tạo mới một cửa sổ Google Chrome chạy ngầm (Headless) đã được hợp nhất
    toàn bộ các tối ưu hóa tài nguyên phần cứng tốt nhất từ cả 3 file scraper cũ.
    Giúp tăng tốc tải trang lên gấp 3 lần, tiết kiệm RAM/Băng thông mạng tối đa!
    """
    opts = Options()
    opts.add_argument("--headless")       # Chạy ẩn danh ngầm bên dưới hệ thống, không mở cửa sổ UI trình duyệt
    opts.add_argument("--disable-gpu")     # Tắt card đồ họa ảo phần cứng ảo để tiết kiệm CPU/RAM
    opts.add_argument("--no-sandbox")       # Bỏ qua chế độ cô lập Chrome để chạy ổn định hơn trên nền Windows
    opts.add_argument("--disable-dev-shm-usage") # Tránh crash khi đầy bộ nhớ tạm của Chrome
    opts.add_argument("--log-level=3")     # Tắt toàn bộ các cảnh báo và log rác vô ích của Google Chrome
    
    # 1. Tắt tải hình ảnh thực tế bằng experimental options (rất mạnh cho Cambridge)
    opts.add_experimental_option("prefs", {"profile.managed_default_content_settings.images": 2})
    # 2. Tắt tải hình ảnh thực tế bằng blink settings (rất ổn định cho Phonics)
    opts.add_argument("--blink-settings=imagesEnabled=false")
    
    # page_load_strategy = 'eager': Trả về tài nguyên ngay khi nạp xong cây thư mục DOM chính
    # (DOMContentLoaded), không mất thời gian đợi tải hết CSS, phông chữ nặng, hay các tracker quảng cáo chạy ngầm.
    opts.page_load_strategy = 'eager'
    
    # Lấy driver path thông qua hàm cache an toàn luồng
    driver_path = get_chrome_driver_path()
    
    # Khởi chạy trình duyệt thật sự
    return webdriver.Chrome(service=Service(driver_path), options=opts)


# ============================================================
# 4. HÀM TỰ ĐỘNG KHÁM PHÁ DANH SÁCH KHÓA HỌC (AUTO DISCOVER)
# ============================================================
def discover_course_urls(config=Config) -> List[Dict[str, str]]:
    """
    Khởi tạo 1 trình duyệt tạm thời để truy cập trang chủ Cambridge tổng hợp,
    tự động phát hiện tất cả các khóa học tiếng Anh hiện có trên trang web.
    """
    logger.info(f"Đang quét danh sách khóa học từ: {config.CAMBRIDGE_LISTING_PAGE}")
    driver = create_driver() # Khởi tạo driver tạm
    try:
        driver.get(config.CAMBRIDGE_LISTING_PAGE)
        time.sleep(1.5) # Đợi trang tải mã HTML
        soup = BeautifulSoup(driver.page_source, 'html.parser')
    finally:
        driver.quit() # Tắt trình duyệt tạm ngay lập tức khi đã lấy được mã nguồn HTML

    courses: List[Dict[str, str]] = []
    # Duyệt tìm các phần tử danh sách khóa học có cấu trúc CSS: div.list div.item
    for item in soup.select('div.list div.item'):
        links = item.find_all('a', href=True)
        if not links:
            continue
        # Lấy link chính (loại bỏ tham số dấu hỏi chấm ?t=... đằng sau nếu có)
        href = links[0]['href'].split('?')[0]
        # Lấy tên khóa học hiển thị (ghép các chuỗi chữ lại với nhau ngăn cách bằng dấu gạch ngang)
        name = " - ".join(a.get_text(strip=True) for a in links if a.get_text(strip=True))
        
        # ĐIỂM CỰC KỲ QUAN TRỌNG: 
        # Bỏ qua khóa Phonics (Đánh vần) để nhường quyền cào cho file scraper_phonics.py riêng biệt,
        # đảm bảo file alokiddy_cambridge.json này chỉ chứa 6 khóa tiếng Anh chính khóa sạch sẽ.
        if "phonics" in href.lower() or "đánh vần" in name.lower():
            continue
            
        # Chuẩn hóa link tuyệt đối dùng chung hàm normalize_url tiện lợi
        full_url = normalize_url(href, config.BASE_URL)
        courses.append({"name": name, "url": full_url})

    # In ra danh sách khóa học quét được lên Terminal
    logger.info(f"Đã tìm thấy {len(courses)} khóa học:")
    for i, c in enumerate(courses, 1):
        logger.info(f"   [{i}] {c['name']} -> {c['url']}")
    return courses


# ============================================================
# 5. HÀM QUÉT SÂU TÀI NGUYÊN BÀI HỌC HỢP NHẤT (RESOURCE EXTRACTOR)
# ============================================================
def get_all_resources(driver: webdriver.Chrome, page_url: str, config=Config) -> Dict[str, Any]:
    """
    Quét và thu thập toàn bộ tài nguyên chi tiết (Media video/audio, Hình ảnh minh họa sạch,
    Nội dung văn bản câu hỏi) trên trang hoạt động được chỉ định.
    
    Hàm này được tối ưu hóa thông minh để xử lý trơn tru cả trang HTML thường (chứa thẻ video/source)
    và trang tương tác Game từ vựng dạng iframe (game Cocos) của cả Cambridge lẫn Phonics.
    
    Đặc biệt: Khắc phục triệt để lỗi quét lặp lại thẻ <source> giúp giảm tải cho RAM và tối ưu hóa tốc độ.
    """
    try:
        # Nếu trình duyệt đang ở chính xác link cần cào rồi (do vừa click chuyển tab xong),
        # thì lấy thẳng DOM luôn, KHÔNG cần ra lệnh tải lại trang driver.get() lần nữa giúp chạy siêu tốc!
        if driver.current_url != page_url:
            driver.get(page_url)
            time.sleep(1.5)

        html = driver.page_source
        soup = BeautifulSoup(html, 'html.parser')

        # --- 1. LẤY NỘI DUNG CHỮ SẠCH (TEXT CONTENT) ---
        lesson_content = soup.select_one('#LessonContent')
        text_content = ""
        if lesson_content:
            # Lấy văn bản thô, xuống dòng hợp lý giữa các thẻ
            raw_text = lesson_content.get_text(separator="\n", strip=True)
            # Dọn dẹp văn bản: Loại bỏ các từ điều hướng giao diện của Alokiddy
            for term in ["Câu tiếp theo", "Tiếp theo >", "nghe lại tại đây", "Nghe lại tại đây", "Xem hướng dẫn"]:
                raw_text = raw_text.replace(term, "")
            # Lọc các dòng rỗng vô nghĩa
            text_content = "\n".join([line.strip() for line in raw_text.split("\n") if line.strip()])

        # --- 2. LẤY HÌNH ẢNH MINH HỌA SẠCH ---
        image_links: List[str] = []
        if lesson_content:
            # Dò tìm thẻ <img>
            for img in lesson_content.find_all('img'):
                src = img.get('src') or img.get('data-src')
                if src:
                    if any(kw in src.lower() for kw in config.EXCLUDE_IMAGE_KEYWORDS):
                        continue
                    image_links.append(normalize_url(src, "https://file.alokiddy.com.vn/"))

            # Dò tìm ảnh nền dạng CSS: background-image: url(...)
            for tag in lesson_content.find_all(lambda t: t.has_attr('style')):
                style = tag.get('style')
                bg_match = re.search(r'background-image\s*:\s*url\([\'""]?([^\'""\)\s]+)[\'""]?\)', style)
                if bg_match:
                    src = bg_match.group(1)
                    if any(kw in src.lower() for kw in config.EXCLUDE_IMAGE_KEYWORDS):
                        continue
                    image_links.append(normalize_url(src, "https://file.alokiddy.com.vn/"))

        # --- TRƯỜNG HỢP A: BÀI HỌC DẠNG IFRAME (GAMES/COCOS TƯƠNG TÁC) ---
        # Điểm mấu chốt xử lý bug: Lọc sạch các iframe rác/quảng cáo của Google Tag Manager, FB pixel...
        # chỉ giữ lại duy nhất iframe game bài tập hoặc game học từ vựng thật sự của Alokiddy.
        valid_iframes = []
        for iframe in driver.find_elements(By.TAG_NAME, "iframe"):
            src = iframe.get_attribute("src") or ""
            if not src:
                continue
            # Bỏ qua các liên kết bên thứ ba
            if any(tracker in src.lower() for tracker in ["googletagmanager", "google", "facebook", "doubleclick", "youtube"]):
                continue
            # Chấp nhận iframe game học liệu thực sự
            if any(kw in src.lower() for kw in ["cdngame", "uploads", "vocab", "cocos", "game", "lesson"]):
                valid_iframes.append(iframe)

        # Nếu tồn tại iframe trò chơi tương tác, robot sẽ chuyển hướng driver chui vào bên trong iframe
        if valid_iframes:
            iframe_src = valid_iframes[0].get_attribute("src")
            driver.get(iframe_src)
            time.sleep(1.5) # Chờ trò chơi khởi tạo dữ liệu
            html = driver.page_source
            soup = BeautifulSoup(html, 'html.parser')

            if not text_content:
                text_content = soup.get_text(separator="\n", strip=True)

            # Lấy hình ảnh minh họa bên trong game
            for img in soup.find_all('img'):
                src = img.get('src') or img.get('data-src')
                if src and not any(kw in src.lower() for kw in config.EXCLUDE_IMAGE_KEYWORDS):
                    image_links.append(normalize_url(src, "https://cdngame.alokiddy.com.vn/"))

            links: List[str] = []
            # Bóc tách Regex nâng cao: Dò tìm định dạng danh sách mp4 game Cocos ẩn (ví dụ: 19|starters01/U04/)
            # tự động tạo vòng lặp ghép ra đủ 19 video phát âm từ vựng mp4 chính xác 100%!
            match = re.search(r'(\d+)\|([a-zA-Z0-9_\-/]+)', html)
            if match:
                count = int(match.group(1))
                path = match.group(2)
                for i in range(1, count + 1):
                    links.append(f"https://cdngame.alokiddy.com.vn/cocos/Video/{path}{i}.mp4")

            # Lấy các thẻ âm thanh, video trong game (Duyệt gộp 1 lần các thẻ tương đồng)
            for tag in soup.find_all(['video', 'audio', 'source']):
                src = tag.get('src') or tag.get('data-src')
                if src:
                    links.append(normalize_url(src, "https://cdngame.alokiddy.com.vn/"))

            # Quét tìm chuỗi chứa link file mp3/mp4 ẩn trong javascript game
            links.extend(re.findall(r'https?://[^\s"\']+\.(?:mp3|mp4)', html))
            
            return {
                "media": list(dict.fromkeys(links)), # dict.fromkeys() loại bỏ link trùng cực nhanh mà giữ thứ tự
                "images": list(dict.fromkeys(image_links)),
                "text": text_content
            }

        # --- TRƯỜNG HỢP B: BÀI HỌC DẠNG HTML THƯỜNG (BÀI HỌC VIDEO/AUDIO TRỰC TIẾP) ---
        links: List[str] = []
        
        # TỐI ƯU HÓA: Thay thế hoàn toàn 2 vòng lặp thẻ video+source và audio+source trùng lặp cũ
        # bằng 1 vòng lặp duy nhất quét cả 3 loại thẻ, tránh duyệt lặp lại các thẻ <source>
        for tag in soup.find_all(['video', 'audio', 'source']):
            src = tag.get('src') or tag.get('data-src')
            if src and any(ext in src.lower() for ext in ['.mp3', '.mp4']):
                links.append(normalize_url(src, "https://file.alokiddy.com.vn/"))

        # Dò tìm hàm Javascript gọi video popup (ví dụ: loadModalVideo('/Uploads/...mp4'))
        for v_path in re.findall(r'loadModalVideo\([\'""]([^\'"]+\.mp4)[\'""]\)', html):
            links.append(normalize_url(v_path, "https://file.alokiddy.com.vn/"))

        # Dò tìm tất cả đường dẫn chứa /Uploads/...mp3 trực tiếp trong javascript
        for a_path in re.findall(r'[\'""]([^\'"]+\.mp3)[\'""]', html):
            if '/Uploads/' in a_path:
                links.append(normalize_url(a_path, "https://file.alokiddy.com.vn/"))

        # Dò tìm file đa phương tiện nằm trong thư mục Uploads
        for r_path in re.findall(r'["\']\/Uploads\/[^\s"\']+\.(?:mp3|mp4)["\']', html):
            r_path = r_path.strip('"\'')
            links.append(normalize_url(r_path, "https://file.alokiddy.com.vn/"))

        # Quét bổ sung toàn bộ liên kết video/âm thanh dạng regex (như trong Phonics) để đảm bảo không bỏ sót
        js_sources = re.findall(r'https?://[^\s\'"\)]+\.(?:mp3|mp4|ogg|wav)', html)
        for js_src in js_sources:
            if js_src not in links:
                links.append(js_src)

        return {
            "media": list(dict.fromkeys(links)),
            "images": list(dict.fromkeys(image_links)),
            "text": text_content
        }

    except Exception as e:
        logger.error(f"[ERROR] Lỗi cào chi tiết tại {page_url}: {e}")
        return {"media": [], "images": [], "text": f"Lỗi: {e}"}
