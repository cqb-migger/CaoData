# ============================================================
# DỰ ÁN CÀO DỮ LIỆU TỰ ĐỘNG - TIẾNG ANH CAMBRIDGE (TUẦN TỰ ĐƠN LUỒNG)
# File này được viết cực kỳ chi tiết nhằm mục đích giúp bạn học Python!
# ============================================================

# --- 1. NHẬP CÁC THƯ VIỆN CẦN THIẾT (IMPORTS) ---
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
# 2. CẤU HÌNH NHẬT KÝ HOẠT ĐỘNG (LOGGING CONFIGURATION)
# ============================================================
logging.basicConfig(
    level=logging.INFO, # Hiển thị các thông điệp chỉ dẫn tổng quát trở lên
    format="%(asctime)s [%(levelname)s] %(message)s", # Định dạng dòng log: Thời gian [Mức độ] Thông tin
    datefmt="%H:%M:%S", # Định dạng giờ in ra dạng Giờ:Phút:Giây
    handlers=[
        logging.StreamHandler(sys.stdout) # Đưa toàn bộ log ra màn hình console của Windows
    ]
)
logger = logging.getLogger("AlokiddySequentialScraper")

# Cấu hình Windows Console ghi UTF-8: Ngăn ngừa lỗi "UnicodeEncodeError" 
# khi in chữ tiếng Việt có dấu hoặc ký tự phiên âm quốc tế IPA (ví dụ: /æ/, /eɪ/) ra Terminal.
sys.stdout.reconfigure(encoding='utf-8')


# ============================================================
# 3. LỚP CẤU HÌNH HỆ THỐNG (SYSTEM CONFIGURATION)
# ============================================================
class Config:
    """
    Lớp tập trung tất cả các thông số tĩnh của hệ thống.
    Giúp lập trình viên dễ dàng điều chỉnh cấu hình toàn dự án tại một nơi duy nhất.
    """
    BASE_URL: str = "https://alokiddy.com.vn" # Địa chỉ trang chủ
    # Link listing tổng hợp 6 khóa học tiếng Anh Cambridge
    CAMBRIDGE_LISTING_PAGE: str = "https://alokiddy.com.vn/gioi-thieu-ve-cambridge-n/tieng-anh-tre-em-cambridge-young-learners-english-yle-ct24"
    OUTPUT_JSON: str = "alokiddy_cambridge.json" # Tên file JSON kết quả đầu ra
    
    # Bộ lọc hình ảnh rác: robot sẽ tự động bỏ qua các ảnh có chứa các từ khóa này trong URL 
    # (tránh lấy nhầm các icon nút bấm, logo, ảnh trang trí, hiệu ứng...)
    EXCLUDE_IMAGE_KEYWORDS: List[str] = [
        'icontab', 'logo', 'avatar', 'themes', 'header', 'footer',
        'play', 'pause', 'loading', 'btn_', 'next', 'prev', 'speaker', 'audio',
        'sound', 'icon_tuvung', 'icon_luyendoc', 'icon_luyenphatam',
        'icon_baihoc', 'icon_maucau', 'icon_nghehieu', 'icon_dochieu',
        'icon_luyenviet', 'icon_luyennoi', 'icon_trochoi', 'icon_baihat',
        'right.png', 'wrong.png', 'right.gif', 'wrong.gif', 'covu', 'recording', 'mic'
    ]

# Tải và thiết lập tự động đường dẫn Driver tương thích phiên bản Google Chrome hiện tại của máy bạn
CHROME_DRIVER_PATH = ChromeDriverManager().install()


