# -*- coding: utf-8 -*-
"""Skill JunOps — bản YOUTUBE (video ngang dài). Dùng CHUNG công cụ cắt/ghi CapCut (junops_capcut.py) trong cùng thư mục.

Bản này chỉ thêm những việc riêng của video ngang dài (mọi thứ còn lại — chép lời, cắt ghép, SFX — dùng lệnh của junops_capcut.py):

  python youtube_junops.py phu-de-cau "<dự án>" --loi <file_loi.json> [--ban-do ban_do_cat.json]   phụ đề theo CÂU (chữ trắng)
  python youtube_junops.py zoom-noi    "<dự án>"                       xen kẽ phóng to/thu nhỏ ở các chỗ cắt cảnh
  python youtube_junops.py zoom-chu    "<dự án>" --diem 12.5,31.0      phóng to rồi trả về ở những chỗ nói quan trọng
  python youtube_junops.py chu-quan-trong "<dự án>" --chu chu.json --mat trai|giua|phai   chữ nhấn mạnh KHÔNG đè mặt
  python youtube_junops.py kiem        "<dự án>"                       kiểm tra tham chiếu thiếu / file mất / đoạn chồng nhau

Thêm --dry-run để xem trước, không ghi gì. Dùng chung: --root --timeline --draft-file --kho
An toàn: từ chối ghi khi CapCut đang mở · luôn backup vào <dự án>/_backup_junops/<giờ>_<việc>."""
import argparse
import copy
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import junops_capcut as J  # noqa: E402

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

S = J.S


def mo(a):
    J.ROOT = J.tim_goc(a.root) if not getattr(a, "draft_file", None) else (a.root or "")
    path, pdir = J.resolve(a)
    J.kiem_tra_dong_capcut(a.dry_run, pdir)
    return path, pdir, J.load(path)


def kiem_cb(d):
    idx = J.index(d)
    thieu = sum(1 for t in d["tracks"] for s in t["segments"]
                if s["material_id"] not in idx or any(r not in idx for r in s.get("extra_material_refs", [])))
    chong = 0
    for t in d["tracks"]:
        if t["type"] == "text":
            continue
        cuoi = 0
        for s in sorted(t["segments"], key=lambda s: s["target_timerange"]["start"]):
            if s["target_timerange"]["start"] < cuoi - 1000:
                chong += 1
            cuoi = s["target_timerange"]["start"] + s["target_timerange"]["duration"]
    return thieu, chong


def luu(d, path, pdir, a, nhan):
    for i, t in enumerate(d["tracks"]):
        for s in t["segments"]:
            s["track_render_index"] = i
    thieu, chong = kiem_cb(d)
    print(f"Kiểm tra: tham chiếu thiếu {thieu} · đoạn chồng nhau {chong}")
    if thieu:
        sys.exit("Còn tham chiếu thiếu — KHÔNG ghi.")
    if a.dry_run:
        print("(dry-run) chưa ghi gì.")
        return
    n, bdir = J.ghi_du_an(d, path, pdir, nhan)
    print(f"Đã ghi {n} file. Backup: {bdir}")


def video_chinh(d):
    vt = next((t for t in d["tracks"] if t["type"] == "video"), None)
    if not vt or not vt["segments"]:
        sys.exit("Dòng thời gian chưa có video chính.")
    return vt


# ================================================================ phu-de-cau
def tach_dai(tu, toi_da):
    """tu: [(bắt đầu, kết thúc, chữ)] → các nhóm ≤ toi_da ký tự; cắt gần giữa, ưu tiên sau dấu phẩy"""
    tong = sum(len(x[2]) + 1 for x in tu)
    if tong <= toi_da + 1 or len(tu) < 2:
        return [tu]
    best, bi, acc = None, 1, 0
    for i in range(1, len(tu)):
        acc += len(tu[i - 1][2]) + 1
        sc = abs(acc - (tong - acc)) - (14 if tu[i - 1][2].rstrip().endswith((",", ";", ":")) else 0)
        if best is None or sc < best:
            best, bi = sc, i
    return tach_dai(tu[:bi], toi_da) + tach_dai(tu[bi:], toi_da)


