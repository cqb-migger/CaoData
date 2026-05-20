# ============================================================
# DỰ ÁN CÀO DỮ LIỆU TỰ ĐỘNG - KHÓA HỌC PHONICS (ĐÁNH VẦN)
# File này được viết cực kỳ chi tiết nhằm mục đích giúp bạn học Python!
# ============================================================

# --- 1. NHẬP CÁC THƯ VIỆN CẦN THIẾT (IMPORTS) ---
import time       # Thư viện dùng để tạm dừng chương trình (delay), ví dụ: time.sleep(2)
import os         # Thư viện tương tác với hệ điều hành, ví dụ: tạo thư mục lưu file
import json       # Thư viện dùng để đọc/ghi dữ liệu định dạng JSON (.json)
import re         # Thư viện Regex (Regular Expression) dùng để tìm kiếm chuỗi theo quy luật
import sys        # Thư viện tương tác trực tiếp với hệ thống Python và console đầu ra
import logging    # Thư viện chuẩn để ghi nhận nhật ký (logs) chuyên nghiệp thay cho lệnh print

# Typing cung cấp các công cụ khai báo kiểu dữ liệu (Type Hinting) giúp viết code chuẩn mực
from typing import List, Dict, Any, Tuple
# Thư viện xử lý đường dẫn URL, giúp ghép 2 đường dẫn tương đối thành tuyệt đối
from urllib.parse import urljoin

# Selenium: Thư viện điều khiển trình duyệt Web tự động (Robot giả lập hành vi người dùng)
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
# Thư viện hỗ trợ tự động tải và cấu hình Driver tương thích cho Google Chrome
from webdriver_manager.chrome import ChromeDriverManager
# BeautifulSoup: Thư viện cực mạnh dùng để duyệt và bóc tách cấu trúc HTML
from bs4 import BeautifulSoup
# Concurrent.futures: Hỗ trợ lập trình song song đa luồng (Multi-threading) cực kỳ tiện lợi
from concurrent.futures import ThreadPoolExecutor, as_completed


# ============================================================
# 2. LỚP CẤU HÌNH HỆ THỐNG (SYSTEM CONFIGURATION)
# ============================================================
class Config:
    """
    Lớp này dùng để gom tất cả các cài đặt tĩnh của dự án vào một nơi duy nhất.
    Khi bạn muốn thay đổi bất kỳ cài đặt nào (như link web, số luồng Chrome, file lưu...),
    bạn chỉ cần chỉnh sửa ở đây mà không cần đi tìm và sửa code ở các dòng bên dưới.
    """
    BASE_URL = "https://alokiddy.com.vn" # Trang chủ của Alokiddy
    PHONICS_URL = "https://alokiddy.com.vn/Phonics28" # Link trực tiếp tới trang khóa học Phonics
    OUTPUT_JSON = "alokiddy_phonics.json" # Tên file JSON đầu ra chứa dữ liệu đã cào
    
    # Số lượng trình duyệt Chrome sẽ được bật lên cào song song cùng một lúc.
    # Tùy thuộc vào CPU và RAM máy tính của bạn: máy yếu nên để 2-3, máy mạnh có thể tăng lên 5-7.
    MAX_WORKERS = 4
    
    # Danh sách các từ khóa rác xuất hiện trong tên hình ảnh.
    # Robot sẽ bỏ qua (không cào) các hình ảnh có tên chứa từ khóa này để tránh lấy nhầm nút bấm, logo...
    EXCLUDE_IMAGE_KEYWORDS = [
        "logo", "btn_", "play", "pause", "next", "prev", "rotate", "diabay", 
        "maybay", "answer-status", "mic-ico", "loading", "sprite", "trans"
    ]


