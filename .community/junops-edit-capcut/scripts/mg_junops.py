# -*- coding: utf-8 -*-
"""Skill JunOps — MOTION GRAPHIC vẽ bằng code (4 mẫu có sẵn), đặt thẳng lên dòng thời gian CapCut.

4 mẫu:  tieu-de    thẻ tiêu đề lớn (+ dòng phụ)
        danh-sach  tiêu đề + 2-6 ý hiện lần lượt
        so-lieu    con số lớn đếm tăng dần (85%, 1.250.000, 3,5 tỷ…) + nhãn
        the-phan   thẻ phần/chương: «PHẦN 02» + tên phần

CHỈ VẼ, xem thử (không đụng CapCut):
  python mg_junops.py ve tieu-de --chu "3 CÁCH DÙNG CLAUDE" --phu "Dành cho người mới" --ra mg1.mp4 --anh-xem
  python mg_junops.py ve danh-sach --chu "Cần chuẩn bị" --muc "Máy tính|Tài khoản Claude|Video gốc" --ra mg2.mp4
  python mg_junops.py ve so-lieu --so "85%" --chu "KẾT QUẢ" --phu "người xem hài lòng" --ra mg3.mp4
  python mg_junops.py ve the-phan --so 2 --chu "Nối Claude với CapCut" --ra mg4.mp4
VẼ + ĐẶT VÀO CAPCUT (đóng CapCut trước; luôn backup):
  python mg_junops.py chen "<tên dự án>" --mg mg.json [--dry-run]
  python mg_junops.py mau-json      # in ra file mg.json mẫu để sửa

Tuỳ chọn chung: --dong ngang|doc (mặc định theo khung dự án) · --bang-mau toi-vang|toi-xanh|toi-xanh-la|toi-do|sang
  · --nen/--nhan/--chu-mau "#RRGGBB" tự chọn màu · --trong-suot (xuất .mov có nền trong suốt, phủ lên video) · --font <file .ttf>
Cần: Python 3.9+, pip install pillow numpy, và ffmpeg. Không kèm font/ảnh/âm thanh nào — dùng font có sẵn trong máy."""
import argparse
import copy
import json
import os
import re
import shutil
import subprocess
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

HERE = os.path.dirname(os.path.abspath(__file__))
FPS = 30
S = 1_000_000

BANG_MAU = {
    "toi-vang": dict(bg0=(26, 26, 32), bg1=(8, 8, 11), chu=(255, 255, 255), phu=(196, 196, 204), nhan=(255, 200, 40)),
    "toi-xanh": dict(bg0=(18, 30, 48), bg1=(6, 10, 18), chu=(255, 255, 255), phu=(178, 198, 218), nhan=(64, 196, 255)),
    "toi-do": dict(bg0=(34, 22, 24), bg1=(10, 7, 8), chu=(255, 255, 255), phu=(206, 190, 190), nhan=(255, 96, 84)),
    "toi-xanh-la": dict(bg0=(16, 32, 26), bg1=(6, 12, 10), chu=(255, 255, 255), phu=(176, 204, 192), nhan=(82, 214, 140)),
    "sang": dict(bg0=(252, 250, 245), bg1=(230, 226, 218), chu=(24, 24, 28), phu=(98, 98, 106), nhan=(232, 98, 44)),
}


# ---------------------------------------------------------------- tiện ích
def hex_rgb(s):
    s = s.lstrip("#")
    return tuple(int(s[i:i + 2], 16) for i in (0, 2, 4))


def smooth(u):
    u = min(1.0, max(0.0, u))
    return u * u * (3 - 2 * u)


def pop(u, k=1.5):
    """ra nhanh rồi nảy rất nhẹ"""
    u = min(1.0, max(0.0, u))
    return 1 + (k + 1) * (u - 1) ** 3 + k * (u - 1) ** 2


def tim_font(tuy_chon=None):
    ds = [tuy_chon, os.environ.get("JUNOPS_FONT"),
          r"C:\Windows\Fonts\segoeuib.ttf", r"C:\Windows\Fonts\arialbd.ttf", r"C:\Windows\Fonts\tahomabd.ttf",
          "/System/Library/Fonts/Supplemental/Arial Bold.ttf", "/Library/Fonts/Arial Bold.ttf",
          "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"]
    for p in ds:
        if p and os.path.isfile(p):
            return p
    sys.exit("Không tìm thấy font nào trong máy. Chỉ rõ 1 file font tiếng Việt bằng --font \"<đường dẫn .ttf>\".")


def tim_ffmpeg():
    p = shutil.which("ffmpeg")
    if not p:
        sys.exit("Chưa có ffmpeg. Cài: winget install Gyan.FFmpeg  (rồi mở lại cửa sổ dòng lệnh).")
    return p


def lines_fit(text, fpath, size, maxw, maxlines):
    while True:
        font = ImageFont.truetype(fpath, max(12, int(size)))
        lines = []
        for para in str(text).split("\n"):
            cur = ""
            for w in para.split():
                t = (cur + " " + w).strip()
                if cur and font.getlength(t) > maxw:
                    lines.append(cur)
                    cur = w
                else:
                    cur = t
            lines.append(cur)
        if (len(lines) <= maxlines and all(font.getlength(l) <= maxw for l in lines)) or size <= 22:
            return font, lines
        size *= 0.93


