# -*- coding: utf-8 -*-
"""Skill JunOps — đổi giây "trong video thô" sang giây "trên dòng thời gian" sau khi cắt.

python doi_moc.py <ban_do_cat.json> <giây thô> [<giây thô> ...] [--file "<một phần tên video>"]

Dùng khi muốn đặt chữ nhấn mạnh / SFX / zoom đúng chỗ người nói nhắc từ quan trọng:
tìm giây của từ đó trong file _loi.json, đổi sang giây dòng thời gian, rồi đưa vào plan.json.
Giây rơi vào đoạn đã bị cắt bỏ thì báo "đã bị cắt".
"""
import json
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass


def main():
    args = sys.argv[1:]
    if len(args) < 2:
        sys.exit(__doc__)
    loc = None
    if "--file" in args:
        i = args.index("--file")
        loc = args[i + 1].lower()
        del args[i:i + 2]
    bd = json.load(open(args[0], encoding="utf-8"))
    if loc:
        bd = [b for b in bd if loc in (b.get("file") or "").lower()]
    for t in map(float, args[1:]):
        for b in bd:
            n0, n1 = b["nguon"]
            if n0 <= t < n1:
                print(f"{t:8.2f}s (thô) → {b['dong_thoi_gian'][0] + t - n0:8.2f}s (dòng thời gian)")
                break
        else:
            print(f"{t:8.2f}s (thô) → đã bị cắt")


if __name__ == "__main__":
    main()