# ============================================================
# 4. HÀM KHỞI TẠO TRÌNH DUYỆT ĐƠN LUỒNG (WEBDRIVER FACTORY)
# ============================================================
def create_driver() -> webdriver.Chrome:
    """
    Tạo mới một cửa sổ Google Chrome chạy ngầm (Headless) đã tối ưu tài nguyên tối đa.
    Chạy cực kỳ tiết kiệm bộ nhớ RAM trên máy cấu hình trung bình/yếu.
    """
    opts = Options()
    opts.add_argument("--headless")       # Chạy ẩn danh ngầm bên dưới hệ thống, không mở cửa sổ UI trình duyệt
    opts.add_argument("--disable-gpu")     # Tắt tăng tốc đồ họa phần cứng
    opts.add_argument("--no-sandbox")       # Bỏ qua chế độ cô lập Chrome để chạy ổn định hơn trên nền Windows
    opts.add_argument("--disable-dev-shm-usage") # Tránh crash khi đầy bộ nhớ tạm
    
    # Tắt tải hình ảnh thật từ Web: Chỉ lấy cấu trúc mã HTML chứ không tải ảnh thật về, 
    # giúp tăng tốc tải trang lên gấp 3 lần và tiết kiệm băng thông mạng cực kỳ hiệu quả!
    opts.add_experimental_option("prefs", {"profile.managed_default_content_settings.images": 2})
    
    # page_load_strategy = 'eager': Trả về tài nguyên ngay khi nạp xong cây thư mục DOM chính
    # (DOMContentLoaded), không mất thời gian đợi tải hết CSS, phông chữ, hay các tracker quảng cáo chạy ngầm.
    opts.page_load_strategy = 'eager'
    
    # Khởi chạy trình duyệt thật sự
    return webdriver.Chrome(service=Service(CHROME_DRIVER_PATH), options=opts)


# ============================================================
# 5. HÀM TỰ ĐỘNG KHÁM PHÁ DANH SÁCH KHÓA HỌC (AUTO DISCOVER)
# ============================================================
def discover_course_urls(driver: webdriver.Chrome) -> List[Dict[str, str]]:
    """
    Sử dụng trình duyệt đang mở để truy cập trang chủ Cambridge tổng hợp,
    tự động phát hiện tất cả các khóa học tiếng Anh hiện có trên trang web.
    """
    logger.info(f"Đang quét danh sách khóa học từ: {Config.CAMBRIDGE_LISTING_PAGE}")
    driver.get(Config.CAMBRIDGE_LISTING_PAGE)
    time.sleep(1.5) # Đợi trang tải mã HTML
    soup = BeautifulSoup(driver.page_source, 'html.parser')

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
            
        # Chuẩn hóa link tuyệt đối
        full_url = href if href.startswith('http') else urljoin(Config.BASE_URL, href)
        courses.append({"name": name, "url": full_url})

    # In ra danh sách khóa học quét được lên Terminal
    logger.info(f"Đã tìm thấy {len(courses)} khóa học:")
    for i, c in enumerate(courses, 1):
        logger.info(f"   [{i}] {c['name']} -> {c['url']}")
    return courses