def text_spr(text, size, color, fpath, maxw, maxlines=3, align="center", shadow=0.0, gian=1.18):
    font, lines = lines_fit(text, fpath, size, maxw, maxlines)
    lh = int(font.size * gian)
    pad = int(font.size * 0.3)
    wmax = int(max(font.getlength(l) for l in lines)) if lines else 10
    w, h = wmax + pad * 2, lh * len(lines) + pad * 2
    lay = Image.new("RGBA", (w, h), color + (0,))
    dr = ImageDraw.Draw(lay)
    for i, l in enumerate(lines):
        lw = font.getlength(l)
        x = pad if align == "left" else (w - lw) / 2
        dr.text((x, pad + i * lh), l, font=font, fill=color + (255,))
    if shadow > 0:
        al = lay.split()[3].filter(ImageFilter.GaussianBlur(font.size * 0.12))
        sh = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        sh.putalpha(al.point(lambda v: int(v * shadow)))
        out = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        out.alpha_composite(sh, (0, int(font.size * 0.06)))
        out.alpha_composite(lay)
        out.pad_ = pad
        return out
    lay.pad_ = pad
    return lay


def vh(spr):
    """chiều cao nhìn thấy (bỏ viền trống quanh chữ)"""
    return spr.height - 2 * getattr(spr, "pad_", 0)


def disc_spr(d, color, ss=3):
    im = Image.new("RGBA", (d * ss, d * ss), color + (0,))
    ImageDraw.Draw(im).ellipse([0, 0, d * ss - 1, d * ss - 1], fill=color + (255,))
    return im.resize((d, d), Image.LANCZOS)


def rrect_spr(w, h, color, r=None, ss=3):
    r = r if r is not None else h // 2
    im = Image.new("RGBA", (w * ss, h * ss), color + (0,))
    ImageDraw.Draw(im).rounded_rectangle([0, 0, w * ss - 1, h * ss - 1], r * ss, fill=color + (255,))
    return im.resize((w, h), Image.LANCZOS)


def glow_spr(color, r):
    y, x = np.mgrid[-r:r + 1, -r:r + 1].astype(np.float32)
    a = np.clip(1 - np.sqrt(x * x + y * y) / r, 0, 1) ** 2
    arr = np.zeros((2 * r + 1, 2 * r + 1, 4), np.uint8)
    arr[..., :3] = color
    arr[..., 3] = (a * 255).astype(np.uint8)
    return Image.fromarray(arr, "RGBA")


class Canvas:
    """Bề mặt vẽ RGBA nhân trước alpha (float32)."""

    def __init__(self, W, H, bg=None):
        self.W, self.H = W, H
        self.a = np.zeros((H, W, 4), np.float32)
        if bg is not None:
            self.a[..., :3] = bg
            self.a[..., 3] = 1.0

    def paste(self, spr, cx, cy, a=1.0, sc=1.0):
        if a <= 0.003:
            return
        im = spr
        if abs(sc - 1.0) > 1e-3:
            im = im.resize((max(1, int(im.width * sc)), max(1, int(im.height * sc))), Image.LANCZOS)
        w, h = im.size
        x0, y0 = int(round(cx - w / 2)), int(round(cy - h / 2))
        gx0, gy0, gx1, gy1 = max(0, x0), max(0, y0), min(self.W, x0 + w), min(self.H, y0 + h)
        if gx1 <= gx0 or gy1 <= gy0:
            return
        src = np.asarray(im, dtype=np.float32)[gy0 - y0:gy1 - y0, gx0 - x0:gx1 - x0] / 255.0
        sa = src[..., 3:4] * a
        dst = self.a[gy0:gy1, gx0:gx1]
        dst[...] = np.concatenate([src[..., :3] * sa, sa], -1) + dst * (1 - sa)

    def rect(self, x0, y0, x1, y1, color, a=1.0):
        x0, y0, x1, y1 = int(max(0, x0)), int(max(0, y0)), int(min(self.W, x1)), int(min(self.H, y1))
        if x1 <= x0 or y1 <= y0 or a <= 0.003:
            return
        c = np.array(list(color) + [255], np.float32) / 255.0 * a
        dst = self.a[y0:y1, x0:x1]
        dst[...] = c + dst * (1 - a)

    def bytes_rgb(self):
        return (np.clip(self.a[..., :3], 0, 1) * 255 + 0.5).astype(np.uint8).tobytes()

    def bytes_rgba(self):
        al = self.a[..., 3:4]
        rgb = np.where(al > 1e-4, self.a[..., :3] / np.maximum(al, 1e-4), 0)
        return (np.clip(np.concatenate([rgb, al], -1), 0, 1) * 255 + 0.5).astype(np.uint8).tobytes()


def nen_gradient(W, H, c0, c1):
    t = np.linspace(0, 1, H, dtype=np.float32)[:, None, None]
    g = np.array(c0, np.float32) * (1 - t) + np.array(c1, np.float32) * t
    y, x = np.mgrid[0:H, 0:W].astype(np.float32)
    v = 1 - 0.28 * np.clip(np.sqrt(((x - W / 2) / (W / 2)) ** 2 + ((y - H / 2) / (H / 2)) ** 2) - 0.35, 0, 1)
    return np.broadcast_to(g, (H, W, 3)) * v[..., None] / 255.0


# ---------------------------------------------------------------- số liệu
def parse_so(s):
    m = re.search(r"\d[\d.,]*\d|\d", s)
    if not m:
        return None
    pre, num, suf = s[:m.start()], m.group(), s[m.end():]
    dec, ths = 0, ""
    if "," in num and "." in num:
        last = max(num.rfind(","), num.rfind("."))
        ds = num[last]
        ths = "," if ds == "." else "."
        dec = len(num) - last - 1
        val = float(num.replace(ths, "").replace(ds, "."))
    elif "," in num or "." in num:
        sep = "," if "," in num else "."
        parts = num.split(sep)
        if len(parts) > 2 or (len(parts[1]) == 3 and parts[0] not in ("0", "00")):
            ths = sep
            val = float(num.replace(sep, ""))
        else:
            dec = len(parts[1])
            val = float(num.replace(sep, "."))
            return pre, suf, val, dec, "", sep
    else:
        val = float(num)
    return pre, suf, val, dec, ths, ("," if ths == "." else ".")