# ============================================================
# 3. CẤU HÌNH NHẬT KÝ HOẠT ĐỘNG (LOGGING)
# ============================================================
# logging.basicConfig giúp thiết lập giao diện dòng nhật ký in ra màn hình Console
logging.basicConfig(
    level=logging.INFO, # Đặt mức độ log là INFO (In ra các thông tin chỉ dẫn chung)
    format='%(asctime)s [%(levelname)s] %(message)s', # Định dạng log gồm: Thời gian [Mức độ] Thông tin
    datefmt='%H:%M:%S', # Định dạng thời gian in ra chỉ lấy Giờ:Phút:Giây
    handlers=[
        logging.StreamHandler(sys.stdout) # Xuất toàn bộ log trực tiếp ra cửa sổ console dòng lệnh
    ]
)
# Khởi tạo logger riêng của file Phonics
logger = logging.getLogger("PhonicsScraper")

# Cực kỳ quan trọng trên Windows: Cấu hình lại đầu ra console để hỗ trợ hiển thị 
# chuẩn mã hóa UTF-8, giúp in chữ Tiếng Việt có dấu và các ký tự phiên âm quốc tế IPA (ví dụ: /æ/) mà không bị lỗi.
sys.stdout.reconfigure(encoding='utf-8')


# ============================================================
# 4. HÀM TẠO TRÌNH DUYỆT TỰ ĐỘNG (ROBOT INITIALIZATION)
# ============================================================
def create_driver() -> webdriver.Chrome:
    """
    Hàm này khởi tạo và thiết lập một cửa sổ trình duyệt Google Chrome ẩn (Headless).
    Returns:
        webdriver.Chrome: Đối tượng trình duyệt đã được thiết lập sẵn sàng để sử dụng.
    """
    chrome_options = Options()
    
    # Bật chế độ chạy ẩn danh/không giao diện đồ họa (Headless Mode)
    # Trình duyệt sẽ chạy ngầm bên dưới hệ thống, không hiện cửa sổ để tiết kiệm CPU và RAM.
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--disable-gpu") # Tắt tăng tốc đồ họa phần cứng (cần thiết cho headless)
    chrome_options.add_argument("--no-sandbox") # Bỏ qua cơ chế bảo vệ sandbox của Chrome để chạy ổn định hơn
    chrome_options.add_argument("--disable-dev-shm-usage") # Tránh lỗi thiếu dung lượng bộ nhớ tạm thời trên Linux/Windows
    
    # Tắt tính năng tải hình ảnh thực tế từ website về máy.
    # Website chỉ hiển thị code HTML chứa liên kết ảnh chứ không tải ảnh thật, giúp tăng tốc độ tải trang gấp 3 lần!
    chrome_options.add_argument("--blink-settings=imagesEnabled=false")
    chrome_options.add_argument("--log-level=3") # Tắt toàn bộ các cảnh báo và log phụ vô ích của Google Chrome
    
    # ChromeDriverManager().install() tự động dò phiên bản Chrome máy bạn đang dùng,
    # sau đó tải bản driver tương thích về cài đặt ngầm. Bác không cần làm tay thủ công!
    service = Service(ChromeDriverManager().install())
    
    # Khởi chạy trình duyệt thật sự với các cài đặt ở trên
    return webdriver.Chrome(service=service, options=chrome_options)


