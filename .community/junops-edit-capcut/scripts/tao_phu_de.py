# -*- coding: utf-8 -*-
"""Skill JunOps — tạo kế hoạch PHỤ ĐỀ tự động từ lời đã chép + bản đồ cắt.

python tao_phu_de.py <file_loi.json> <ban_do_cat.json> [--ra plan_phu_de.json] [--so-chu 4] [--file "<một phần tên video>"]

- Lấy từng chữ trong file_loi.json (do chep_loi.py tạo), giữ những chữ nằm trong các đoạn đã cắt,
  đổi giây "trong video thô" sang giây "trên dòng thời gian" bằng ban_do_cat.json (do lệnh 'cat' tạo).
- Gom tối đa --so-chu chữ mỗi dòng (mặc định 4), ngắt thêm ở dấu câu hoặc khi có quãng nghỉ.
- Ra plan_phu_de.json: danh sách thao tác 'chu' (mẫu phu_de) để đưa vào 'junops_capcut.py apply'.
Mốc chữ của máy chép lời chỉ gần đúng, nên Claude/bạn vẫn cần xem lại chữ sai chính tả và nhịp.
"""
import argparse
import json
import sys
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("loi")
    ap.add_argument("ban_do")
    ap.add_argument("--ra")
    ap.add_argument("--so-chu", type=int, default=4)
    ap.add_argument("--file", default=None)
    ap.add_argument("--nghi", type=float, default=0.6, help="quãng nghỉ (giây) thì ngắt dòng")
    ap.add_argument("--y", type=float, default=None, help="vị trí dọc của chữ (-1 đáy … 1 đỉnh), bỏ trống = theo mẫu")
    a = ap.parse_args()

    words = json.loads(Path(a.loi).read_text(encoding="utf-8"))["words"]
    bd = json.loads(Path(a.ban_do).read_text(encoding="utf-8"))
    if a.file:
        bd = [b for b in bd if a.file.lower() in (b.get("file") or "").lower()]
    if not bd:
        sys.exit("Bản đồ cắt trống (hoặc --file không khớp).")

    tl = []  # (giây trên dòng thời gian, kết thúc, chữ)
    for s, e, w, *_ in words:
        mid = (s + e) / 2
        for b in bd:
            n0, n1 = b["nguon"]
            if n0 <= mid < n1:
                off = b["dong_thoi_gian"][0] - n0
                tl.append((s + off, e + off, w))
                break
    tl.sort()
    nhom, cur = [], []
    for i, (s, e, w) in enumerate(tl):
        if cur and (len(cur) >= a.so_chu or s - cur[-1][1] > a.nghi or cur[-1][2][-1:] in ".?!"):
            nhom.append(cur)
            cur = []
        cur.append((s, e, w))
    if cur:
        nhom.append(cur)

    ops = []
    for i, g in enumerate(nhom):
        s = g[0][0]
        e = g[-1][1] + 0.15
        if i + 1 < len(nhom):
            e = min(e + 0.25, nhom[i + 1][0][0])  # nối liền với dòng sau
        e = max(e, s + 0.4)
        op = {"op": "chu", "mau": "phu_de", "start": round(s, 3), "dur": round(e - s, 3),
              "text": " ".join(w for _, _, w in g).strip(" ,;")}
        if a.y is not None:
            op["y"] = a.y
        ops.append(op)
    out = Path(a.ra) if a.ra else Path(a.loi).with_name("plan_phu_de.json")
    out.write_text(json.dumps({"ops": ops}, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"{len(ops)} dòng phụ đề (≤{a.so_chu} chữ) → {out}")


if __name__ == "__main__":
    main()