def fmt_so(p, v):
    pre, suf, _, dec, ths, ds = p
    s = f"{v:,.{dec}f}" if dec else f"{int(round(v)):,}"
    s = s.replace(",", "\0").replace(".", ds if dec else ".").replace("\0", ths or "")
    return pre + s + suf


# ---------------------------------------------------------------- HÌNH (MG BẮT BUỘC có 1–2 hình, không chỉ chữ)
ICONS = ("tia-sang", "thu-muc", "dong-thoi-gian", "video", "chat", "tick", "mui-ten-len")
ICON_MAC_DINH = {"tieu-de": ["tia-sang"], "danh-sach": ["tick"], "so-lieu": ["mui-ten-len"], "the-phan": ["tia-sang", "dong-thoi-gian"]}


def _mix(c, k):
    return tuple(int(v * k) for v in c)


def ve_icon(name, h, P, k=1.0):
    """hình vẽ bằng code (RGBA). k = tiến độ 0..1 cho hình có chuyển động (dong-thoi-gian)."""
    ss = 3
    nh, ph = P["nhan"], P["phu"]
    w = int(h * 1.7) if name == "dong-thoi-gian" else (int(h * 1.3) if name == "video" else h)
    im = Image.new("RGBA", (w * ss, h * ss), (0, 0, 0, 0))
    dr = ImageDraw.Draw(im)
    W, H = w * ss, h * ss

    def rr(x0, y0, x1, y1, r, fill, outline=None, wd=0):
        dr.rounded_rectangle([x0 * W, y0 * H, x1 * W, y1 * H], r * H, fill=fill + (255,) if fill else None,
                             outline=outline + (255,) if outline else None, width=int(wd * ss))

    if name == "tia-sang":
        def star(cx_, cy_, R, fill):
            pts = []
            for i in range(8):
                r = R if i % 2 == 0 else R * 0.16
                a = np.pi * i / 4 - np.pi / 2
                pts.append(((cx_ + r * np.cos(a)) * W, (cy_ + r * np.sin(a)) * H))
            dr.polygon(pts, fill=fill + (255,))
        star(0.5, 0.52, 0.44, nh)
        star(0.84, 0.18, 0.13, P["chu"])
        star(0.17, 0.84, 0.10, P["chu"])
    elif name == "thu-muc":
        rr(0.05, 0.20, 0.95, 0.88, 0.07, _mix(nh, 0.7))
        rr(0.05, 0.12, 0.42, 0.32, 0.05, _mix(nh, 0.7))
        rr(0.05, 0.32, 0.95, 0.90, 0.07, nh)
        rr(0.14, 0.50, 0.60, 0.56, 0.02, P["bg1"])
        rr(0.14, 0.64, 0.46, 0.70, 0.02, P["bg1"])
    elif name == "dong-thoi-gian":
        rr(0.0, 0.10, 1.0, 0.90, 0.07, (34, 34, 42), ph, 3)
        for i in range(12):                                  # thước chia
            x = 0.05 + 0.9 * i / 11
            dr.line([x * W, 0.17 * H, x * W, (0.22 if i % 3 else 0.26) * H], fill=ph + (255,), width=ss * 2)
        blocks = [(0.05, 0.33, 0.30, nh), (0.37, 0.64, 0.30, nh), (0.68, 0.95, 0.30, nh),
                  (0.05, 0.22, 0.56, P["chu"]), (0.26, 0.58, 0.56, P["chu"]), (0.62, 0.95, 0.56, P["chu"])]
        for j, (x0, x1, y0, col) in enumerate(blocks):
            v = min(1.0, max(0.0, k * 7.5 - j))
            if v > 0.01:
                rr(x0, y0, x0 + (x1 - x0) * v, y0 + 0.2, 0.05, col)
        px = 0.05 + 0.9 * min(1.0, k)
        dr.line([px * W, 0.24 * H, px * W, 0.86 * H], fill=(255, 255, 255, 255), width=ss * 4)
        dr.polygon([((px - 0.025) * W, 0.20 * H), ((px + 0.025) * W, 0.20 * H), (px * W, 0.27 * H)], fill=(255, 255, 255, 255))
    elif name == "video":
        rr(0.03, 0.12, 0.97, 0.88, 0.10, (34, 34, 42), P["chu"], 5)
        dr.polygon([(0.42 * W, 0.32 * H), (0.42 * W, 0.68 * H), (0.62 * W, 0.50 * H)], fill=nh + (255,))
    elif name == "chat":
        rr(0.04, 0.10, 0.96, 0.72, 0.14, nh)
        dr.polygon([(0.22 * W, 0.70 * H), (0.22 * W, 0.92 * H), (0.46 * W, 0.70 * H)], fill=nh + (255,))
        for cxp in (0.32, 0.5, 0.68):
            dr.ellipse([(cxp - 0.05) * W, 0.36 * H, (cxp + 0.05) * W, 0.46 * H], fill=P["bg1"] + (255,))
    elif name == "tick":
        dr.ellipse([0.04 * W, 0.04 * H, 0.96 * W, 0.96 * H], fill=nh + (255,))
        dr.line([(0.28 * W, 0.52 * H), (0.44 * W, 0.68 * H), (0.74 * W, 0.34 * H)], fill=P["bg1"] + (255,),
                width=int(0.11 * H), joint="curve")
    elif name == "mui-ten-len":
        dr.polygon([(0.5 * W, 0.06 * H), (0.92 * W, 0.50 * H), (0.64 * W, 0.50 * H), (0.64 * W, 0.94 * H),
                    (0.36 * W, 0.94 * H), (0.36 * W, 0.50 * H), (0.08 * W, 0.50 * H)], fill=nh + (255,))
    elif name == "mui-ten":                                   # mũi tên phải nối 2 hình
        dr.polygon([(0.02 * W, 0.40 * H), (0.62 * W, 0.40 * H), (0.62 * W, 0.14 * H), (0.98 * W, 0.50 * H),
                    (0.62 * W, 0.86 * H), (0.62 * W, 0.60 * H), (0.02 * W, 0.60 * H)], fill=P["chu"] + (255,))
    return im.resize((w, h), Image.LANCZOS)