# ============================================================
# 5. HÀM LẤY TÀI NGUYÊN CHI TIẾT (RESOURCE EXTRACTOR)
# ============================================================
def get_all_resources(driver: webdriver.Chrome, page_url: str) -> Dict[str, Any]:
    """
    Hàm cốt lõi chuyên đi lượm lặt tài nguyên học liệu trên trang hiện tại bao gồm:
    Video, Audio, Hình ảnh minh họa sạch, và Nội dung chữ giảng dạy.
    
    Args:
        driver (webdriver.Chrome): Trình duyệt hiện tại đang chạy của Thread đó.
        page_url (str): Link trang bài học cần lấy tài nguyên.
        
    Returns:
        Dict[str, Any]: Một từ điển (Dictionary) chứa 3 danh sách tài nguyên và nội dung chữ.
    """
    try:
        # TỐI ƯU HÓA TỐC ĐỘ: 
        # Nếu trình duyệt đang đứng sẵn ở chính URL này rồi (do vừa click tab xong),
        # thì ta chỉ việc parse DOM luôn chứ KHÔNG cần gọi driver.get() tải lại trang từ đầu!
        if driver.current_url != page_url:
            driver.get(page_url)
            time.sleep(1.5) # Chờ 1.5 giây để trang tải xong cấu trúc DOM và chạy JavaScript cơ bản

        html = driver.page_source # Lấy toàn bộ mã nguồn HTML của trang sau khi đã chạy dynamic JS
        soup = BeautifulSoup(html, 'html.parser') # Nạp mã HTML vào BeautifulSoup để dễ bóc tách

        # --- 1. LẤY NỘI DUNG VĂN BẢN SẠCH ---
        lesson_content = soup.select_one('#LessonContent') # Tìm khung chứa nội dung bài giảng chính
        text_content = ""
        if lesson_content:
            # Lấy toàn bộ chữ, tự động chèn dấu xuống dòng giữa các thẻ
            raw_text = lesson_content.get_text(separator="\n", strip=True)
            # Loại bỏ các đoạn văn bản điều hướng giao diện của trang để chỉ giữ lại kiến thức học
            for term in ["Câu tiếp theo", "Tiếp theo >", "nghe lại tại đây", "Nghe lại tại đây", "Xem hướng dẫn"]:
                raw_text = raw_text.replace(term, "")
            # Lọc bỏ các dòng chữ rỗng không có nghĩa
            text_content = "\n".join([line.strip() for line in raw_text.split("\n") if line.strip()])

        # --- 2. LẤY HÌNH ẢNH MINH HỌA ---
        image_links: List[str] = []
        if lesson_content:
            for img in lesson_content.find_all('img'):
                src = img.get('src') or img.get('data-src') # Lấy link ảnh từ thuộc tính src hoặc data-src
                if src:
                    # Bỏ qua hình ảnh nếu thuộc danh sách ảnh rác (nút bấm, icon nhỏ, logo...)
                    if any(kw in src.lower() for kw in Config.EXCLUDE_IMAGE_KEYWORDS):
                        continue
                    # Chuẩn hóa link ảnh từ tương đối thành liên kết tuyệt đối chạy được luôn
                    if src.startswith('//'): full_img_url = 'https:' + src
                    elif src.startswith('http'): full_img_url = src
                    else: full_img_url = urljoin("https://file.alokiddy.com.vn/", src)
                    image_links.append(full_img_url)

        # --- 3. KIỂM TRA VÀ XỬ LÝ IFRAME GAME (BÀI TẬP TƯƠNG TÁC COCOS) ---
        # Điểm cực kỳ thông minh: Lọc sạch các iframe theo dõi (GTM, FB pixel, doubleclick...)
        # Chỉ giữ lại các iframe học tập/game thực tế của Alokiddy.
        valid_iframes = []
        for iframe in driver.find_elements(By.TAG_NAME, "iframe"):
            src = iframe.get_attribute("src") or ""
            if not src:
                continue
            # Bỏ qua các iframe tracker quảng cáo hoặc mã độc
            if any(tracker in src.lower() for tracker in ["googletagmanager", "google", "facebook", "doubleclick", "youtube"]):
                continue
            # Chỉ lấy các iframe của trò chơi
            if any(kw in src.lower() for kw in ["cdngame", "uploads", "vocab", "cocos", "game", "lesson"]):
                valid_iframes.append(iframe)

        # Nếu phát hiện có iframe game hợp lệ, robot sẽ điều hướng chui sâu vào trong iframe đó để lấy tài nguyên
        if valid_iframes:
            iframe_src = valid_iframes[0].get_attribute("src")
            driver.get(iframe_src)
            time.sleep(1.5) # Đợi game Cocos khởi tạo và nạp dữ liệu
            html = driver.page_source
            soup = BeautifulSoup(html, 'html.parser')

        # --- 4. LẤY TẤT CẢ LIÊN KẾT VIDEO & AUDIO (MEDIA) ---
        media_links: List[str] = []
        # Tìm trong các thẻ chuẩn HTML5 như <source>, <video>, <audio>
        for tag in soup.find_all(['source', 'video', 'audio']):
            src = tag.get('src') or tag.get('data-src')
            if src:
                if src.startswith('//'): full_media_url = 'https:' + src
                elif src.startswith('http'): full_media_url = src
                else: full_media_url = urljoin(Config.BASE_URL, src)
                if full_media_url not in media_links:
                    media_links.append(full_media_url)

        # KỸ THUẬT SIÊU VIỆT: Dùng biểu thức chính quy (Regex) quét toàn bộ mã HTML 
        # để dò tìm các liên kết video/âm thanh .mp3 hoặc .mp4 ẩn sâu bên trong các file Script JS trò chơi
        js_sources = re.findall(r'https?://[^\s\'"\)]+\.(?:mp3|mp4|ogg|wav)', html)
        for js_src in js_sources:
            if js_src not in media_links:
                media_links.append(js_src)

        # Trả về kết quả sau khi loại bỏ các liên kết trùng lặp bằng hàm set()
        return {
            "media": media_links,
            "images": list(set(image_links)),
            "text": text_content
        }

    except Exception as e:
        # Nếu có bất kỳ lỗi mạng hay DOM xảy ra, in cảnh báo lỗi và trả về dữ liệu rỗng
        logger.warning(f"Lỗi khi cào tài nguyên chi tiết tại {page_url}: {e}")
        return {"media": [], "images": [], "text": ""}


