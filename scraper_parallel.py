# ============================================================
# DỰ ÁN CÀO DỮ LIỆU TỰ ĐỘNG - TIẾNG ANH CAMBRIDGE (ĐA LUỒNG SONG SONG)
# File này đã được refactor gọn gàng, sử dụng thư viện lõi src/core.py!
# ============================================================

# --- 1. NHẬP CÁC THƯ VIỆN CẦN THIẾT (IMPORTS) ---
import time       # Dùng để trì hoãn chương trình (chờ trang web tải xong)
import os         # Làm việc với hệ thống file, thư mục
import json       # Đọc/ghi cấu trúc dữ liệu JSON (.json)
import sys        # Giao tiếp với terminal hệ thống và nhận tham số dòng lệnh
from urllib.parse import urljoin  # Hỗ trợ ghép link tương đối thành liên kết tuyệt đối

# Khai báo kiểu dữ liệu hỗ trợ viết code chuẩn hóa (Type Hinting)
from typing import List, Dict, Tuple, Any

# Các thư viện phục vụ điều khiển trình duyệt ẩn tự động Chrome
from selenium import webdriver
from selenium.webdriver.common.by import By
from bs4 import BeautifulSoup

# Lập trình song song đa luồng (Multi-threading)
from concurrent.futures import ThreadPoolExecutor, as_completed

# Nhập các hàm, class cấu hình dùng chung từ thư viện lõi của dự án
from src.core import (
    Config,
    setup_logging,
    create_driver,
    discover_course_urls,
    get_all_resources
)

# Khởi tạo logger hoạt động cho file scraper đa luồng song song
logger = setup_logging("AlokiddyParallelScraper")


# ============================================================
# 2. HÀM CÀO TRỌN GÓI 1 KHÓA HỌC TRONG THREAD (THREAD-SAFE WORKER)
# ============================================================
def scrape_course(course_url: str, course_hint_name: str = "") -> Tuple[str, List[Dict[str, Any]]]:
    """
    Hàm cào dữ liệu cho 1 khóa học bất kỳ.
    Hàm này tự mở và tự giải phóng Webdriver của riêng nó (Thread-safe tuyệt đối), 
    cho phép chạy đồng thời hàng loạt luồng Chrome song song mà không sợ tranh chấp dữ liệu.
    """
    driver = create_driver() # Khởi tạo Chrome Driver ẩn độc lập cho riêng khóa học này
    try:
        logger.info(f"[THREAD-START] Bắt đầu cào khóa học: {course_hint_name or course_url}")

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

        # Đọc danh sách các bài học (.item_box) trên trang listing
        items = soup.select('.item_box')
        logger.info(f"[{course_title}] Phát hiện {len(items)} bài học.")

        all_data: List[Dict[str, Any]] = []
        free_lessons: List[Dict[str, str]] = []

        # Duyệt qua từng bài học để lấy thông tin cơ bản
        for item in items:
            title_tag = item.select_one('.name_intro h3 a')
            if not title_tag:
                continue

            title = title_tag.text.strip()
            link_bai = urljoin(Config.BASE_URL, title_tag['href'])
            # Dán nhãn miễn phí nếu phát hiện class '.lb_free'
            is_free = "Có" if item.select_one('.lb_free') else "Không"

            # Lưu danh sách các bài học miễn phí để cào sâu ở Bước 2
            if is_free == "Có":
                free_lessons.append({"title": title, "link": link_bai})

            img_tag = item.find('img')
            img_url = (img_tag.get('data-src') or img_tag.get('src') or "") if img_tag else ""
            if img_url.startswith('//'): img_url = 'https:' + img_url

            content = item.select_one('.intro_news').get_text(separator="\n").strip() if item.select_one('.intro_news') else ""

            # Đóng gói thông tin cơ bản
            all_data.append({
                "ten_bai_hoc": title,
                "mien_phi": is_free,
                "link_hinh_anh_goc": img_url,
                "noi_dung_chi_tiet": content,
                "link_bai_hoc": link_bai,
                "chi_tiet_tai_nguyen": []
            })

        logger.info(f"[{course_title}] Cần cào chi tiết {len(free_lessons)} bài miễn phí.")

        # --- BƯỚC 2: Cào sâu tài nguyên các bài miễn phí (Quét các bong bóng hoạt động) ---
        for lesson in free_lessons:
            logger.info(f"[{course_title}] Tiến hành cào bài: {lesson['title']}")
            driver.get(lesson['link'])
            time.sleep(1.5)

            lesson_soup = BeautifulSoup(driver.page_source, 'html.parser')
            # Lấy các quả bong bóng hoạt động (.mn-item-bongbay) như: Bài học, Từ vựng, Nói, Viết...
            sections = lesson_soup.select('.mn-item-bongbay')

            # Lưu danh sách thông tin section trước khi điều hướng 
            # để tránh lỗi mất phần tử DOM động khi Selenium nhảy trang
            section_infos: List[Dict[str, str]] = []
            for sec in sections:
                name = sec.get('data-name') or sec.text.strip()
                link_goc = urljoin(Config.BASE_URL, sec.get('href', ''))
                icon = urljoin(Config.BASE_URL, sec.find('img').get('src')) if sec.find('img') else ""
                section_infos.append({"name": name, "link": link_goc, "icon": icon})

            detail_list: List[Dict[str, Any]] = []
            # Duyệt qua từng quả bong bóng để cào tài nguyên chi tiết
            for sec_info in section_infos:
                name = sec_info["name"]
                link_goc = sec_info["link"]
                logger.info(f"   [{course_title}] -> {name}")
                
                # Gọi hàm quét sâu tài nguyên dùng chung
                tai_nguyen_data = get_all_resources(driver, link_goc)

                # Ghi nhận tài nguyên bóc tách được của hoạt động
                detail_list.append({
                    "ten_tab": name,
                    "link_icon": sec_info["icon"],
                    "link_goc": link_goc,
                    "tai_nguyen_media": tai_nguyen_data["media"],
                    "tai_nguyen_hinh_anh": tai_nguyen_data["images"],
                    "noi_dung_van_ban": tai_nguyen_data["text"]
                })

            # Gộp dữ liệu tài nguyên chi tiết vào bài học gốc
            for item in all_data:
                if item["ten_bai_hoc"] == lesson['title']:
                    item["chi_tiet_tai_nguyen"] = detail_list
                    break

        logger.info(f"[{course_title}] HOÀN TẤT THÀNH CÔNG.")
        return course_title, all_data

    finally:
        driver.quit()  # Đảm bảo tắt Chrome ở mọi kịch bản lỗi để giải phóng tài nguyên hệ thống