def anh_tu_file(path, hs, maxw):
    im = Image.open(path).convert("RGBA")
    k = min(hs * 1.25 / im.height, maxw / im.width)
    im = im.resize((max(1, int(im.width * k)), max(1, int(im.height * k))), Image.LANCZOS)
    m = Image.new("L", im.size, 0)
    ImageDraw.Draw(m).rounded_rectangle([0, 0, im.width - 1, im.height - 1], int(min(im.size) * 0.08), fill=255)
    im.putalpha(Image.fromarray((np.asarray(im.split()[3], np.float32) * np.asarray(m, np.float32) / 255).astype(np.uint8)))
    return im


def lop_hinh(cx, it, dur):
    """vẽ 1–2 hình phía trên khối chữ: tên hình có sẵn (ICONS) hoặc đường dẫn file ảnh (ảnh chụp màn hình, logo, ảnh lấy từ web)."""
    u, W, H, P = cx.u, cx.W, cx.H, cx.P
    ds = [str(x) for x in (it.get("anh") or [])][:2]
    if not ds:
        ds = ICON_MAC_DINH[it["loai"]]
        print(f"    ⚠ MG này chưa khai báo 'anh' — tạm dùng hình vẽ mặc định {ds}. Hãy chọn hình ĐÚNG nội dung (xem ICONS) "
              f"hoặc đưa file ảnh thật (ảnh chụp màn hình, logo, sản phẩm).")
    hs = int(min(0.14 * H, 290 * u))
    cy = H * 0.27
    xs = [W / 2] if len(ds) == 1 else [W * 0.25, W * 0.74]
    maxw = W * (0.5 if len(ds) == 1 else 0.36)
    thanh = []
    for d in ds:
        if d in ICONS:
            thanh.append(("icon", d))
        elif os.path.isfile(d):
            thanh.append(("file", anh_tu_file(d, hs, maxw)))
        else:
            sys.exit(f"Hình '{d}' không phải tên hình có sẵn {list(ICONS)} cũng không phải file ảnh tồn tại.")
    cache = {}
    mui = ve_icon("mui-ten", int(hs * 0.42), P) if len(ds) == 2 else None

    def draw(cv, t):
        out = 1 - smooth((t - (dur - 0.35)) / 0.35)
        for i, (loai, v) in enumerate(thanh):
            t0 = 0.2 + 0.35 * i
            e = smooth((t - t0) / 0.45)
            if loai == "icon":
                kk = round(smooth((t - t0) / 1.3) * 24) / 24 if v == "dong-thoi-gian" else 1.0
                key = (v, kk)
                if key not in cache:
                    cache[key] = ve_icon(v, hs, P, kk)
                spr = cache[key]
            else:
                spr = v
            cv.paste(spr, xs[i], cy + 30 * u * (1 - e), e * out, 0.82 + 0.18 * pop((t - t0) / 0.5))
        if mui is not None:
            e = smooth((t - 0.5) / 0.4)
            cv.paste(mui, W * 0.495 + 18 * u * (e - 1), cy, e * out)
    return draw


# ---------------------------------------------------------------- 4 mẫu
class Ctx:
    def __init__(self, W, H, P, fpath):
        self.W, self.H, self.P, self.f = W, H, P, fpath
        self.u = min(W, H) / 1080.0
        self.dy = 0.0                                   # đẩy khối chữ xuống để chừa chỗ cho hình
        self.glow = glow_spr(P["nhan"], int(520 * self.u))


def nen(cv, cx, t, dur):
    """hai quầng sáng màu nhấn trôi chậm sau lưng chữ"""
    W, H, u = cx.W, cx.H, cx.u
    k = 0.5 + 0.5 * min(1.0, t / 0.8)
    cv.paste(cx.glow, W * (0.25 + 0.04 * np.sin(t * 0.9)), H * (0.22 + 0.03 * np.cos(t * 0.7)), 0.20 * k)
    cv.paste(cx.glow, W * (0.78 + 0.04 * np.cos(t * 0.8)), H * (0.80 + 0.03 * np.sin(t * 0.6)), 0.14 * k)


