# -*- coding: utf-8 -*-
"""Skill JunOps — tạo danh sách đoạn cắt (edl.json) bằng cách BỎ KHOẢNG LẶNG, giữ phần có tiếng.

python tao_edl_bo_lang.py <file_loi.json từ chep_loi.py> [--ra edl.json] [--clip "<một phần tên file video>"]
                          [--lang-toi-thieu 0.45] [--dem 0.10]

Đây chỉ là điểm xuất phát. Việc chọn LẦN NÓI TỐT NHẤT của từng câu (bỏ lần nói vấp, nói hụt) là việc của Claude:
đọc file _loi.txt, rồi sửa edl.json (xoá/thêm/đổi giây) cho đúng ý bạn.

edl.json: [{"clip": "<tên file>", "a": giây bắt đầu trong video nguồn, "b": giây kết thúc, "loi": "ghi chú"}]
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
    ap.add_argument("--ra")
    ap.add_argument("--clip", default=None)
    ap.add_argument("--lang-toi-thieu", type=float, default=0.45, help="khoảng lặng dài hơn mức này (giây) thì cắt bỏ")
    ap.add_argument("--dem", type=float, default=0.10, help="giữ thêm bấy nhiêu giây ở đầu/cuối mỗi đoạn")
    a = ap.parse_args()

    d = json.loads(Path(a.loi).read_text(encoding="utf-8"))
    speech = d.get("speech") or []
    if not speech:
        sys.exit("File chép lời không có khoảng có tiếng (speech).")
    tong = d.get("dur", speech[-1][1])
    # gộp các khoảng có tiếng cách nhau ngắn hơn ngưỡng
    gop = [list(speech[0])]
    for s, e in speech[1:]:
        if s - gop[-1][1] < a.lang_toi_thieu:
            gop[-1][1] = e
        else:
            gop.append([s, e])
    edl = []
    for s, e in gop:
        a0, b0 = max(0.0, s - a.dem), min(tong, e + a.dem)
        edl.append({"clip": a.clip, "a": round(a0, 3), "b": round(b0, 3), "loi": ""})
    # đoạn kề nhau vì đệm chồng lên thì nối khít
    for i in range(1, len(edl)):
        if edl[i]["a"] < edl[i - 1]["b"]:
            edl[i]["a"] = edl[i - 1]["b"]
    out = Path(a.ra) if a.ra else Path(a.loi).with_name("edl.json")
    out.write_text(json.dumps(edl, ensure_ascii=False, indent=1), encoding="utf-8")
    giu = sum(x["b"] - x["a"] for x in edl)
    print(f"{len(edl)} đoạn, giữ {giu:.1f}s / {tong:.1f}s (bỏ {tong - giu:.1f}s im lặng) → {out}")


if __name__ == "__main__":
    main()
