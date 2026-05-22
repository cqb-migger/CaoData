# ============================================================
# DỰ ÁN CÀO DỮ LIỆU TỰ ĐỘNG - TIẾNG ANH CAMBRIDGE (TUẦN TỰ ĐƠN LUỒNG)
# File này đã được refactor gọn gàng, sử dụng thư viện lõi src/core.py!
# ============================================================

# --- 1. NHẬP CÁC THƯ VIỆN CẦN THIẾT (IMPORTS) ---
import time       # Dùng để trì hoãn chương trình (chờ trang web tải xong)
import os         # Làm việc với hệ thống file, thư mục
import json       # Đọc/ghi cấu trúc dữ liệu JSON (.json)
import sys        # Giao tiếp với terminal hệ thống và nhận tham số dòng lệnh
from urllib.parse import urljoin  # Hỗ trợ ghép link tương đối thành liên kết tuyệt đối

# Khai báo kiểu dữ liệu hỗ trợ viết code chuẩn hóa (Type Hinting)
from typing import List, Dict, Any, Tuple

# Các thư viện phục vụ điều khiển trình duyệt và bóc tách DOM
from selenium import webdriver
from selenium.webdriver.common.by import By
from bs4 import BeautifulSoup

# Nhập các hàm, class cấu hình dùng chung từ thư viện lõi của dự án
from src.core import (
    Config,
    setup_logging,
    create_driver,
    discover_course_urls,
    get_all_resources
)

# Khởi tạo logger hoạt động cho file scraper tuần tự
logger = setup_logging("AlokiddySequentialScraper")


# ============================================================
# 2. HÀM CÀO TRỌN GÓI 1 KHÓA HỌC (TUẦN TỰ)
# ============================================================
def scrape_course(driver: webdriver.Chrome, course_url: str, course_hint_name: str = "") -> Tuple[str, List[Dict[str, Any]]]:
    """
    Hàm cào dữ liệu cho 1 khóa học bất kỳ của Cambridge.
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

    all_data: List[Dict[str, Any]] = []
    free_lessons: List[Dict[str, str]] = []

    # Cambridge học thường (không bao gồm Phonics)
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
            "ten_bai_hoc": title,
            "mien_phi": is_free,
            "link_hinh_anh_goc": img_url,
            "noi_dung_chi_tiet": content,
            "link_bai_hoc": link_bai,
            "chi_tiet_tai_nguyen": []
        })

    logger.info(f"==> TRONG ĐÓ {len(free_lessons)} BÀI MIỄN PHÍ (SẼ CÀO SÂU TÀI NGUYÊN)")

    # --- BƯỚC 2: Cào sâu tài nguyên các bài miễn phí ---
    logger.info("--- BƯỚC 2: QUÉT TÀI NGUYÊN CHI TIẾT CÁC BÀI MIỄN PHÍ ---")
    
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
                "ten_tab": name,
                "link_icon": sec_info["icon"],
                "link_goc": link_goc,
                "tai_nguyen_media": tai_nguyen_data["media"],
                "tai_nguyen_hinh_anh": tai_nguyen_data["images"],
                "noi_dung_van_ban": tai_nguyen_data["text"]
            })

        for item in all_data:
            if item["ten_bai_hoc"] == lesson['title']:
                item["chi_tiet_tai_nguyen"] = detail_list
                logger.info(f"   -> Đã gộp dữ liệu chi tiết vào bài: {lesson['title']}")
                break

    logger.info(f"==> XONG! Đã cào {len(all_data)} bài ({len(free_lessons)} bài miễn phí có tài nguyên chi tiết)")
    return course_title, all_data


# ============================================================
# 3. ĐIỂM KHỞI CHẠY CHƯƠNG TRÌNH (ENTRY POINT - MAIN BLOCK)
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
            courses = discover_course_urls()

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
        logger.warning("\n==> Đã bị dừng cưỡng bức bởi tổ hợp Ctrl+C.")
    finally:
        driver.quit() # Tắt trình duyệt Chrome khi kết thúc chương trình