# ============================================================
# 3. ĐIỂM KHỞI CHẠY CHƯƠNG TRÌNH (ENTRY POINT - MAIN BLOCK)
# ============================================================
if __name__ == "__main__":
    try:
        master_data: Dict[str, List[Dict[str, Any]]] = {}

        # Trình chạy hỗ trợ 2 chế độ:
        # 1. Chế độ đơn (Bác truyền link trực tiếp sau lệnh chạy, ví dụ: python scraper_parallel.py "link-web")
        # 2. Chế độ tự động hoàn toàn (Không truyền gì: robot tự quét danh sách và cào song song toàn bộ)
        if len(sys.argv) > 1:
            # --- CHẾ ĐỘ ĐƠN (CÀO DUY NHẤT 1 LINK CHỈ ĐỊNH) ---
            target_url = sys.argv[1]
            logger.info(f"==> CHẾ ĐỘ ĐƠN SONG SONG: URL: {target_url}")
            title, data = scrape_course(target_url)
            master_data[title] = data

        else:
            # --- CHẾ ĐỘ TỰ ĐỘNG SONG SONG ĐA LUỒNG TOÀN BỘ KHÓA HỌC ---
            logger.info(f"==> CHẾ ĐỘ TỰ ĐỘNG SONG SONG ĐA LUỒNG: Hạn mức {Config.DEFAULT_MAX_WORKERS} Chrome instances cùng lúc.")
            courses = discover_course_urls() # Khám phá toàn bộ khóa học hiện có trên trang Cambridge

            if not courses:
                logger.warning("Không phát hiện bất kỳ khóa học nào!")
            else:
                actual_threads = min(Config.DEFAULT_MAX_WORKERS, len(courses))
                logger.info(f"\n==> Đang khởi động {actual_threads} browsers chạy song song...")

                # Dictionary tạm dùng để lưu kết quả ánh xạ: URL khóa học -> (Tên khóa học, Dữ liệu cào được)
                # Dùng để đảm bảo thứ tự ghi file JSON giống hệt thứ tự quét ban đầu
                url_to_result: Dict[str, Tuple[str, List[Dict[str, Any]]]] = {}

                # Khởi chạy ThreadPoolExecutor để quản lý song song đa luồng Chrome
                with ThreadPoolExecutor(max_workers=actual_threads) as executor:
                    # submit() gửi công việc cào khóa học vào hàng đợi đa luồng
                    futures = {
                        executor.submit(scrape_course, c['url'], c['name']): c
                        for c in courses
                    }
                    # Lấy kết quả của các luồng khi chúng kết thúc công việc
                    for future in as_completed(futures):
                        course = futures[future]
                        try:
                            title, data = future.result()
                            url_to_result[course['url']] = (title, data)
                            logger.info(f"✓ CÀO THÀNH CÔNG: {title} ({len(data)} bài)")
                        except Exception as e:
                            logger.error(f"✗ LỖI đột xuất tại khóa học '{course['name']}': {e}")

                # BẢO TOÀN THỨ TỰ (REORDERING):
                # Vì các luồng hoàn thành lúc nhanh lúc chậm ngẫu nhiên khiến thứ tự bị xáo trộn,
                # vòng lặp dưới đây sắp xếp lại kết quả đúng chuẩn theo thứ tự khám phá ban đầu.
                for course in courses:
                    if course['url'] in url_to_result:
                        title, data = url_to_result[course['url']]
                        master_data[title] = data

        # Ghi toàn bộ dữ liệu hợp nhất vào file JSON kết quả
        os.makedirs("json", exist_ok=True)
        out_path = os.path.join("json", Config.CAMBRIDGE_OUTPUT_JSON)
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(master_data, f, ensure_ascii=False, indent=4)

        logger.info(f"\n============================================================\nHOÀN THÀNH TẤT CẢ! Đã ghi dữ liệu hợp nhất vào: '{out_path}'\n============================================================")

        # TỰ ĐỘNG TẢI TÀI NGUYÊN NGAY LẬP TỨC
        try:
            logger.info("==> ĐANG TỰ ĐỘNG TẢI TÀI NGUYÊN VÀ CẬP NHẬT JSON...")
            sys.path.append(os.path.dirname(os.path.abspath(__file__)))
            from src import downloader
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
        # Bắt phím dừng nóng Ctrl+C để dừng an toàn
        logger.warning("\n==> Đã bị dừng cưỡng bức bởi tổ hợp Ctrl+C.")