# ============================================================
# 6. HÀM CÀO TIẾN TRÌNH KHÓA HỌC PHONICS (COURSE LEVEL)
# ============================================================
def scrape_phonics_course() -> Tuple[str, List[Dict[str, Any]]]:
    """
    Hàm tổng quản lý việc cào toàn bộ khóa học Phonics.
    Đầu tiên quét landing page lấy danh sách bài học, sau đó khởi chạy đa luồng cào chi tiết.
    """
    driver = create_driver() # Tạo driver tạm để tải trang danh sách bài học ban đầu
    try:
        logger.info("[START] Đang tải danh sách bài học Phonics...")
        driver.get(Config.PHONICS_URL)
        time.sleep(2)

        soup = BeautifulSoup(driver.page_source, 'html.parser')
        
        # Bóc tách tên khóa học động từ trang web
        course_title = "Phonics for Starters"
        title_el = soup.select_one('.intro_tab_new_name span') or soup.select_one('.intro_tab_new_name')
        if title_el:
            course_title = title_el.text.strip()
            if '(' in course_title:
                course_title = course_title.split('(')[0].strip()

        # Quét tất cả thẻ `a.image` có liên kết chứa chữ "/Phonics/" (đây là các bài học)
        phonics_items = soup.select('a.image[href*="/Phonics/"]')
        logger.info(f"[{course_title}] Tìm thấy {len(phonics_items)} bài học.")

        all_data: List[Dict[str, Any]] = [] # Chứa toàn bộ cấu trúc bài học
        free_lessons: List[Dict[str, str]] = [] # Chỉ chứa các bài miễn phí được dán nhãn '.lb_free'

        # Duyệt qua từng bài học tìm được
        for idx, a in enumerate(phonics_items, 1):
            img_tag = a.find('img')
            title = img_tag.get('alt', f"Phonics Unit {idx}") if img_tag else f"Phonics Unit {idx}"
            title = title.strip()
            link_bai = urljoin(Config.BASE_URL, a['href'])
            
            # Nếu thẻ chứa class '.lb_free' tức là bài này miễn phí (được mở khóa xem chi tiết)
            is_free = "Có" if a.select_one('.lb_free') else "Không"

            if is_free == "Có":
                free_lessons.append({"title": title, "link": link_bai})

            img_url = (img_tag.get('src') or "") if img_tag else ""
            if img_url.startswith('//'): img_url = 'https:' + img_url

            # Cấu trúc ban đầu của 1 bài học (tài nguyên tạm thời rỗng, sẽ điền sau ở Bước 2)
            all_data.append({
                "Tên Bài Học": title,
                "Miễn phí": is_free,
                "Link Hình Ảnh (Gốc)": img_url,
                "Nội Dung Chi Tiết": f"Bài học phát âm Phonics cho {title}",
                "Link Bài Học": link_bai,
                "Chi tiết tài nguyên": []
            })

        logger.info(f"[{course_title}] Cần cào tài nguyên chi tiết {len(free_lessons)} bài miễn phí.")

        # --- BƯỚC 2: KHỞI CHẠY ĐA LUỒNG CÀO SONG SONG CÁC BÀI MIỄN PHÍ ---
        if free_lessons:
            # Xác định số lượng luồng thực tế (không vượt quá số bài cần cào)
            actual_workers = min(Config.MAX_WORKERS, len(free_lessons))
            logger.info(f"==> Đang khởi động {actual_workers} browsers cào song song các bài Phonics miễn phí...")
            
            # Sử dụng ThreadPoolExecutor quản lý tự động việc phân phối luồng
            with ThreadPoolExecutor(max_workers=actual_workers) as executor:
                # Gửi công việc cào từng bài học cho các Thread xử lý
                futures = {
                    executor.submit(scrape_phonics_lesson, lesson): lesson['title']
                    for lesson in free_lessons
                }
                # as_completed lắng nghe và lấy kết quả của luồng nào hoàn tất công việc trước
                for future in as_completed(futures):
                    title = futures[future]
                    try:
                        detail_list = future.result() # Nhận về danh sách tài nguyên của bài học đó
                        
                        # Điền dữ liệu chi tiết vào bài học tương ứng trong all_data
                        for item in all_data:
                            if item["Tên Bài Học"] == title:
                                item["Chi tiết tài nguyên"] = detail_list
                                break
                        logger.info(f"✓ CÀO TÀI NGUYÊN THÀNH CÔNG: {title}")
                    except Exception as e:
                        logger.error(f"✗ LỖI khi cào bài Phonics '{title}': {e}")

        logger.info(f"[{course_title}] Hoàn tất cào khóa học.")
        return course_title, all_data

    finally:
        driver.quit() # Tắt trình duyệt quét chính


