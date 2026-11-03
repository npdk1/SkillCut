# -*- coding: utf-8 -*-
"""Skill JunOps — ĐO SÓNG ÂM THẬT (không dựa vào bản chép lời) để cắt sát tiếng, chỉnh âm lượng, tránh chữ đè mặt.

  python song_am.py khoi    <video> [--tu 100 --den 130]     các «khối tiếng nói» (bắt đầu–kết thúc chính xác, 10 ms); ghi voiced.json
  python song_am.py kiem-cat <video> <edl.json>               soi từng đoạn định cắt: cắt sớm/muộn, khoảng lặng giữa đoạn, khối âm thanh lẻ
  python song_am.py am-luong <video>                          tăng âm lượng giọng bao nhiêu dB để vạch cam xuất hiện rải rác (CapCut)
  python song_am.py luoi-mat <video> --giay 9.5,38.4 [--zoom 1.15] [--ra luoi_mat.jpg]
                                                              ảnh ghép các khung hình có kẻ lưới % chiều cao → Claude XEM ẢNH để biết mặt nằm ở đâu
EDL: danh sách [{"a": giây bắt đầu, "b": giây kết thúc, ...}] (cùng định dạng lệnh `cat`)."""
import argparse
import json
import subprocess
import sys

import numpy as np

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass
SR, HOP = 16000, 160                                  # 10 ms


def doc_am(video, sr=SR):
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", video, "-vn", "-ac", "1", "-ar", str(sr), "-f", "s16le", "-"],
                         capture_output=True).stdout
    if not raw:
        sys.exit("Không đọc được âm thanh (thiếu ffmpeg hoặc video không có tiếng).")
    return np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768


def khoi_tieng(x, khe=0.12, toi_thieu=0.06):
    """các khoảng có tiếng (giây). Ngưỡng = nền ồn + 9 dB; lấp khe < 120 ms (khoảng giữa âm tiết)."""
    n = len(x) // HOP
    db = 20 * np.log10(np.sqrt((x[:n * HOP].reshape(n, HOP) ** 2).mean(1)) + 1e-9)
    v = db > np.percentile(db, 10) + 9.0
    khoi, i = [], 0
    while i < n:
        if v[i]:
            j = i
            while j < n and v[j]:
                j += 1
            khoi.append([i / 100, j / 100])
            i = j
        else:
            i += 1
    gop = []
    for a, b in khoi:
        if gop and a - gop[-1][1] < khe:
            gop[-1][1] = b
        else:
            gop.append([a, b])
    return [(a, b) for a, b in gop if b - a >= toi_thieu]


def cmd_khoi(a):
    kh = khoi_tieng(doc_am(a.video))
    json.dump({"voiced": kh}, open("voiced.json", "w"), indent=0)
    print(f"{len(kh)} khối tiếng nói → voiced.json")
    if a.tu is not None:
        print("  ".join(f"{x:.2f}-{y:.2f}" for x, y in kh if y >= a.tu and x <= (a.den or 1e9)))


