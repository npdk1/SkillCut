# -*- coding: utf-8 -*-
"""Skill JunOps — kiểm tra máy đã đủ đồ chưa, và cài phần thiếu.

python cai_dat.py          # chỉ kiểm tra
python cai_dat.py --cai    # tự cài những gì cài được bằng pip (faster-whisper)
"""
import importlib.util
import os
import shutil
import subprocess
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass


def main():
    cai = "--cai" in sys.argv
    ok = True
    print(f"Python {sys.version.split()[0]}", "✅" if sys.version_info >= (3, 9) else "❌ cần Python 3.9 trở lên")
    ok &= sys.version_info >= (3, 9)

    cc = os.path.expandvars(r"%LOCALAPPDATA%\CapCut\User Data\Projects\com.lveditor.draft")
    if os.path.isdir(cc):
        n = len([x for x in os.listdir(cc) if os.path.isfile(os.path.join(cc, x, "draft_content.json"))])
        print(f"CapCut: ✅ thấy {n} dự án trong {cc}")
    else:
        print("CapCut: ❌ không thấy thư mục bản nháp. Cài CapCut bản máy tính, mở và tạo 1 dự án; "
              "hoặc đặt biến môi trường CAPCUT_DRAFTS trỏ tới thư mục bản nháp của bạn.")
        ok = False

    if shutil.which("ffmpeg"):
        print("ffmpeg: ✅")
    elif cai and shutil.which("winget"):
        print("ffmpeg: đang cài bằng winget…")
        subprocess.run(["winget", "install", "-e", "--id", "Gyan.FFmpeg", "--accept-source-agreements", "--accept-package-agreements"], check=False)
        print("ffmpeg: đã cài xong — hãy MỞ LẠI cửa sổ Claude rồi làm tiếp (để máy nhận ffmpeg mới).")
        ok = False
    else:
        print("ffmpeg: ❌ chưa có. Chạy: python cai_dat.py --cai  (hoặc: winget install Gyan.FFmpeg), rồi mở lại cửa sổ Claude")
        ok = False

    for mod, pk in (("PIL", "pillow"), ("numpy", "numpy")):
        if importlib.util.find_spec(mod):
            print(f"{pk}: ✅")
        elif cai:
            print(f"{pk}: đang cài…")
            subprocess.run([sys.executable, "-m", "pip", "install", pk], check=False)
        else:
            print(f"{pk}: ❌ chưa có (cần cho motion graphic). Chạy: python cai_dat.py --cai")
            ok = False

    if importlib.util.find_spec("faster_whisper"):
        print("faster-whisper: ✅")
    elif cai:
        print("faster-whisper: đang cài…")
        subprocess.run([sys.executable, "-m", "pip", "install", "faster-whisper"], check=False)
    else:
        print("faster-whisper: ❌ chưa có (cần cho chep_loi.py). Chạy: python cai_dat.py --cai")
        ok = False
    print("\nXong." if ok else "\nCòn thiếu vài thứ (xem dòng ❌ ở trên).")


if __name__ == "__main__":
    main()
