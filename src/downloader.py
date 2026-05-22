#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Alokiddy Resources Downloader
Tu dong doc cac file JSON dau ra va tai toan bo hinh anh, video, am thanh ve may.
Sau do cap nhat lai file JSON voi duong dan cuc bo (local path).
"""

import os
import re
import json
import time
import argparse
import unicodedata
from concurrent.futures import ThreadPoolExecutor, as_completed
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from tqdm import tqdm

# Dinh nghia cac thu muc mac dinh - Chuyen sang BASE_DIR la thu muc cha (root workspace)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_DOWNLOAD_DIR = os.path.join(BASE_DIR, "downloads")
JSON_CAMBRIDGE_PATH = os.path.join(BASE_DIR, "json", "alokiddy_cambridge.json")
JSON_PHONICS_PATH = os.path.join(BASE_DIR, "json", "alokiddy_phonics.json")

# Bộ lọc các tài nguyên rác (ảnh nút điều hướng UI game, icon hệ thống...)
# Tránh tải các file 404/rác do game Cocos định nghĩa hoặc liên kết chết phổ biến
EXCLUDE_DOWNLOAD_KEYWORDS = [
    'icon/pre.png', 'icon/next.png', 'pre.png', 'next.png', 'prev.png',
    'icontab', 'logo', 'avatar', 'themes', 'header', 'footer',
    'loading', 'btn_', 
    'icon_tuvung', 'icon_luyendoc', 'icon_luyenphatam',
    'icon_baihoc', 'icon_maucau', 'icon_nghehieu', 'icon_dochieu',
    'icon_luyenviet', 'icon_luyennoi', 'icon_trochoi', 'icon_baihat',
    'right.png', 'wrong.png', 'right.gif', 'wrong.gif', 'covu', 'recording', 'mic'
]

def is_trash_url(url):
    """Kiem tra xem URL co phai la tai nguyen rac/UI khong can tai khong"""
    if not url:
        return True
    url_lower = url.lower()
    # Khong bao gio loc cac file media hoc tap (.mp3, .mp4, .ogg, .wav)
    if any(ext in url_lower for ext in ['.mp3', '.mp4', '.ogg', '.wav']):
        return False
    return any(kw in url_lower for kw in EXCLUDE_DOWNLOAD_KEYWORDS)

# Header gia lap trinh duyet de tranh bi chan tai file
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Referer": "https://alokiddy.com.vn/"
}

# File log cac URL bi 404 de de dang don dep data JSON sau - Luu tai root workspace
NOT_FOUND_LOG = os.path.join(BASE_DIR, "404_not_found.log")

def make_session():
    """
    Tao mot requests.Session voi HTTPAdapter co retry built-in.
    Xu ly tu dong cac loi: ConnectionError, Timeout, 502, 503, 504.
    DNS failure (NameResolutionError) se duoc thu lai qua urllib3 Retry.
    """
    session = requests.Session()
    retry_strategy = Retry(
        total=4,                    # Tong so lan thu lai
        backoff_factor=1,           # Delay: 0s, 2s, 4s, 8s (2^n * backoff_factor)
        status_forcelist=[429, 500, 502, 503, 504],  # Thu lai cac HTTP error nay
        allowed_methods=["GET", "HEAD"],
        raise_on_status=False,
    )
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    session.headers.update(HEADERS)
    return session

# Thread-local storage de moi thread co session rieng (tranh conflict)
import threading
_thread_local = threading.local()

def get_session():
    """Lay session cua thread hien tai, tao moi neu chua co."""
    if not hasattr(_thread_local, 'session'):
        _thread_local.session = make_session()
    return _thread_local.session

def log_404(url, context_str=None):
    """Ghi URL bi 404 kem nguon goc chi tiet vao file log de de theo doi."""
    try:
        with open(NOT_FOUND_LOG, 'a', encoding='utf-8') as f:
            if context_str:
                f.write(f"[{context_str}] {url}\n")
            else:
                f.write(url + '\n')
    except Exception:
        pass

def slugify(text):
    """
    Chuyen tieng Viet co dau, ky tu dac biet thanh chuoi khong dau, cach nhau boi dau gach duoi.
    Dam bao ten thu muc hop le tren Windows va Linux.
    """
    if not text:
        return "unnamed"
    # Chuan hoa unicode va loai bo dau tieng Viet
    text = unicodedata.normalize('NFKD', text)
    text = text.encode('ascii', 'ignore').decode('utf-8')
    # Chuyen ve chu thuong
    text = text.lower()
    # Loai bo ky tu dac biet, chi giu lai chu cai, so, khoang trang, gach ngang va gach duoi
    text = re.sub(r'[^\w\s\-]', '', text)
    # Thay the khoang trang va gach ngang lien tiep bang mot dau gach duoi
    text = re.sub(r'[\s\-]+', '_', text)
    # Loai bo dau gach duoi du thua o dau va cuoi
    return text.strip('_')

def get_file_extension(url, default="bin"):
    """Lay duoi file tu URL, neu khong tim thay tra ve mac dinh"""
    # Loai bo cac query parameter neu co
    clean_url = url.split('?')[0]
    # Tim duoi file bang regex
    match = re.search(r'\.([a-zA-Z0-9]+)$', clean_url)
    if match:
        ext = match.group(1).lower()
        # De phong cac truong hop duoi qua dai hoac rac
        if len(ext) <= 4:
            return ext
    # Mot so truong hop url anh alokiddy khong co duoi ro rang
    if "image" in url or "jpg" in url:
        return "jpg"
    elif "png" in url:
        return "png"
    elif "mp4" in url:
        return "mp4"
    elif "mp3" in url:
        return "mp3"
    return default

def download_single_file(url, dest_path, dry_run=False, max_retries=5, context_str=None):
    """
    Thuc hien tai mot file duy nhat tu URL ve duong dan dich.
    Ho tro bo qua neu file da ton tai va dung dinh dang.
    Su dung requests.Session + HTTPAdapter/Retry de xu ly DNS failure, connection reset.
    Dung exponential backoff cho retry thu cong (2^attempt giay).
    """
    if not url:
        return False, "URL trong"
    
    # Chuan hoa URL (de phong URL bat dau bang //)
    if url.startswith("//"):
        url = "https:" + url
    elif not url.startswith("http"):
        # URL tuong doi (neu co)
        url = "https://file.alokiddy.com.vn" + url if url.startswith("/") else "https://" + url

    if dry_run:
        return True, "Dry-run: Se tai ve"

    # Kiem tra xem file da duoc tai truoc do chua
    if os.path.exists(dest_path):
        # Neu file da ton tai va co dung luong lon hon 0, coi nhu da tai xong
        if os.path.getsize(dest_path) > 0:
            return True, "Da ton tai (Skip)"
    
    # Tao thu muc cha neu chua co
    os.makedirs(os.path.dirname(dest_path), exist_ok=True)

    session = get_session()

    for attempt in range(1, max_retries + 1):
        try:
            # Timeout dang tuple (connect_timeout, read_timeout):
            # - 15 giay cho ket noi ban dau
            # - 60 giay cho viec doc data (file lon / mang cham)
            response = session.get(url, timeout=(15, 60), stream=True)
            if response.status_code == 200:
                # Ghi file tam roi rename de dam bao ghi thanh cong, tranh corrupt file neu ngat giua chung
                temp_path = dest_path + ".tmp"
                with open(temp_path, "wb") as f:
                    for chunk in response.iter_content(chunk_size=65536):
                        if chunk:
                            f.write(chunk)
                if os.path.exists(temp_path):
                    if os.path.exists(dest_path):
                        os.remove(dest_path)
                    os.rename(temp_path, dest_path)
                    return True, "Tai thanh cong"
                else:
                    return False, "File tam bi mat sau khi tai"
            elif response.status_code == 404:
                # HTTP 404: file khong ton tai tren server, ghi log va bo qua luon
                log_404(url, context_str)
                return False, f"HTTP Error 404"
            else:
                raise requests.exceptions.HTTPError(f"HTTP Error {response.status_code}")
        except Exception as e:
            # Don dep file tam neu bi loi
            temp_path = dest_path + ".tmp"
            if os.path.exists(temp_path):
                try:
                    os.remove(temp_path)
                except Exception:
                    pass
            
            if attempt == max_retries:
                return False, f"Loi sau {max_retries} lan thu: {str(e)}"
            
            # Exponential backoff: 2s, 4s, 8s, 16s...
            sleep_time = 2 ** attempt
            tqdm.write(f"[!] Tai that bai lan {attempt}/{max_retries}: {url[:80]}... Loi: {type(e).__name__}. Thu lai sau {sleep_time}s...")
            time.sleep(sleep_time)

    return False, "Khong the tai file sau nhieu lan thu"

def process_source(json_path, source_name, download_dir, max_workers=4, dry_run=False):
    """
    Xu ly doc file JSON, lap danh sach tai ve, chay da luong va cap nhat JSON.
    """
    if not os.path.exists(json_path):
        print(f"[-] Khong tim thay file JSON nguon: {json_path}")
        return

    print(f"[*] Dang doc du lieu tu: {json_path}")
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    # Danh sach cac task tai: { (url_goc, path_dich): [danh sach cac vi tri tham chieu trong JSON de cap nhat sau] }
    # Dung dict de gop cac URL bi trung nhau trong toan du an, tranh tai lai mot file nhieu lan
    download_tasks = {}

    # Ham phu tro de luu thong tin tham chieu phuc vu cap nhat JSON sau khi tai
    def add_task(url, dest_path, update_ref):
        if not url:
            return
        key = (url, dest_path)
        if key not in download_tasks:
            download_tasks[key] = []
        download_tasks[key].append(update_ref)

    # 1. Thu thap tat ca cac tai nguyen can tai
    for course_title, lessons in data.items():
        course_slug = slugify(course_title)
        
        for lesson_idx, lesson in enumerate(lessons):
            lesson_title = lesson.get("ten_bai_hoc", f"Lesson_{lesson_idx}")
            lesson_slug = slugify(lesson_title)
            # Neu la bai hoc mien phi, danh dau thu muc bang tien to [FREE]_ de nguoi dung de nhan biet
            if lesson.get("mien_phi") == "Có":
                lesson_folder = f"[FREE]_{lesson_slug}"
            else:
                lesson_folder = lesson_slug
            
            # Thu muc goc cua bai hoc nay
            lesson_dir = os.path.join(download_dir, source_name, course_slug, lesson_folder)

            # 1.1 Taim anh Thumbnail bai hoc (link_hinh_anh_goc)
            thumb_url = lesson.get("link_hinh_anh_goc")
            if thumb_url:
                ext = get_file_extension(thumb_url, "jpg")
                dest_thumb_path = os.path.join(lesson_dir, f"thumbnail.{ext}")
                
                # Tham chieu cap nhat: key la "thumbnail", value la lesson dict
                add_task(thumb_url, dest_thumb_path, {
                    "type": "thumbnail",
                    "lesson_dict": lesson,
                    "course": course_title,
                    "lesson": lesson_title,
                    "tab": "Ảnh Thumbnail"
                })

            # 1.2 Tai chi tiet tai nguyen cua tung tab
            tabs = lesson.get("chi_tiet_tai_nguyen", [])
            for tab_idx, tab in enumerate(tabs):
                tab_title = tab.get("ten_tab", f"Tab_{tab_idx}").strip()
                tab_slug = slugify(tab_title)
                
                # Thu muc rieng cua tab
                tab_dir = os.path.join(lesson_dir, tab_slug)

                # Media tab (MP4, MP3)
                media_list = tab.get("tai_nguyen_media", [])
                for media_idx, item in enumerate(media_list):
                    # Ho tro ca truong hop da cap nhat truoc do: item co the la dict {"url": ..., "local": ...}
                    url = item.get("url") if isinstance(item, dict) else item
                    if url:
                        if is_trash_url(url):
                            # Neu la link rac, cap nhat luon sang format {"url": ..., "local": null} va khong can tai
                            if isinstance(item, dict):
                                item["local"] = None
                            else:
                                tab["tai_nguyen_media"][media_idx] = {
                                    "url": url,
                                    "local": None
                                }
                            continue

                        ext = get_file_extension(url, "mp4")
                        # Dat ten file theo index hoac ten goc
                        file_name = url.split('/')[-1].split('?')[0]
                        if not file_name or len(file_name) < 4:
                            file_name = f"media_{media_idx}.{ext}"
                        
                        dest_media_path = os.path.join(tab_dir, "media", file_name)
                        
                        add_task(url, dest_media_path, {
                            "type": "media",
                            "tab_dict": tab,
                            "index": media_idx,
                            "course": course_title,
                            "lesson": lesson_title,
                            "tab": tab_title
                        })

                # Hinh anh tab (JPG, PNG)
                image_list = tab.get("tai_nguyen_hinh_anh", [])
                for img_idx, item in enumerate(image_list):
                    url = item.get("url") if isinstance(item, dict) else item
                    if url:
                        if is_trash_url(url):
                            # Neu la link rac, cap nhat luon sang format {"url": ..., "local": null} va khong can tai
                            if isinstance(item, dict):
                                item["local"] = None
                            else:
                                tab["tai_nguyen_hinh_anh"][img_idx] = {
                                    "url": url,
                                    "local": None
                                }
                            continue

                        ext = get_file_extension(url, "jpg")
                        file_name = url.split('/')[-1].split('?')[0]
                        if not file_name or len(file_name) < 4:
                            file_name = f"image_{img_idx}.{ext}"
                        
                        dest_img_path = os.path.join(tab_dir, "images", file_name)
                        
                        add_task(url, dest_img_path, {
                            "type": "image",
                            "tab_dict": tab,
                            "index": img_idx,
                            "course": course_title,
                            "lesson": lesson_title,
                            "tab": tab_title
                        })

    total_unique_files = len(download_tasks)
    print(f"[*] Da quet xong. Tong so file doc nhat can xu ly: {total_unique_files}")

    if total_unique_files == 0:
        print("[+] Khong co file nao can tai.")
        return

    # Dict luu ket qua anh xa tu URL goc -> duong dan local (tuong doi)
    # Dung de update lai cau truc JSON
    url_to_local_mapping = {}

    success_count = 0
    skip_count = 0
    fail_count = 0

    # 2. Thuc hien tai da luong
    print(f"[*] Bat dau tai song song su dung {max_workers} luong...")
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Gui tat ca cac tac vu tai len thread pool
        futures_map = {}
        for (url, dest_path), refs in download_tasks.items():
            ref = refs[0] if refs else {}
            course = ref.get("course", "Khóa học ẩn")
            lesson = ref.get("lesson", "Bài học ẩn")
            tab = ref.get("tab", "Phần học ẩn")
            context_str = f"Khóa: {course} | Bài: {lesson} | Phần: {tab}"
            
            future = executor.submit(download_single_file, url, dest_path, dry_run, 5, context_str)
            futures_map[future] = (url, dest_path, refs)

        # Su dung tqdm hien thi thanh tien trinh truc quan
        with tqdm(total=total_unique_files, desc=f"Downloading {source_name}") as pbar:
            for future in as_completed(futures_map):
                url, dest_path, refs = futures_map[future]
                try:
                    success, msg = future.result()
                    # Tinh toan duong dan tuong doi de ghi vao JSON
                    relative_path = os.path.relpath(dest_path, BASE_DIR).replace('\\', '/')
                    
                    if success:
                        if "Skip" in msg:
                            skip_count += 1
                        else:
                            success_count += 1
                        url_to_local_mapping[(url, id(refs))] = relative_path
                    else:
                        fail_count += 1
                        print(f"\n[-] Tai loi: {url} -> {msg}")
                        url_to_local_mapping[(url, id(refs))] = None
                except Exception as exc:
                    fail_count += 1
                    print(f"\n[-] Exception khi tai {url}: {exc}")
                    url_to_local_mapping[(url, id(refs))] = None
                
                pbar.update(1)

    # 3. Cap nhat du lieu JSON tu ket qua anh xa
    print("[*] Dang cap nhat lai thong tin vao doi tuong JSON...")
    for (url, dest_path), refs in download_tasks.items():
        # Lay relative_path tuong ung
        relative_path = url_to_local_mapping.get((url, id(refs)))

        for ref in refs:
            ref_type = ref["type"]
            
            if ref_type == "thumbnail":
                lesson_dict = ref["lesson_dict"]
                lesson_dict["link_hinh_anh_local"] = relative_path
            
            elif ref_type == "media":
                tab_dict = ref["tab_dict"]
                idx = ref["index"]
                # Cap nhat phan tu tai index tuong ung thanh dict {url, local}
                original_item = tab_dict["tai_nguyen_media"][idx]
                
                # Giu nguyen neu da la dict, chi cap nhat local path
                if isinstance(original_item, dict):
                    original_item["local"] = relative_path
                else:
                    tab_dict["tai_nguyen_media"][idx] = {
                        "url": url,
                        "local": relative_path
                    }
            
            elif ref_type == "image":
                tab_dict = ref["tab_dict"]
                idx = ref["index"]
                # Cap nhat phan tu tai index tuong ung thanh dict {url, local}
                original_item = tab_dict["tai_nguyen_hinh_anh"][idx]
                
                if isinstance(original_item, dict):
                    original_item["local"] = relative_path
                else:
                    tab_dict["tai_nguyen_hinh_anh"][idx] = {
                        "url": url,
                        "local": relative_path
                    }

    # 4. Ghi de tro lai file JSON nguon
    if not dry_run:
        # Ghi de file JSON mot cach an toan bang file tam de tranh corrupt neu mat dien/tat ngang
        temp_json_path = json_path + ".tmp"
        try:
            with open(temp_json_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=4)
            
            if os.path.exists(temp_json_path):
                if os.path.exists(json_path):
                    # Luu 1 ban backup truoc khi ghi de neu muon an toan
                    backup_path = json_path + ".bak"
                    if os.path.exists(backup_path):
                        os.remove(backup_path)
                    os.rename(json_path, backup_path)
                os.rename(temp_json_path, json_path)
                print(f"[+] Da ghi de cap nhat du lieu JSON an toan tai: {json_path}")
                # Xoa file backup sau khi ghi de hoan tat va thanh cong
                if os.path.exists(json_path + ".bak"):
                    os.remove(json_path + ".bak")
        except Exception as e:
            print(f"[-] Gap loi khi ghi file JSON moi: {e}. Van giu file JSON goc.")
            if os.path.exists(temp_json_path):
                os.remove(temp_json_path)

    # Bao cao tong ket
    print(f"\n=================== TONG KET ({source_name.upper()}) ===================")
    print(f" - Tong so file xu ly: {total_unique_files}")
    print(f" - Tai thanh cong moi: {success_count}")
    print(f" - Bo qua (da ton tai): {skip_count}")
    print(f" - Loi / Khong tai duoc: {fail_count}")
    if fail_count > 0 and os.path.exists(NOT_FOUND_LOG):
        print(f" - Cac URL bi 404 da duoc ghi vao: {NOT_FOUND_LOG}")
    print("=========================================================\n")


def main():
    parser = argparse.ArgumentParser(description="Alokiddy Resources Downloader - Tai toan bo media va hinh anh ve may.")
    parser.add_argument(
        "--source", 
        type=str, 
        choices=["cambridge", "phonics", "all"], 
        default="all",
        help="Nguon JSON can tai: 'cambridge' hoac 'phonics' hoac 'all' (mac dinh: 'all')"
    )
    parser.add_argument(
        "--workers", 
        type=int, 
        default=4,
        help="So luong tai song song cung luc (mac dinh: 4)"
    )
    parser.add_argument(
        "--dest", 
        type=str, 
        default=DEFAULT_DOWNLOAD_DIR,
        help=f"Thu muc goc luu tru file tai ve (mac dinh: {DEFAULT_DOWNLOAD_DIR})"
    )
    parser.add_argument(
        "--dry-run", 
        action="store_true",
        help="Chi quet du lieu va in ra danh sach file se tai, KHONG thuc hien tai that va KHONG ghi de JSON."
    )
    
    args = parser.parse_args()

    print(f"[*] Thu muc luu tai nguyen: {args.dest}")
    if args.dry_run:
        print("[!] Che do DRY-RUN kich hoat. Se khong tai file that va khong sua JSON.")

    # Dam bao thu muc luu ton tai
    os.makedirs(args.dest, exist_ok=True)

    if args.source in ["cambridge", "all"]:
        process_source(
            json_path=JSON_CAMBRIDGE_PATH, 
            source_name="cambridge", 
            download_dir=args.dest, 
            max_workers=args.workers,
            dry_run=args.dry_run
        )
        
    if args.source in ["phonics", "all"]:
        process_source(
            json_path=JSON_PHONICS_PATH, 
            source_name="phonics", 
            download_dir=args.dest, 
            max_workers=args.workers,
            dry_run=args.dry_run
        )

if __name__ == "__main__":
    main()