# ============================================================
# 7. HÀM CÀO CHI TIẾT BÀI HỌC TRONG THREAD (THREAD WORKER)
# ============================================================
def scrape_phonics_lesson(lesson: Dict[str, str]) -> List[Dict[str, Any]]:
    """
    Hàm này được chạy độc lập trên mỗi Thread/Browser riêng biệt.
    Nhiệm vụ: Lần lượt click vào 4 nút Tên lửa của bài học để kích hoạt phiên làm việc (Session) 
    và thu thập sạch sẽ tài nguyên của từng hoạt động.
    """
    driver = create_driver() # Khởi tạo riêng 1 browser Chrome độc lập cho Thread này
    detail_list: List[Dict[str, Any]] = []
    
    # Bảng ánh xạ class CSS của nút Tên lửa sang tên hoạt động trực quan
    tab_names = {
        "cl-1": "Bài học",
        "cl-2": "Từ vựng",
        "cl-3": "Luyện tập",
        "cl-6": "Bài hát"
    }
    try:
        # Load trang bài học lần đầu tiên để đếm số lượng hoạt động (nút tên lửa) thực tế
        driver.get(lesson['link'])
        time.sleep(1.5)
        floatings_count = len(driver.find_elements(By.CSS_SELECTOR, "a.floating"))

        for i in range(floatings_count):
            # Điểm cốt lõi: Refresh lại DOM bằng cách load lại URL gốc của bài học trước khi click
            # giúp tránh lỗi ElementNotInteractableException (phần tử bị mất liên kết trong DOM cũ)
            driver.get(lesson['link'])
            time.sleep(1.5)

            floatings = driver.find_elements(By.CSS_SELECTOR, "a.floating")
            if i >= len(floatings):
                break

            btn = floatings[i]
            class_attr = btn.get_attribute("class") or ""

            # Dựa vào tên class cl-1, cl-2... để định danh hoạt động tương ứng
            tab_name = "Hoạt động"
            for cl_prefix, name in tab_names.items():
                if cl_prefix in class_attr:
                    tab_name = name
                    break

            # SỬ DỤNG JAVASCRIPT ĐỂ CLICK:
            # Click bằng code JS qua Selenium mô phỏng việc bấm chuột trực tiếp vào nút Tên lửa.
            # Server Alokiddy sẽ ghi nhận Session trạng thái mới của tab hoạt động này.
            driver.execute_script("arguments[0].click();", btn)
            time.sleep(2) # Đợi trang chuyển hướng và render nạp học liệu của tab mới

            # Cào tài nguyên trực tiếp từ trạng thái trình duyệt hiện tại sau khi click
            tai_nguyen_data = get_all_resources(driver, driver.current_url)

            # Đóng gói dữ liệu hoạt động vào danh sách
            detail_list.append({
                "Bài học": tab_name,
                "Link Icon": "",  # Phonics sử dụng class css sprite chứ không có link file ảnh icon riêng biệt
                "Link gốc": driver.current_url,
                "Tài nguyên Media": tai_nguyen_data["media"],
                "Tài nguyên Hình ảnh": tai_nguyen_data["images"],
                "Nội dung văn bản": tai_nguyen_data["text"]
            })

        return detail_list

    finally:
        driver.quit() # Đóng trình duyệt của thread này khi đã hoàn thành hoặc gặp lỗi