def mau_tieu_de(cx, it, dur):
    u, W, H, P = cx.u, cx.W, cx.H, cx.P
    chu = text_spr(it.get("chu", ""), 124 * u, P["chu"], cx.f, W * 0.84, 4, shadow=0.5)
    phu = text_spr(it["phu"], 50 * u, P["phu"], cx.f, W * 0.78, 3) if it.get("phu") else None
    bar_h = max(6, int(9 * u))
    gap = 34 * u
    tot = vh(chu) + gap + bar_h + ((gap + vh(phu)) if phu else 0)
    y0 = H / 2 - tot / 2 + cx.dy

    def draw(cv, t):
        out = 1 - smooth((t - (dur - 0.35)) / 0.35)
        e = smooth(t / 0.55)
        cv.paste(chu, W / 2, y0 + vh(chu) / 2 + 46 * u * (1 - e), e * out, 0.94 + 0.06 * e)
        yb = y0 + vh(chu) + gap
        bw = 0.2 * W * smooth((t - 0.3) / 0.55)
        cv.rect(W / 2 - bw / 2, yb, W / 2 + bw / 2, yb + bar_h, P["nhan"], out)
        if phu:
            e2 = smooth((t - 0.55) / 0.5)
            cv.paste(phu, W / 2, yb + bar_h + gap + vh(phu) / 2 + 24 * u * (1 - e2), e2 * out)
    return draw


def mau_danh_sach(cx, it, dur):
    u, W, H, P = cx.u, cx.W, cx.H, cx.P
    muc = [m for m in it.get("muc", []) if str(m).strip()][:6]
    tieu = text_spr(it["chu"], 66 * u, P["nhan"], cx.f, W * 0.84, 2, align="left") if it.get("chu") else None
    bd = int(92 * u)
    gx = 28 * u
    tw = W * 0.84 - bd - gx
    badges = [(disc_spr(bd, P["nhan"]),
               text_spr(str(i + 1), 52 * u, P["bg1"] if P is not BANG_MAU["sang"] else (255, 255, 255), cx.f, bd, 1))
              for i in range(len(muc))]
    txts = [text_spr(m, 62 * u, P["chu"], cx.f, tw, 2, align="left", shadow=0.4) for m in muc]
    rows = [max(bd, vh(t)) for t in txts]
    gap = 40 * u
    tot = (vh(tieu) + 36 * u if tieu else 0) + sum(rows) + gap * max(0, len(rows) - 1)
    ytop = H / 2 - tot / 2 + cx.dy
    xl = W * 0.08

    def draw(cv, t):
        out = 1 - smooth((t - (dur - 0.35)) / 0.35)
        y = ytop
        if tieu:
            e = smooth(t / 0.5)
            cv.paste(tieu, xl + tieu.width / 2 - tieu.pad_ - 60 * u * (1 - e), y + vh(tieu) / 2, e * out)
            y += vh(tieu) + 36 * u
        for i, (bs, ns) in enumerate(badges):
            t0 = 0.55 + 0.45 * i
            e = smooth((t - t0) / 0.5)
            cy = y + rows[i] / 2
            dx = -70 * u * (1 - e)
            cv.paste(bs, xl + bd / 2 + dx, cy, e * out, 0.85 + 0.15 * pop((t - t0) / 0.5))
            cv.paste(ns, xl + bd / 2 + dx, cy, e * out)
            cv.paste(txts[i], xl + bd + gx + txts[i].width / 2 - txts[i].pad_ + dx, cy, e * out)
            y += rows[i] + gap
    return draw