def cmd_phu_de_cau(a):
    path, pdir, d = mo(a)
    kho = J.doc_kho(a)
    words = json.load(open(a.loi, encoding="utf-8"))["words"]
    bd = json.load(open(a.ban_do, encoding="utf-8")) if a.ban_do else None
    tl = []
    for s, e, w, *_ in words:
        if bd is None:
            tl.append((s, e, w.strip()))
            continue
        mid = (s + e) / 2
        for b in bd:
            n0, n1 = b["nguon"]
            if n0 <= mid < n1:
                off = b["dong_thoi_gian"][0] - n0
                tl.append((s + off, e + off, w.strip()))
                break
    tl.sort()
    if not tl:
        sys.exit("Không có chữ nào nằm trong các đoạn đã giữ (kiểm tra --loi và --ban-do).")
    cau, cur = [], []
    for s, e, w in tl:
        if cur and (cur[-1][2].endswith((".", "?", "!", "…")) or s - cur[-1][1] > a.nghi):
            cau.append(cur)
            cur = []
        cur.append((s, e, w))
    if cur:
        cau.append(cur)
    nhom = []
    for c in cau:
        nhom += tach_dai(c, a.toi_da)
    tpl = copy.deepcopy(J.lay_mau(kho, a.mau, "chu"))
    if a.mau_chu == "trang":
        m = tpl["material"][1]
        c = json.loads(m["content"])
        for st in c["styles"]:
            st.setdefault("fill", {}).setdefault("content", {})["render_type"] = "solid"
            st["fill"]["content"]["solid"] = {"color": [1.0, 1.0, 1.0]}
        m["content"] = json.dumps(c, ensure_ascii=False)
        m["text_color"] = "#ffffff"
    n = 0
    for i, g in enumerate(nhom):
        s0 = g[0][0]
        e0 = g[-1][1] + 0.15
        if i + 1 < len(nhom) and nhom[i + 1][0][0] - e0 < 0.5:
            e0 = nhom[i + 1][0][0]                       # nối liền với câu sau
        e0 = max(e0, s0 + 0.5)
        text = " ".join(x[2] for x in g).strip(" ,;")
        J.add_from_template(d, tpl, s0, e0 - s0, text, None, a.y, None, None, None)
        n += 1
        if n <= 4:
            print(f"  {s0:7.2f}s +{e0 - s0:4.1f}s  {text}")
    dai = [len(" ".join(x[2] for x in g)) for g in nhom]
    print(f"{n} lần hiện phụ đề (mỗi lần 1 câu, tối đa {a.toi_da} ký tự; dài nhất {max(dai)}, trung bình {sum(dai) // len(dai)})")
    luu(d, path, pdir, a, "phu_de_cau")


# ================================================================ zoom-noi (phóng to / thu nhỏ xen kẽ ở chỗ cắt cảnh)
def cmd_zoom_noi(a):
    path, pdir, d = mo(a)
    vt = video_chinh(d)
    muc = [float(x) for x in a.muc.split(",")]
    if len(muc) < 2 or any(m < 1.0 or m > 1.6 for m in muc):
        sys.exit("--muc cần ít nhất 2 mức trong khoảng 1.0–1.6, ví dụ 1.0,1.12,1.0,1.22")
    segs = sorted(vt["segments"], key=lambda s: s["target_timerange"]["start"])
    n = 0
    for i, s in enumerate(segs):
        sc = muc[i % len(muc)]
        if sc == 1.0 and abs(s["clip"]["scale"]["x"] - 1.0) < 1e-6:
            continue
        s["clip"]["scale"] = {"x": sc, "y": sc}
        n += 1
    print(f"{len(segs)} đoạn video chính · đổi cỡ khung {n} đoạn theo vòng {muc} (hai đoạn kề nhau luôn khác cỡ)")
    luu(d, path, pdir, a, "zoom_noi")


# ================================================================ zoom-chu (nhấn vào chữ quan trọng, tính theo cỡ khung hiện tại)
def cmd_zoom_chu(a):
    path, pdir, d = mo(a)
    vt = video_chinh(d)
    log = []
    for at in [float(x) for x in a.diem.split(",") if x.strip()]:
        seg = next((s for s in vt["segments"] if J.seg_range(s)[0] <= at < J.seg_range(s)[1]), None)
        if seg is None:
            sys.exit(f"Không có đoạn video chính tại {at}s")
        base = seg["clip"]["scale"]["x"]
        dinh = min(base * a.muc, 1.5)
        pts = [[0, base], [a.vao, dinh], [round(a.vao + a.giu, 3), dinh], [round(a.vao + a.giu + a.ra, 3), base]]
        J.add_zoom(d, at, pts)
        log.append(f"  zoom @ {at}s : {base:.2f} → {dinh:.2f} → {base:.2f}")
    print("\n".join(log))
    luu(d, path, pdir, a, "zoom_chu")


