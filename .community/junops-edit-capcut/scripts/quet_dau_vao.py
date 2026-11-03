# -*- coding: utf-8 -*-
"""Skill JunOps — quét ĐẦU VÀO người dùng đưa: 1 file video thô, hoặc 1 thư mục có video thô (+ file kịch bản).

  python quet_dau_vao.py "<file video | thư mục>" [thêm đường dẫn khác ...]

In ra: các video (thời lượng, khung, DỌC hay NGANG → mục A hay B của SKILL.md), các file có thể là kịch bản,
và việc nên làm tiếp. Không ghi/sửa gì. Cần ffprobe (đi kèm ffmpeg) — thiếu thì vẫn liệt kê file, chỉ không có thời lượng."""
import json
import os
import shutil
import subprocess
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

VIDEO = {".mp4", ".mov", ".mkv", ".m4v", ".avi", ".webm", ".mts", ".wmv"}
KICH_BAN = {".txt", ".md", ".docx", ".doc", ".xlsx", ".xls", ".csv", ".pdf", ".rtf", ".odt"}
BO_QUA = {"_backup_junops", "__pycache__", ".git", "node_modules"}


def thong_tin(p):
    ff = shutil.which("ffprobe")
    if not ff:
        return None
    try:
        out = subprocess.run([ff, "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height:stream_side_data=rotation:format=duration",
                              "-of", "json", p], capture_output=True, text=True, encoding="utf-8", timeout=60).stdout
        j = json.loads(out)
        st = (j.get("streams") or [{}])[0]
        w, h = int(st.get("width") or 0), int(st.get("height") or 0)
        rot = 0
        for sd in st.get("side_data_list") or []:
            rot = abs(int(float(sd.get("rotation", 0)))) % 180
        if rot == 90:
            w, h = h, w
        return dict(w=w, h=h, giay=float(j.get("format", {}).get("duration") or 0))
    except Exception:
        return None


def quet(duong_dan):
    vids, docs = [], []
    for d in duong_dan:
        if os.path.isfile(d):
            (vids if os.path.splitext(d)[1].lower() in VIDEO else docs).append(d)
            continue
        for r, ds, fs in os.walk(d):
            ds[:] = [x for x in ds if x not in BO_QUA]
            for f in sorted(fs):
                e = os.path.splitext(f)[1].lower()
                p = os.path.join(r, f)
                if e in VIDEO:
                    vids.append(p)
                elif e in KICH_BAN and not f.startswith("~$") and not f.endswith("_loi.txt"):
                    docs.append(p)
    return sorted(vids), sorted(docs)


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    ds = [p for p in sys.argv[1:]]
    miss = [p for p in ds if not os.path.exists(p)]
    if miss:
        sys.exit("Không thấy: " + "; ".join(miss) + "\nKiểm tra lại đường dẫn (kéo thả file/thư mục vào khung chat để lấy đúng đường dẫn).")
    vids, docs = quet(ds)
    print(f"Tìm thấy {len(vids)} video, {len(docs)} file có thể là kịch bản.\n")
    huong = {"doc": 0, "ngang": 0}
    for p in vids:
        t = thong_tin(p)
        if t and t["w"] and t["h"]:
            kieu = "DỌC (mục A)" if t["h"] > t["w"] else "NGANG (mục B)"
            huong["doc" if t["h"] > t["w"] else "ngang"] += 1
            print(f"  🎬 {p}\n     {t['w']}x{t['h']} · {t['giay'] / 60:.1f} phút ({t['giay']:.0f}s) · {kieu}")
        else:
            print(f"  🎬 {p}\n     (chưa đọc được thông số — cài ffmpeg bằng cai_dat.py --cai)")
    for p in docs:
        print(f"  📄 {p}   {os.path.getsize(p) // 1024} KB")
    print()
    if not vids:
        print("➜ CHƯA có video thô. Hỏi người dùng gửi lại đường dẫn thư mục/file video.")
        return
    if len(vids) > 1:
        print("➜ Có NHIỀU video: hỏi người dùng là làm RIÊNG từng video, hay GHÉP thành một video theo thứ tự tên file.")
    if docs:
        print("➜ Có file có thể là kịch bản: hỏi người dùng file nào là kịch bản (nếu chưa rõ), đọc nội dung rồi dùng để chọn lần nói đúng + đặt tên phần/chữ nhấn.")
    else:
        print("➜ KHÔNG có kịch bản: vẫn làm được — chép lời, bỏ lần nói vấp/khoảng lặng theo SKILL.md; hỏi người dùng có muốn dán kịch bản/ý chính không.")
    if huong["doc"] and huong["ngang"]:
        print("➜ Lẫn video dọc và ngang: hỏi người dùng định đăng ở đâu để chọn mục A hay B.")
    print("➜ Việc tiếp theo: người dùng tạo DỰ ÁN CAPCUT mới, kéo video thô vào dòng thời gian, đặt tên, ĐÓNG HẲN CapCut (xem mục «Dẫn dắt» của SKILL.md).")


if __name__ == "__main__":
    main()