def mau_so_lieu(cx, it, dur):
    u, W, H, P = cx.u, cx.W, cx.H, cx.P
    goc = it.get("so", "0")
    p = parse_so(str(goc))
    kicker = text_spr(it["chu"].upper(), 50 * u, P["nhan"], cx.f, W * 0.8, 2) if it.get("chu") else None
    nhan = text_spr(it["phu"], 62 * u, P["phu"], cx.f, W * 0.8, 3) if it.get("phu") else None
    cuoi = text_spr(str(goc), 300 * u, P["chu"], cx.f, W * 0.88, 1, shadow=0.5)
    gap = 34 * u
    bar_h = max(6, int(9 * u))
    tot = (vh(kicker) + gap * 0.5 if kicker else 0) + vh(cuoi) + gap + bar_h + ((gap + vh(nhan)) if nhan else 0)
    y0 = H / 2 - tot / 2 + cx.dy
    cache = {}

    def draw(cv, t):
        out = 1 - smooth((t - (dur - 0.35)) / 0.35)
        y = y0
        if kicker:
            e = smooth(t / 0.45)
            cv.paste(kicker, W / 2, y + vh(kicker) / 2 + 20 * u * (1 - e), e * out)
            y += vh(kicker) + gap * 0.5
        e = smooth(t / 0.4)
        if p:
            k = 1 - (1 - smooth((t - 0.15) / 1.3)) ** 3
            s = fmt_so(p, p[2] * k)
            if s not in cache:
                cache[s] = text_spr(s, 300 * u, P["chu"], cx.f, W * 0.88, 1, shadow=0.5)
            sp = cache[s]
            if sp.width < cuoi.width:                       # giữ số căn giữa, không nhảy khi đếm
                bg = Image.new("RGBA", cuoi.size, (0, 0, 0, 0))
                bg.alpha_composite(sp, ((cuoi.width - sp.width) // 2, (cuoi.height - sp.height) // 2))
                sp = bg
        else:
            sp = cuoi
        cv.paste(sp, W / 2, y + vh(cuoi) / 2 + 30 * u * (1 - e), e * out, 0.95 + 0.05 * e)
        y += vh(cuoi) + gap
        bw = 0.22 * W * smooth((t - 0.9) / 0.5)
        cv.rect(W / 2 - bw / 2, y, W / 2 + bw / 2, y + bar_h, P["nhan"], out)
        if nhan:
            e2 = smooth((t - 1.1) / 0.5)
            cv.paste(nhan, W / 2, y + bar_h + gap + vh(nhan) / 2 + 20 * u * (1 - e2), e2 * out)
    return draw


def mau_the_phan(cx, it, dur):
    u, W, H, P = cx.u, cx.W, cx.H, cx.P
    so = str(it.get("so", "1")).strip()
    so = so.zfill(2) if so.isdigit() else so
    lab = text_spr(it.get("nhan", "PHẦN"), 46 * u, P["phu"], cx.f, W * 0.6, 1)
    num = text_spr(so, 300 * u, P["nhan"], cx.f, W * 0.8, 1, shadow=0.4)
    ten = text_spr(it.get("chu", ""), 96 * u, P["chu"], cx.f, W * 0.84, 3, shadow=0.5)
    phu = text_spr(it["phu"], 46 * u, P["phu"], cx.f, W * 0.78, 2) if it.get("phu") else None
    gap = 26 * u
    bar_h = max(5, int(7 * u))
    tot = vh(lab) + vh(num) + gap + bar_h + gap + vh(ten) + ((gap * 0.6 + vh(phu)) if phu else 0)
    y0 = H / 2 - tot / 2 + cx.dy

    def draw(cv, t):
        out = 1 - smooth((t - (dur - 0.3)) / 0.3)
        y = y0
        e = smooth(t / 0.4)
        cv.paste(lab, W / 2, y + vh(lab) / 2 + 16 * u * (1 - e), e * out)
        y += vh(lab)
        e = smooth((t - 0.08) / 0.5)
        cv.paste(num, W / 2, y + vh(num) / 2 + 50 * u * (1 - e), e * out, 0.9 + 0.1 * pop((t - 0.08) / 0.55))
        y += vh(num) + gap
        bw = 0.34 * W * smooth((t - 0.3) / 0.5)
        cv.rect(W / 2 - bw / 2, y, W / 2 + bw / 2, y + bar_h, P["chu"], out)
        y += bar_h + gap
        e = smooth((t - 0.45) / 0.5)
        cv.paste(ten, W / 2, y + vh(ten) / 2 + 30 * u * (1 - e), e * out)
        if phu:
            y += vh(ten) + gap * 0.6
            e = smooth((t - 0.7) / 0.5)
            cv.paste(phu, W / 2, y + vh(phu) / 2 + 16 * u * (1 - e), e * out)
    return draw


MAU = {"tieu-de": mau_tieu_de, "danh-sach": mau_danh_sach, "so-lieu": mau_so_lieu, "the-phan": mau_the_phan}


def thoi_luong_mac_dinh(it):
    loai = it["loai"]
    if loai == "danh-sach":
        return 1.6 + 0.45 * len([m for m in it.get("muc", []) if str(m).strip()]) + 1.6
    return {"tieu-de": 3.0, "so-lieu": 3.6, "the-phan": 2.6}[loai]


# ---------------------------------------------------------------- vẽ ra file
def render(it, out, W, H, P, fpath, trong_suot=False, anh_xem=None):
    ff = tim_ffmpeg()
    dur = float(it.get("dur") or thoi_luong_mac_dinh(it))
    cx = Ctx(W, H, P, fpath)
    cx.dy = 0.075 * H
    draw = MAU[it["loai"]](cx, it, dur)
    draw_hinh = lop_hinh(cx, it, dur)
    bg = None if trong_suot else nen_gradient(W, H, P["bg0"], P["bg1"])
    n = int(round(dur * FPS))
    if trong_suot:
        out = os.path.splitext(out)[0] + ".mov"
        enc = ["-c:v", "prores_ks", "-profile:v", "4", "-pix_fmt", "yuva444p10le", "-c:a", "pcm_s16le"]
        pin = "rgba"
    else:
        enc = ["-c:v", "libx264", "-preset", "fast", "-crf", "16", "-pix_fmt", "yuv420p", "-c:a", "aac", "-movflags", "+faststart"]
        pin = "rgb24"
    cmd = [ff, "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", pin, "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
           "-f", "lavfi", "-i", "anullsrc=r=48000:cl=stereo", "-t", f"{dur:.3f}"] + enc + [out]   # kèm âm thanh im lặng để CapCut nhận đủ
    os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
    pr = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    mocs = {int(n * f) for f in (0.3, 0.55, 0.85)}
    xem = []
    for i in range(n):
        t = i / FPS
        cv = Canvas(W, H, bg)
        if not trong_suot:
            nen(cv, cx, t, dur)
        draw(cv, t)
        draw_hinh(cv, t)
        pr.stdin.write(cv.bytes_rgba() if trong_suot else cv.bytes_rgb())
        if anh_xem and i in mocs:
            xem.append(Image.frombytes("RGB", (W, H), cv.bytes_rgb()) if not trong_suot else
                       Image.frombytes("RGBA", (W, H), cv.bytes_rgba()).convert("RGB"))
    pr.stdin.close()
    if pr.wait() != 0:
        sys.exit("ffmpeg báo lỗi khi xuất video (xem dòng lỗi phía trên).")
    if anh_xem and xem:
        k = 520 / max(W, H)
        tw, th = int(W * k), int(H * k)
        sheet = Image.new("RGB", (tw * len(xem) + 8 * (len(xem) - 1), th), (60, 60, 60))
        for j, im in enumerate(xem):
            sheet.paste(im.resize((tw, th), Image.LANCZOS), (j * (tw + 8), 0))
        sheet.save(anh_xem, quality=90)
    return out, dur


def bang_mau(a):
    P = dict(BANG_MAU[getattr(a, "bang_mau", None) or "toi-vang"])
    if getattr(a, "nen", None):
        P["bg0"] = P["bg1"] = hex_rgb(a.nen)
    if getattr(a, "nhan", None):
        P["nhan"] = hex_rgb(a.nhan)
    if getattr(a, "chu_mau", None):
        P["chu"] = hex_rgb(a.chu_mau)
    return P


def kich_thuoc(dong, rong=None, cao=None):
    if rong and cao:
        return int(rong) // 2 * 2, int(cao) // 2 * 2
    return (1920, 1080) if dong == "ngang" else (1080, 1920)


def cmd_ve(a):
    it = dict(loai=a.loai, chu=a.chu or "", phu=a.phu or "", so=a.so or "", muc=[x.strip() for x in (a.muc or "").split("|")],
              dur=a.dur, nhan=a.nhan_phan, anh=[x.strip() for x in (a.anh or "").split("|") if x.strip()])
    W, H = kich_thuoc(a.dong or "doc")
    ra = a.ra or f"mg_{a.loai}.mp4"
    anh = os.path.splitext(ra)[0] + "_xem.jpg" if a.anh_xem else None
    out, dur = render(it, ra, W, H, bang_mau(a), tim_font(a.font), a.trong_suot, anh)
    print(f"Đã vẽ {out}  ({W}x{H}, {dur:.1f}s)" + (f" · ảnh xem thử: {anh}" if anh else ""))


# ---------------------------------------------------------------- đặt vào CapCut
KEEP_REFS = {"speeds", "canvases", "sound_channel_mappings", "placeholder_infos", "material_colors"}


def mau_video_tu_du_an(J, d):
    """Lấy khuôn đoạn video từ CHÍNH dự án của bạn (không dựa vào mẫu cài sẵn)."""
    idx = J.index(d)
    for t in d["tracks"]:
        if t["type"] != "video":
            continue
        for s in t["segments"]:
            k, m = idx.get(s["material_id"], (None, None))
            if k == "videos" and m.get("type") == "video":
                refs = [(idx[r][0], copy.deepcopy(idx[r][1])) for r in s.get("extra_material_refs", [])
                        if r in idx and idx[r][0] in KEEP_REFS]
                return dict(seg=copy.deepcopy(s), mat=copy.deepcopy(m), refs=refs)
    sys.exit("Dòng thời gian này chưa có đoạn video nào để làm khuôn. Kéo ít nhất 1 video vào dòng thời gian rồi chạy lại.")


def dat_vao_du_an(J, d, tpl, track_state, file_mg, at, dur, W, H):
    seg = copy.deepcopy(tpl["seg"])
    mat = copy.deepcopy(tpl["mat"])
    mat["id"] = J.new_id()
    base = os.path.basename(file_mg)
    mat.update(path=file_mg.replace("\\", "/"), material_name=base, duration=int(dur * S) + S // FPS, width=W, height=H,
               has_audio=True, local_material_id=J.new_id().lower(), category_name="local")
    va = mat.get("video_algorithm")
    if isinstance(va, dict):
        va.update(algorithms=[], quality_enhance=None, super_resolution=None, path="")
    d["materials"].setdefault("videos", []).append(mat)
    refs = []
    for rk, rm in tpl["refs"]:
        rm = copy.deepcopy(rm)
        rm["id"] = J.new_id()
        if rk == "speeds":
            rm.update(speed=1.0, mode=0)
        d["materials"].setdefault(rk, []).append(rm)
        refs.append(rm["id"])
    seg.update(id=J.new_id(), material_id=mat["id"], extra_material_refs=refs, common_keyframes=[], keyframe_refs=[],
               speed=1.0, volume=0.0, reverse=False, visible=True)
    seg["target_timerange"] = {"start": int(at * S), "duration": int(dur * S)}
    seg["source_timerange"] = {"start": 0, "duration": int(dur * S)}
    c = seg.get("clip")
    if c:
        c.update(alpha=1.0, rotation=0.0, scale={"x": 1.0, "y": 1.0}, flip={"horizontal": False, "vertical": False})
        c["transform"] = {"x": 0.0, "y": 0.0}
    seg["uniform_scale"] = {"on": True, "value": 1.0}
    # track riêng của MG, nằm TRÊN cùng; chồng nhau thì sang track mới
    for ti in track_state:
        tr = d["tracks"][ti]
        if all(s["target_timerange"]["start"] + s["target_timerange"]["duration"] <= seg["target_timerange"]["start"]
               or s["target_timerange"]["start"] >= seg["target_timerange"]["start"] + seg["target_timerange"]["duration"]
               for s in tr["segments"]):
            break
    else:
        d["tracks"].append({"id": J.new_id(), "type": "video", "flag": 2, "attribute": 0, "name": "MG JunOps",
                            "is_default_name": False, "segments": []})
        ti = len(d["tracks"]) - 1
        track_state.append(ti)
    rmax = max([s.get("render_index", 0) for t in d["tracks"] if t["type"] == "video" for s in t["segments"]] + [0])
    seg["render_index"] = rmax + 1
    d["tracks"][ti]["segments"].append(seg)
    d["tracks"][ti]["segments"].sort(key=lambda s: s["target_timerange"]["start"])
    return ti


def cmd_chen(a):
    sys.path.insert(0, HERE)
    import junops_capcut as J
    J.ROOT = J.tim_goc(a.root) if not a.draft_file else (a.root or "")
    path, pdir = J.resolve(a)
    J.kiem_tra_dong_capcut(a.dry_run, pdir)
    d = J.load(path)
    ds = json.load(open(a.mg, encoding="utf-8"))
    cc = d.get("canvas_config") or {}
    W, H = int(cc.get("width") or 1080) // 2 * 2, int(cc.get("height") or 1920) // 2 * 2
    if max(W, H) > 1920:
        k = 1920 / max(W, H)
        W, H = int(W * k) // 2 * 2, int(H * k) // 2 * 2
    P, fpath = bang_mau(a), tim_font(a.font)
    ten = os.path.basename(os.path.dirname(path)) if not pdir else os.path.basename(pdir)
    ra = a.ra or os.path.join(os.path.expanduser("~"), "Videos", "JunOps_MG", re.sub(r"[^\w\- ]", "_", ten))
    print(f"Khung dự án {W}x{H} · {len(ds)} motion graphic · lưu file tại {ra}")
    tpl = mau_video_tu_du_an(J, d)
    tracks = []
    for i, it in enumerate(ds):
        if it.get("loai") not in MAU:
            sys.exit(f"Mục {i + 1}: loai phải là một trong {list(MAU)}")
        if "at" not in it:
            sys.exit(f"Mục {i + 1}: thiếu 'at' (giây trên dòng thời gian).")
        dur = float(it.get("dur") or thoi_luong_mac_dinh(it))
        print(f"  {float(it['at']):7.2f}s +{dur:.1f}s  {it['loai']:<9}  {it.get('chu') or it.get('so', '')}")
        if (float(it["at"]) + dur) * S > d["duration"] > 0:
            print(f"    ⚠ MG này vượt quá độ dài dòng thời gian ({d['duration'] / S:.1f}s) — phần vượt sẽ không hiện, hãy đổi 'at'.")
        if a.dry_run:
            continue
        ts = bool(it.get("trong_suot", a.trong_suot))
        out, dur = render(it, os.path.join(ra, f"mg_{i + 1:02d}_{it['loai']}.mp4"), W, H, P, fpath, ts)
        dat_vao_du_an(J, d, tpl, tracks, out, float(it["at"]), dur, W, H)
    if a.dry_run:
        print("(dry-run) chưa vẽ, chưa ghi gì.")
        return
    for i, t in enumerate(d["tracks"]):
        for s in t["segments"]:
            s["track_render_index"] = i
    idx = J.index(d)
    thieu = sum(1 for t in d["tracks"] for s in t["segments"]
                if s["material_id"] not in idx or any(r not in idx for r in s.get("extra_material_refs", [])))
    if thieu:
        sys.exit(f"Còn {thieu} tham chiếu thiếu — KHÔNG ghi.")
    n, bdir = J.ghi_du_an(d, path, pdir, "motion_graphic")
    print(f"Đã ghi {n} file. Backup: {bdir}\nMở CapCut: các MG nằm ở track «MG JunOps» trên cùng — kéo, cắt, xoá thoải mái.")


MG_MAU = [
    {"at": 0.5, "loai": "tieu-de", "chu": "3 CÁCH DÙNG CLAUDE", "phu": "Dành cho người mới", "dur": 3, "anh": ["tia-sang"]},
    {"at": 12.0, "loai": "danh-sach", "chu": "Cần chuẩn bị", "muc": ["Máy tính cài CapCut", "Tài khoản Claude", "Video đã quay"], "anh": ["thu-muc"]},
    {"at": 25.0, "loai": "so-lieu", "so": "85%", "chu": "Kết quả", "phu": "người xem hài lòng"},
    {"at": 40.0, "loai": "the-phan", "so": 2, "chu": "Nối Claude với CapCut", "phu": "Chỉ một file", "anh": ["tia-sang", "dong-thoi-gian"]},
    {"at": 52.0, "loai": "tieu-de", "chu": "Phủ lên video", "trong_suot": True, "dur": 2.5},
]


def main():
    chung = argparse.ArgumentParser(add_help=False)
    chung.add_argument("--bang-mau", choices=list(BANG_MAU), default="toi-vang")
    chung.add_argument("--nen", help="màu nền #RRGGBB")
    chung.add_argument("--nhan", help="màu nhấn #RRGGBB")
    chung.add_argument("--chu-mau", help="màu chữ chính #RRGGBB")
    chung.add_argument("--font", help="file font .ttf hỗ trợ tiếng Việt (mặc định: font có sẵn trong máy)")
    chung.add_argument("--trong-suot", action="store_true", help="xuất .mov nền trong suốt để phủ lên video")
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("ve", parents=[chung])
    p.add_argument("loai", choices=list(MAU))
    p.add_argument("--chu")
    p.add_argument("--phu")
    p.add_argument("--so")
    p.add_argument("--muc", help="các ý cách nhau dấu |")
    p.add_argument("--dur", type=float)
    p.add_argument("--anh", help="1–2 hình cách nhau dấu |: tên hình có sẵn (tia-sang|thu-muc|dong-thoi-gian|video|chat|tick|mui-ten-len) hoặc đường dẫn file ảnh")
    p.add_argument("--nhan-phan", default="PHẦN", help="chữ nhỏ phía trên số của thẻ phần")
    p.add_argument("--dong", choices=["ngang", "doc"], default="doc")
    p.add_argument("--ra")
    p.add_argument("--anh-xem", action="store_true", help="lưu thêm 1 ảnh ghép 3 khung để xem thử")
    p = sub.add_parser("chen", parents=[chung])
    p.add_argument("project", nargs="?")
    p.add_argument("--mg", required=True, help="file json danh sách MG (xem lệnh mau-json)")
    p.add_argument("--ra", help="thư mục lưu các file MG (mặc định Videos/JunOps_MG/<dự án>)")
    p.add_argument("--root")
    p.add_argument("--timeline", default="01")
    p.add_argument("--draft-file")
    p.add_argument("--dry-run", action="store_true")
    sub.add_parser("mau-json")
    a = ap.parse_args()
    if a.cmd == "mau-json":
        print(json.dumps(MG_MAU, ensure_ascii=False, indent=2))
    elif a.cmd == "ve":
        cmd_ve(a)
    else:
        cmd_chen(a)


if __name__ == "__main__":
    main()
