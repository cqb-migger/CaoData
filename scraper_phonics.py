# ============================================================
# DỰ ÁN CÀO DỮ LIỆU TỰ ĐỘNG - KHÓA HỌC PHONICS (ĐÁNH VẦN)
# File này đã được refactor gọn gàng, sử dụng thư viện lõi src/core.py!
# ============================================================

# --- 1. NHẬP CÁC THƯ VIỆN CẦN THIẾT (IMPORTS) ---
import time       # Thư viện dùng để tạm dừng chương trình (delay), ví dụ: time.sleep(2)
import os         # Thư viện tương tác với hệ điều hành, ví dụ: tạo thư mục lưu file
import json       # Thư viện dùng để đọc/ghi dữ liệu định dạng JSON (.json)
import sys        # Thư viện tương tác trực tiếp với hệ thống Python và console đầu ra
from urllib.parse import urljoin  # Thư viện xử lý đường dẫn URL

# Typing cung cấp các công cụ khai báo kiểu dữ liệu (Type Hinting) giúp viết code chuẩn mực
from typing import List, Dict, Any, Tuple

# Selenium/BeautifulSoup phục vụ điều khiển trình duyệt và bóc tách DOM
from selenium import webdriver
from selenium.webdriver.common.by import By
from bs4 import BeautifulSoup

# Concurrent.futures: Hỗ trợ lập trình song song đa luồng (Multi-threading) cực kỳ tiện lợi
from concurrent.futures import ThreadPoolExecutor, as_completed

# Nhập các hàm, class cấu hình dùng chung từ thư viện lõi của dự án
from src.core import (
    Config,
    setup_logging,
    create_driver,
    get_all_resources
)

# Khởi tạo logger hoạt động cho file Phonics Scraper
logger = setup_logging("PhonicsScraper")


# ============================================================
# 2. HÀM CÀO CHI TIẾT BÀI HỌC TRONG THREAD (THREAD WORKER)
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
            # Sử dụng hàm get_all_resources() đầy đủ, mạnh mẽ từ src/core
            tai_nguyen_data = get_all_resources(driver, driver.current_url)

            # Đóng gói dữ liệu hoạt động vào danh sách
            detail_list.append({
                "ten_tab": tab_name,
                "link_icon": "",  # Phonics sử dụng class css sprite chứ không có link file ảnh icon riêng biệt
                "link_goc": driver.current_url,
                "tai_nguyen_media": tai_nguyen_data["media"],
                "tai_nguyen_hinh_anh": tai_nguyen_data["images"],
                "noi_dung_van_ban": tai_nguyen_data["text"]
            })

        return detail_list

    finally:
        driver.quit() # Đóng trình duyệt của thread này khi đã hoàn thành hoặc gặp lỗi


# ============================================================
# 3. HÀM CÀO TIẾN TRÌNH KHÓA HỌC PHONICS (COURSE LEVEL)
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
                "ten_bai_hoc": title,
                "mien_phi": is_free,
                "link_hinh_anh_goc": img_url,
                "noi_dung_chi_tiet": f"Bài học phát âm Phonics cho {title}",
                "link_bai_hoc": link_bai,
                "chi_tiet_tai_nguyen": []
              })

        logger.info(f"[{course_title}] Cần cào tài nguyên chi tiết {len(free_lessons)} bài miễn phí.")

        # --- BƯỚC 2: KHỞI CHẠY ĐA LUỒNG CÀO SONG SONG CÁC BÀI MIỄN PHÍ ---
        if free_lessons:
            # Xác định số lượng luồng thực tế (không vượt quá số bài cần cào)
            actual_workers = min(Config.DEFAULT_MAX_WORKERS, len(free_lessons))
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
                            if item["ten_bai_hoc"] == title:
                                item["chi_tiet_tai_nguyen"] = detail_list
                                break
                        logger.info(f"✓ CÀO TÀI NGUYÊN THÀNH CÔNG: {title}")
                    except Exception as e:
                        logger.error(f"✗ LỖI khi cào bài Phonics '{title}': {e}")

        logger.info(f"[{course_title}] Hoàn tất cào khóa học.")
        return course_title, all_data

    finally:
        driver.quit() # Tắt trình duyệt quét chính


# ============================================================
# 4. KHỞI CHẠY CHƯƠNG TRÌNH (ENTRY POINT - MAIN BLOCK)
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
        out_path = os.path.join("json", Config.PHONICS_OUTPUT_JSON)
        
        # Ghi dữ liệu dictionary thành file JSON dạng chữ UTF-8 dễ đọc, canh lề 4 khoảng trắng thụt lề
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(master_data, f, ensure_ascii=False, indent=4)

        logger.info(f"\n============================================================\nHOÀN THÀNH CÀO PHONICS! Dữ liệu đã lưu tại: '{out_path}'\n============================================================")

        # TỰ ĐỘNG TẢI TÀI NGUYÊN PHONICS NGAY LẬP TỨC
        try:
            logger.info("==> ĐANG TỰ ĐỘNG TẢI TÀI NGUYÊN PHONICS VÀ CẬP NHẬT JSON...")
            sys.path.append(os.path.dirname(os.path.abspath(__file__)))
            from src import downloader
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