def cmd_kiem_cat(a):
    kh = khoi_tieng(doc_am(a.video))
    edl = json.load(open(a.edl, encoding="utf-8"))
    loi = 0
    for i, e in enumerate(edl):
        s, t = float(e["a"]), float(e["b"])
        ten = e.get("loi", "")[:40]
        trong = [(max(x, s), min(y, t)) for x, y in kh if y > s and x < t]
        msg = []
        for x, y in kh:                                  # khối tiếng bị cắt giữa chừng
            if x < t - 0.03 < y and y - t > 0.06:
                msg.append(f"CẮT SỚM: tiếng còn kéo tới {y:.2f}s nhưng đoạn kết thúc {t:.2f}s (mất {y - t:.2f}s cuối câu)")
            if x < s + 0.02 < y and s - x > 0.06:
                msg.append(f"CẮT MUỘN ĐẦU: tiếng đã bắt đầu từ {x:.2f}s nhưng đoạn bắt đầu {s:.2f}s")
        for (x0, y0), (x1, y1) in zip(trong, trong[1:]):
            if x1 - y0 > 0.2:
                msg.append(f"IM LẶNG GIỮA ĐOẠN {x1 - y0:.2f}s ({y0:.2f}→{x1:.2f}s) — cắt bỏ khúc này")
        if len(trong) > 1 and trong[0][1] - trong[0][0] < 0.3 and trong[1][0] - trong[0][1] > 0.3:
            msg.append(f"KHỐI LẺ {trong[0][1] - trong[0][0]:.2f}s ở đầu ({trong[0][0]:.2f}s) rồi im — nhiều khả năng là tiếng động, "
                       f"chép riêng khối này (chep_loi) nếu không ra chữ thì bỏ")
        if not trong:
            msg.append("KHÔNG CÓ TIẾNG trong đoạn này")
        print(f"[{i + 1}] {s:.2f}–{t:.2f}s {ten}: " + ("OK" if not msg else ""))
        for m in msg:
            print("     ⚠", m)
            loi += 1
    print(f"\n{loi} cảnh báo" if loi else "\nKhông thấy vấn đề.")


def cmd_am_luong(a):
    x = np.abs(doc_am(a.video, 48000))
    p = float(20 * np.log10(np.percentile(x, 99.9) + 1e-9))
    pk = float(20 * np.log10(x.max() + 1e-9))
    g = min(15.0, -6.5 - p)                              # CapCut tối đa +15 dB
    print(f"đỉnh {pk:.1f} dB · 99,9% tiếng nói {p:.1f} dB")
    print(f"→ tăng giọng **{g:+.1f} dB** (volume {10 ** (g / 20):.3f}); ở mức này chỉ vài đỉnh chạm vạch cam. SFX giữ −10 dB (volume ~0,3) để luôn nhỏ hơn giọng.")


def cmd_luoi_mat(a):
    import cv2
    cap = cv2.VideoCapture(a.video)
    tiles = []
    for t in [float(v) for v in a.giay.split(",")]:
        cap.set(cv2.CAP_PROP_POS_MSEC, t * 1000)
        ok, f = cap.read()
        if not ok:
            continue
        h, w = f.shape[:2]
        s = a.zoom
        f = cv2.warpAffine(f, np.float32([[s, 0, w / 2 * (1 - s)], [0, s, h / 2 * (1 - s)]]), (w, h))
        k = 480 / h
        f = cv2.resize(f, (int(w * k), 480))
        for j in range(1, 10):
            y = int(480 * j / 10)
            cv2.line(f, (0, y), (f.shape[1], y), (0, 255, 0), 1)
            cv2.putText(f, f"{j * 10}", (2, y - 2), 0, 0.35, (0, 255, 0), 1)
        cv2.putText(f, f"{t}s", (f.shape[1] - 60, 15), 0, 0.5, (0, 0, 255), 1)
        tiles.append(f)
    cv2.imwrite(a.ra, np.hstack(tiles))
    print(f"Đã lưu {a.ra} — mở ảnh xem: mặt từ đỉnh đầu tới cằm nằm ở % chiều cao nào; chữ nhấn đặt NGOÀI khoảng đó (ưu tiên phía trên đầu).")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("khoi"); p.add_argument("video"); p.add_argument("--tu", type=float); p.add_argument("--den", type=float)
    p = sub.add_parser("kiem-cat"); p.add_argument("video"); p.add_argument("edl")
    p = sub.add_parser("am-luong"); p.add_argument("video")
    p = sub.add_parser("luoi-mat"); p.add_argument("video"); p.add_argument("--giay", required=True)
    p.add_argument("--zoom", type=float, default=1.0); p.add_argument("--ra", default="luoi_mat.jpg")
    a = ap.parse_args()
    {"khoi": cmd_khoi, "kiem-cat": cmd_kiem_cat, "am-luong": cmd_am_luong, "luoi-mat": cmd_luoi_mat}[a.cmd](a)


if __name__ == "__main__":
    main()