# ================================================================ chu-quan-trong (chữ nhấn mạnh không đè mặt)
VI_TRI = {  # mặt nằm ở đâu → chữ đặt ở phía đối diện (x, y tính theo phần khung, y dương = lên trên)
    "trai": (0.42, 0.10),
    "phai": (-0.42, 0.10),
    "giua": (-0.55, 0.30),
}


def cmd_chu_quan_trong(a):
    path, pdir, d = mo(a)
    kho = J.doc_kho(a)
    ds = json.load(open(a.chu, encoding="utf-8"))
    x0, y0 = VI_TRI[a.mat]
    for k, it in enumerate(ds):
        x = it.get("x", x0 if a.mat != "giua" else (x0 if k % 2 == 0 else -x0))   # mặt ở giữa: đặt luân phiên trái/phải
        y = it.get("y", y0)
        dur = it.get("dur", 1.5)
        J.add_from_template(d, J.lay_mau(kho, a.mau, "chu"), it["at"], dur, it["text"], x, y, it.get("scale"), None, None)
        print(f"  {it['at']:7.2f}s +{dur:.1f}s  ({x:+.2f},{y:+.2f})  {it['text']!r}")
    print(f"{len(ds)} chữ quan trọng, mặt ở phía {a.mat} nên chữ đặt phía đối diện.")
    luu(d, path, pdir, a, "chu_quan_trong")


# ================================================================ kiem
def cmd_kiem(a):
    a.dry_run = True
    path, pdir, d = mo(a)
    print([(i, t["type"], len(t["segments"])) for i, t in enumerate(d["tracks"])])
    thieu, chong = kiem_cb(d)
    mat = sorted({os.path.basename(m.get("path") or "") for k in ("videos", "audios") for m in d["materials"].get(k, [])
                  if m.get("path") and not str(m["path"]).startswith("##") and not os.path.exists(m["path"])})
    print(f"tham chiếu thiếu: {thieu} · đoạn chồng nhau: {chong} · file media mất: {mat[:6]}")


def main():
    chung = argparse.ArgumentParser(add_help=False)
    chung.add_argument("--root")
    chung.add_argument("--kho", default=J.KHO_MAC_DINH)
    chung.add_argument("--timeline", default="01")
    chung.add_argument("--draft-file")
    chung.add_argument("--dry-run", action="store_true")
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    P = {}
    for ten in ("phu-de-cau", "zoom-noi", "zoom-chu", "chu-quan-trong", "kiem"):
        P[ten] = sub.add_parser(ten, parents=[chung])
        P[ten].add_argument("project", nargs="?")
    p = P["phu-de-cau"]
    p.add_argument("--loi", required=True)
    p.add_argument("--ban-do")
    p.add_argument("--toi-da", type=int, default=64)
    p.add_argument("--nghi", type=float, default=0.8, help="quãng nghỉ (giây) thì ngắt câu")
    p.add_argument("--mau", default="phu_de")
    p.add_argument("--mau-chu", choices=["trang", "giu"], default="trang")
    p.add_argument("--y", type=float, help="vị trí dọc của phụ đề, bỏ trống = theo mẫu")
    P["zoom-noi"].add_argument("--muc", default="1.0,1.12,1.0,1.22,1.0,1.16")
    p = P["zoom-chu"]
    p.add_argument("--diem", required=True, help="các giây trên dòng thời gian, cách nhau dấu phẩy")
    p.add_argument("--muc", type=float, default=1.12)
    p.add_argument("--vao", type=float, default=0.3)
    p.add_argument("--giu", type=float, default=1.0)
    p.add_argument("--ra", type=float, default=0.4)
    p = P["chu-quan-trong"]
    p.add_argument("--chu", required=True, help='file json: [{"at": 12.5, "dur": 1.5, "text": "TỪ QUAN TRỌNG"}]')
    p.add_argument("--mat", choices=["trai", "giua", "phai"], required=True, help="khuôn mặt nằm ở phía nào trong khung")
    p.add_argument("--mau", default="nhan_manh")
    a = ap.parse_args()
    {"phu-de-cau": cmd_phu_de_cau, "zoom-noi": cmd_zoom_noi, "zoom-chu": cmd_zoom_chu,
     "chu-quan-trong": cmd_chu_quan_trong, "kiem": cmd_kiem}[a.cmd](a)


if __name__ == "__main__":
    main()