# ============================================================
# 8. KHỞI CHẠY CHƯƠNG TRÌNH (ENTRY POINT - MAIN BLOCK)
# ============================================================
if __name__ == "__main__":
    try:
        master_data: Dict[str, List[Dict[str, Any]]] = {}

        logger.info(f"==> ĐANG CHẠY CÀO RIÊNG KHÓA HỌC PHONICS (ĐÁNH VẦN)")
        
        # Gọi hàm cào chính cho khóa Phonics
        title, data = scrape_phonics_course()
        master_data[title] = data

        # Kiểm tra và tạo thư mục "json" nếu chưa tồn tại trên máy
        os.makedirs("json", exist_ok=True)
        out_path = os.path.join("json", Config.OUTPUT_JSON)
        
        # Ghi dữ liệu dictionary thành file JSON dạng chữ UTF-8 dễ đọc, canh lề 4 khoảng trắng thụt lề
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(master_data, f, ensure_ascii=False, indent=4)

        logger.info(f"\n============================================================\nHOÀN THÀNH CÀO PHONICS! Dữ liệu đã lưu tại: '{out_path}'\n============================================================")

        # TỰ ĐỘNG TẢI TÀI NGUYÊN PHONICS NGAY LẬP TỨC
        try:
            logger.info("==> ĐANG TỰ ĐỘNG TẢI TÀI NGUYÊN PHONICS VÀ CẬP NHẬT JSON...")
            sys.path.append(os.path.dirname(os.path.abspath(__file__)))
            import downloader
            downloader.process_source(
                json_path=out_path,
                source_name="phonics",
                download_dir=downloader.DEFAULT_DOWNLOAD_DIR,
                max_workers=4
            )
            logger.info("==> TỰ ĐỘNG TẢI TÀI NGUYÊN PHONICS VÀ CẬP NHẬT JSON HOÀN TẤT!")
        except Exception as e:
            logger.error(f"Lỗi khi tự động tải tài nguyên Phonics: {e}")

    except KeyboardInterrupt:
        # Nhận diện sự kiện người dùng bấm Ctrl+C ở terminal để dừng chương trình cưỡng bức
        logger.warning("\n==> Chương trình bị dừng bởi người dùng.")
