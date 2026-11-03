# -*- coding: utf-8 -*-
"""Skill JunOps — kiểm tra nhanh video đã xuất: khung đen, đứng hình, khung đen đầu/cuối.

python kiem_tra.py <video.mp4>

Cần ffmpeg trong PATH. Máy KHÔNG bắt được chữ sai chính tả, chữ đè lên mặt, hay cảnh không hợp lời nói:
vẫn phải xem lại bằng mắt.
"""
import re
import shutil
import subprocess
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    video = sys.argv[1]
    ff = shutil.which("ffmpeg")
    if not ff:
        sys.exit("Chưa có ffmpeg trong PATH. Cài ffmpeg (ví dụ: winget install Gyan.FFmpeg) rồi chạy lại.")
    cmd = [ff, "-hide_banner", "-i", video, "-vf", "blackdetect=d=0.2:pix_th=0.10,freezedetect=n=0.003:d=1.5",
           "-an", "-f", "null", "-"]
    r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    log = r.stderr
    dur = re.search(r"Duration: (\d+):(\d+):([\d.]+)", log)
    tong = int(dur.group(1)) * 3600 + int(dur.group(2)) * 60 + float(dur.group(3)) if dur else None
    den = [(float(a), float(b)) for a, b in re.findall(r"black_start:([\d.]+) black_end:([\d.]+)", log)]
    dung = list(zip([float(x) for x in re.findall(r"freeze_start: ([\d.]+)", log)],
                    [float(x) for x in re.findall(r"freeze_end: ([\d.]+)", log)]))
    loi = 0
    print(f"Video: {video}" + (f" · dài {tong:.1f}s" if tong else ""))
    for a, b in den:
        dau_cuoi = a < 0.5 or (tong and b > tong - 0.5)
        print(f"  {'🟡' if dau_cuoi else '🔴'} khung đen {a:.2f}s → {b:.2f}s" + ("  (đầu/cuối video)" if dau_cuoi else ""))
        loi += 0 if dau_cuoi else 1
    for a, b in dung:
        print(f"  🟡 đứng hình {a:.2f}s → {b:.2f}s ({b - a:.1f}s)")
    if not den and not dung:
        print("  ✅ Không thấy khung đen hay đứng hình.")
    print(f"\nLỗi nặng (🔴): {loi} · Cảnh báo (🟡): {len(den) + len(dung) - loi}")
    print("Nhớ xem lại bằng mắt: chữ sai chính tả, chữ đè lên mặt, cảnh không hợp lời nói.")


if __name__ == "__main__":
    main()