# ============================================================
# 6. HÀM QUÉT SÂU TÀI NGUYÊN BÀI HỌC (DEEP RESOURCE EXTRACTOR)
# ============================================================
def get_all_resources(driver: webdriver.Chrome, page_url: str) -> Dict[str, Any]:
    """
    Quét và thu thập toàn bộ tài nguyên chi tiết (Media video/audio, Hình ảnh minh họa sạch,
    Nội dung văn bản câu hỏi) trên trang hoạt động được chỉ định.
    
    Hàm này được tối ưu hóa thông minh để xử lý trơn tru cả trang HTML thường (chứa thẻ video/source)
    và trang tương tác Game từ vựng dạng iframe (game Cocos).
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
                    if any(kw in src.lower() for kw in Config.EXCLUDE_IMAGE_KEYWORDS):
                        continue
                    if src.startswith('//'): full_img_url = 'https:' + src
                    elif src.startswith('http'): full_img_url = src
                    else: full_img_url = urljoin("https://file.alokiddy.com.vn/", src)
                    image_links.append(full_img_url)

            # Dò tìm ảnh nền dạng CSS: background-image: url(...)
            for tag in lesson_content.find_all(lambda t: t.has_attr('style')):
                style = tag.get('style')
                bg_match = re.search(r'background-image\s*:\s*url\([\'""]?([^\'""\)\s]+)[\'""]?\)', style)
                if bg_match:
                    src = bg_match.group(1)
                    if any(kw in src.lower() for kw in Config.EXCLUDE_IMAGE_KEYWORDS): continue
                    if src.startswith('//'): full_img_url = 'https:' + src
                    elif src.startswith('http'): full_img_url = src
                    else: full_img_url = urljoin("https://file.alokiddy.com.vn/", src)
                    image_links.append(full_img_url)

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
                if src and not any(kw in src.lower() for kw in ['logo', 'btn_', 'load', 'play', 'pause']):
                    if src.startswith('//'): full_url = 'https:' + src
                    elif src.startswith('http'): full_url = src
                    else: full_url = urljoin("https://cdngame.alokiddy.com.vn/", src)
                    image_links.append(full_url)

            links: List[str] = []
            # Bóc tách Regex nâng cao: Dò tìm định dạng danh sách mp4 game Cocos ẩn (ví dụ: 19|starters01/U04/)
            # tự động tạo vòng lặp ghép ra đủ 19 video phát âm từ vựng mp4 chính xác 100%!
            match = re.search(r'(\d+)\|([a-zA-Z0-9_\-/]+)', html)
            if match:
                count = int(match.group(1))
                path = match.group(2)
                for i in range(1, count + 1):
                    links.append(f"https://cdngame.alokiddy.com.vn/cocos/Video/{path}{i}.mp4")

            # Lấy các thẻ âm thanh, video trong game
            for v in soup.find_all(['video', 'source', 'audio']):
                src = v.get('src')
                if src:
                    if src.startswith('//'): src = 'https:' + src
                    elif not src.startswith('http'): src = urljoin("https://cdngame.alokiddy.com.vn/", src)
                    links.append(src)

            # Quét tìm chuỗi chứa link file mp3/mp4 ẩn trong javascript game
            links.extend(re.findall(r'https?://[^\s"\']+\.(?:mp3|mp4)', html))
            
            return {
                "media": list(dict.fromkeys(links)), # dict.fromkeys() loại bỏ link trùng cực nhanh mà giữ thứ tự
                "images": list(dict.fromkeys(image_links)),
                "text": text_content
            }

        # --- TRƯỜNG HỢP B: BÀI HỌC DẠNG HTML THƯỜNG (BÀI HỌC VIDEO/AUDIO TRỰC TIẾP) ---
        links: List[str] = []
        # Lấy video/source chuẩn
        for v in soup.find_all(['video', 'source']):
            src = v.get('src')
            if src and ('.mp4' in src or '.mp3' in src):
                if src.startswith('//'): src = 'https:' + src
                elif not src.startswith('http'): src = urljoin("https://file.alokiddy.com.vn/", src)
                links.append(src)

        # Lấy audio/source chuẩn
        for a in soup.find_all(['audio', 'source']):
            src = a.get('src')
            if src and ('.mp3' in src or '.mp4' in src):
                if src.startswith('//'): src = 'https:' + src
                elif not src.startswith('http'): src = urljoin("https://file.alokiddy.com.vn/", src)
                links.append(src)

        # Dò tìm hàm Javascript gọi video popup (ví dụ: loadModalVideo('/Uploads/...mp4'))
        for v_path in re.findall(r'loadModalVideo\([\'""]([^\'"]+\.mp4)[\'""]\)', html):
            links.append(urljoin("https://file.alokiddy.com.vn/", v_path))

        # Dò tìm tất cả đường dẫn chứa /Uploads/...mp3 trực tiếp trong javascript
        for a_path in re.findall(r'[\'""]([^\'"]+\.mp3)[\'""]', html):
            if '/Uploads/' in a_path:
                links.append(urljoin("https://file.alokiddy.com.vn/", a_path))

        # Dò tìm file đa phương tiện nằm trong thư mục Uploads
        for r_path in re.findall(r'["\']\/Uploads\/[^\s"\']+\.(?:mp3|mp4)["\']', html):
            r_path = r_path.strip('"\'')
            links.append(urljoin("https://file.alokiddy.com.vn/", r_path))

        return {
            "media": list(dict.fromkeys(links)),
            "images": list(dict.fromkeys(image_links)),
            "text": text_content
        }

    except Exception as e:
        logger.error(f"[ERROR] Lỗi cào chi tiết tại {page_url}: {e}")
        return {"media": [], "images": [], "text": f"Lỗi: {e}"}


# ============================================================
# 7. HÀM CÀO TRỌN GÓI 1 KHÓA HỌC (TUẦN TỰ)
# ============================================================
def scrape_course(driver: webdriver.Chrome, course_url: str, course_hint_name: str = "") -> Tuple[str, List[Dict[str, Any]]]:
    """
    Hàm cào dữ liệu cho 1 khóa học bất kỳ.
    Duyệt tuần tự từng trang bằng duy nhất 1 trình duyệt dùng chung để tiết kiệm RAM.
    """
    logger.info(f"==> BẮT ĐẦU CÀO KHÓA HỌC: {course_hint_name or course_url}")

    # --- BƯỚC 1: Quét danh sách bài học và click nút Tải Thêm ---
    driver.get(course_url)
    time.sleep(2)

    # Mô phỏng người dùng: Nhấp liên tục vào nút "Xem thêm bài học" (.btn_more) 
    # cho đến khi hiển thị toàn bộ bài học của khóa học đó ra ngoài màn hình
    while True:
        try:
            btn = driver.find_element(By.CSS_SELECTOR, ".btn_more")
            if btn.is_displayed():
                driver.execute_script("arguments[0].click();", btn) # Click bằng JS để tránh bị che khuất
                time.sleep(0.8) # Đợi trang nạp thêm các bài mới
            else:
                break
        except:
            break # Nếu không thấy nút .btn_more nữa (đã hiện hết bài), kết thúc vòng lặp click

    soup = BeautifulSoup(driver.page_source, 'html.parser')

    # Dò tìm tên khóa học động từ các vị trí tiêu đề có thể xuất hiện
    course_title = ""
    course_title_el = soup.select_one('.intro_tab_new_name span') or soup.select_one('.intro_tab_new_name')
    if course_title_el:
        course_title = course_title_el.text.strip()
        if '(' in course_title:
            course_title = course_title.split('(')[0].strip()

    if not course_title:
        breadcrumb_links = soup.select('.nav-content a') or soup.select('#Nav a')
        if breadcrumb_links:
            course_title = breadcrumb_links[-1].text.strip()

    if not course_title:
        title_el = soup.find('title')
        if title_el:
            title_text = title_el.text.strip()
            for sep in ['-', '|', '_']:
                if sep in title_text:
                    title_text = title_text.split(sep)[0].strip()
            course_title = title_text

    if not course_title:
        course_title = course_hint_name or "alokiddy_course_data"

    logger.info(f"==> PHÁT HIỆN TÊN KHÓA HỌC: '{course_title}'")

    # Nhận dạng xem đây có phải là khóa học Phonics (Đánh vần) không
    phonics_items = soup.select('a.image[href*="/Phonics/"]')
    is_phonics = len(phonics_items) > 0

    all_data: List[Dict[str, Any]] = []
    free_lessons: List[Dict[str, str]] = []

    if is_phonics:
        logger.info(f"[{course_title}] Phát hiện khóa học dạng PHONICS (Đánh vần).")
        for idx, a in enumerate(phonics_items, 1):
            img_tag = a.find('img')
            title = img_tag.get('alt', f"Phonics Unit {idx}") if img_tag else f"Phonics Unit {idx}"
            # Loại bỏ khoảng trắng thừa nếu có
            title = title.strip()
            link_bai = urljoin(Config.BASE_URL, a['href'])
            is_free = "Có" if a.select_one('.lb_free') else "Không"

            if is_free == "Có":
                free_lessons.append({"title": title, "link": link_bai})

            img_url = (img_tag.get('src') or "") if img_tag else ""
            if img_url.startswith('//'): img_url = 'https:' + img_url

            all_data.append({
                "Tên Bài Học": title,
                "Miễn phí": is_free,
                "Link Hình Ảnh (Gốc)": img_url,
                "Nội Dung Chi Tiết": f"Bài học phát âm Phonics cho {title}",
                "Link Bài Học": link_bai,
                "Chi tiết tài nguyên": []
            })
    else:
        items = soup.select('.item_box')
        logger.info(f"==> TÌM THẤY {len(items)} BÀI HỌC TRONG KHÓA NÀY")

        for item in items:
            title_tag = item.select_one('.name_intro h3 a')
            if not title_tag:
                continue

            title = title_tag.text.strip()
            link_bai = urljoin(Config.BASE_URL, title_tag['href'])
            is_free = "Có" if item.select_one('.lb_free') else "Không"

            if is_free == "Có":
                free_lessons.append({"title": title, "link": link_bai})

            img_tag = item.find('img')
            img_url = (img_tag.get('data-src') or img_tag.get('src') or "") if img_tag else ""
            if img_url.startswith('//'): img_url = 'https:' + img_url

            content = item.select_one('.intro_news').get_text(separator="\n").strip() if item.select_one('.intro_news') else ""

            all_data.append({
                "Tên Bài Học": title,
                "Miễn phí": is_free,
                "Link Hình Ảnh (Gốc)": img_url,
                "Nội Dung Chi Tiết": content,
                "Link Bài Học": link_bai,
                "Chi tiết tài nguyên": []
            })

    logger.info(f"==> TRONG ĐÓ {len(free_lessons)} BÀI MIỄN PHÍ (SẼ CÀO SÂU TÀI NGUYÊN)")

    # --- BƯỚC 2: Cào sâu tài nguyên các bài miễn phí ---
    logger.info("--- BƯỚC 2: QUÉT TÀI NGUYÊN CHI TIẾT CÁC BÀI MIỄN PHÍ ---")
    if is_phonics:
        tab_names = {
            "cl-1": "Bài học",
            "cl-2": "Từ vựng",
            "cl-3": "Luyện tập",
            "cl-6": "Bài hát"
        }
        for lesson in free_lessons:
            logger.info(f"Đang xử lý bài Phonics: {lesson['title']}...")
            detail_list: List[Dict[str, Any]] = []

            # Lấy số lượng tab trước
            driver.get(lesson['link'])
            time.sleep(1.5)
            floatings_count = len(driver.find_elements(By.CSS_SELECTOR, "a.floating"))

            for i in range(floatings_count):
                # Reload trang chi tiết để refresh DOM
                driver.get(lesson['link'])
                time.sleep(1.5)
                
                floatings = driver.find_elements(By.CSS_SELECTOR, "a.floating")
                if i >= len(floatings):
                    break
                
                btn = floatings[i]
                class_attr = btn.get_attribute("class") or ""
                
                tab_name = "Hoạt động"
                for cl_prefix, name in tab_names.items():
                    if cl_prefix in class_attr:
                        tab_name = name
                        break
                        
                logger.info(f"   -> {tab_name}")
                
                # Click để kích hoạt tab trên server
                driver.execute_script("arguments[0].click();", btn)
                time.sleep(2)  # Đợi redirect và render nội dung tab
                
                # Cào tài nguyên trực tiếp từ trang thái hiện tại (không cần get() lại nhờ tối ưu hóa trên)
                tai_nguyen_data = get_all_resources(driver, driver.current_url)

                detail_list.append({
                    "Bài học": tab_name,
                    "Link Icon": "",  # Phonics dùng icon sprites class css, không có link img riêng biệt
                    "Link gốc": driver.current_url,
                    "Tài nguyên Media": tai_nguyen_data["media"],
                    "Tài nguyên Hình ảnh": tai_nguyen_data["images"],
                    "Nội dung văn bản": tai_nguyen_data["text"]
                })

            for item in all_data:
                if item["Tên Bài Học"] == lesson['title']:
                    item["Chi tiết tài nguyên"] = detail_list
                    break
    else:
        for lesson in free_lessons:
            logger.info(f"Đang xử lý bài: {lesson['title']}...")
            driver.get(lesson['link'])
            time.sleep(1.5)

            lesson_soup = BeautifulSoup(driver.page_source, 'html.parser')
            sections = lesson_soup.select('.mn-item-bongbay')

            # Thu thập các thẻ section trước để tránh mất DOM state khi navigate
            section_infos: List[Dict[str, str]] = []
            for sec in sections:
                name = sec.get('data-name') or sec.text.strip()
                link_goc = urljoin(Config.BASE_URL, sec.get('href', ''))
                icon = urljoin(Config.BASE_URL, sec.find('img').get('src')) if sec.find('img') else ""
                section_infos.append({"name": name, "link": link_goc, "icon": icon})

            detail_list: List[Dict[str, Any]] = []
            for sec_info in section_infos:
                name = sec_info["name"]
                link_goc = sec_info["link"]
                logger.info(f"   -> Đang lấy tài nguyên cho mục: {name}")
                tai_nguyen_data = get_all_resources(driver, link_goc)

                detail_list.append({
                    "Bài học": name,
                    "Link Icon": sec_info["icon"],
                    "Link gốc": link_goc,
                    "Tài nguyên Media": tai_nguyen_data["media"],
                    "Tài nguyên Hình ảnh": tai_nguyen_data["images"],
                    "Nội dung văn bản": tai_nguyen_data["text"]
                })

            for item in all_data:
                if item["Tên Bài Học"] == lesson['title']:
                    item["Chi tiết tài nguyên"] = detail_list
                    logger.info(f"   -> Đã gộp dữ liệu chi tiết vào bài: {lesson['title']}")
                    break

    logger.info(f"==> XONG! Đã cào {len(all_data)} bài ({len(free_lessons)} bài miễn phí có tài nguyên chi tiết)")
    return course_title, all_data


# ============================================================
# 8. ĐIỂM KHỞI CHẠY CHƯƠNG TRÌNH (ENTRY POINT - MAIN BLOCK)
# ============================================================
if __name__ == "__main__":
    driver = create_driver() # Khởi tạo 1 browser duy nhất dùng tuần tự suốt chương trình
    try:
        master_data: Dict[str, List[Dict[str, Any]]] = {}

        if len(sys.argv) > 1:
            # --- CHẾ ĐỘ ĐƠN: Cào 1 link chỉ định bằng cách truyền sau lệnh chạy ---
            target_url = sys.argv[1]
            logger.info(f"==> CHẾ ĐỘ ĐƠN TUẦN TỰ: URL: {target_url}")
            title, data = scrape_course(driver, target_url)
            master_data[title] = data

        else:
            # --- CHẾ ĐỘ TỰ ĐỘNG: Robot tự quét danh sách và cào tuần tự từng khóa học ---
            logger.info("==> CHẾ ĐỘ TỰ ĐỘNG: Sẽ quét danh sách khóa học từ trang Cambridge rồi cào tất cả")
            courses = discover_course_urls(driver)

            if not courses:
                logger.warning("Không phát hiện bất kỳ khóa học nào!")
            else:
                # Vòng lặp for duyệt tuần tự từng khóa học một cách chậm rãi, an toàn, tiết kiệm RAM
                for c in courses:
                    try:
                        title, data = scrape_course(driver, c['url'], c['name'])
                        master_data[title] = data
                        logger.info(f"✓ CÀO THÀNH CÔNG: {title} ({len(data)} bài)")
                    except Exception as e:
                        logger.error(f"✗ LỖI khi cào khóa học '{c['name']}': {e}")

        # Ghi dữ liệu dictionary ra file JSON
        os.makedirs("json", exist_ok=True)
        out_path = os.path.join("json", Config.OUTPUT_JSON)
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(master_data, f, ensure_ascii=False, indent=4)

        logger.info(f"\n============================================================\nHOÀN THÀNH TẤT CẢ! Đã ghi dữ liệu hợp nhất vào: '{out_path}'\n============================================================")

        # TỰ ĐỘNG TẢI TÀI NGUYÊN NGAY LẬP TỨC
        try:
            logger.info("==> ĐANG TỰ ĐỘNG TẢI TÀI NGUYÊN VÀ CẬP NHẬT JSON...")
            sys.path.append(os.path.dirname(os.path.abspath(__file__)))
            import downloader
            downloader.process_source(
                json_path=out_path,
                source_name="cambridge",
                download_dir=downloader.DEFAULT_DOWNLOAD_DIR,
                max_workers=4
            )
            logger.info("==> TỰ ĐỘNG TẢI TÀI NGUYÊN VÀ CẬP NHẬT JSON HOÀN TẤT!")
        except Exception as e:
            logger.error(f"Lỗi khi tự động tải tài nguyên: {e}")

    except KeyboardInterrupt:
        logger.warning("\n==> Đã bị dừng cưỡng bức bởi tổ hợp Ctrl+C.")
    finally:
        driver.quit() # Tắt trình duyệt Chrome khi kết thúc chương trình
