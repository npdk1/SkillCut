# -*- coding: utf-8 -*-
"""Skill JunOps — công cụ đọc/ghi dự án CapCut (bản máy tính, Windows).

Mọi thứ chữ / âm thanh / zoom đều lấy từ CHÍNH CapCut của bạn, không có sẵn font hay SFX nào kèm theo.

Lệnh:
  python junops_capcut.py list
  python junops_capcut.py analyze "<tên dự án>" [--timeline 01]
  python junops_capcut.py hoc                      # quét CapCut của bạn: kiểu chữ + SFX đang có
  python junops_capcut.py mau                      # xem danh sách đã quét
  python junops_capcut.py chon --phu-de t2 --nhan-manh t5
  python junops_capcut.py cat   "<tên dự án>" --edl edl.json [--dry-run]     # ghi các đoạn đã cắt
  python junops_capcut.py apply "<tên dự án>" --plan plan.json [--dry-run]   # chữ, SFX, zoom

Dùng chung: --root "<thư mục bản nháp CapCut>"  --kho "<file kho mẫu>"
An toàn: từ chối ghi khi CapCut đang mở · luôn backup vào <dự án>/_backup_junops/<giờ> ·
apply chỉ THÊM đoạn mới (không xoá, không sửa đoạn có sẵn, trừ thêm keyframe zoom).
"""
import argparse
import copy
import datetime
import json
import os
import shutil
import statistics
import subprocess
import sys
import uuid

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

S = 1_000_000
HERE = os.path.dirname(os.path.abspath(__file__))
KHO_MAC_DINH = os.path.normpath(os.path.join(HERE, "..", "du_lieu", "kho_mau.json"))
ROOT = None
REF_GIU = {"speeds", "placeholder_infos", "canvases", "sound_channel_mappings", "material_colors",
           "vocal_separations", "realtime_denoises"}
SKIP_REFS = {"speeds", "placeholder_infos", "sound_channel_mappings", "material_colors",
             "vocal_separations", "canvases", "beats"}


# ---------------------------------------------------------------- tìm dự án
def tim_goc(tuy_chon=None):
    ung_vien = [tuy_chon, os.environ.get("CAPCUT_DRAFTS"),
                os.path.expandvars(r"%LOCALAPPDATA%\CapCut\User Data\Projects\com.lveditor.draft")]
    for p in ung_vien:
        if p and os.path.isdir(p):
            return p
    sys.exit("Không tìm thấy thư mục bản nháp CapCut. Mở CapCut > Cài đặt để xem nơi lưu, rồi chạy lại kèm "
             "--root \"<thư mục>\" (hoặc đặt biến môi trường CAPCUT_DRAFTS).")


def timelines(project):
    pdir = os.path.join(ROOT, project)
    lay_path = os.path.join(pdir, "timeline_layout.json")
    if not os.path.isfile(lay_path):  # bản CapCut chỉ có 1 dòng thời gian
        return pdir, [{"no": "01", "id": "goc", "name": project, "path": os.path.join(pdir, "draft_content.json")}]
    lay = json.load(open(lay_path, encoding="utf-8"))
    out = []
    for dock in lay.get("dockItems", []):
        for i, (tid, name) in enumerate(zip(dock["timelineIds"], dock["timelineNames"])):
            out.append({"no": f"{i + 1:02d}", "id": tid, "name": name,
                        "path": os.path.join(pdir, "Timelines", tid, "draft_content.json")})
    return pdir, out


def resolve(args):
    """Trả về (đường dẫn draft_content.json của dòng thời gian, thư mục dự án hoặc None)."""
    if getattr(args, "draft_file", None):
        return args.draft_file, None
    if not args.project:
        sys.exit("Thiếu tên dự án. Chạy 'list' để xem các dự án.")
    pdir, tls = timelines(args.project)
    for t in tls:
        if args.timeline in (t["no"], t["id"], t["name"]):
            return t["path"], pdir
    sys.exit(f"Không thấy dòng thời gian {args.timeline!r}. Có: {[t['no'] for t in tls]}")


def load(path):
    return json.load(open(path, encoding="utf-8"))


def index(d):
    return {m["id"]: (k, m) for k, v in d["materials"].items() if isinstance(v, list)
            for m in v if isinstance(m, dict) and "id" in m}


def text_of(m):
    try:
        return json.loads(m["content"])["text"]
    except Exception:
        return ""


def seg_range(s):
    t = s["target_timerange"]
    return t["start"] / S, (t["start"] + t["duration"]) / S


def new_id():
    u = str(uuid.uuid4()).split("-")
    return "-".join([u[0].upper(), u[1].upper(), u[2], u[3].upper(), u[4].upper()])


def capcut_running():
    try:
        out = subprocess.run(["tasklist", "/FI", "IMAGENAME eq CapCut.exe"], capture_output=True, text=True).stdout
        return "capcut.exe" in out.lower()
    except Exception:
        return False


def kiem_tra_dong_capcut(dry, pdir):
    if pdir and not dry and capcut_running():
        sys.exit("CapCut đang mở. Hãy đóng hẳn CapCut (chờ vài chục giây) rồi chạy lại, nếu không CapCut sẽ ghi đè "
                 "lên phần vừa làm. Dùng --dry-run để xem trước.")


def ghi_du_an(d, path, pdir, nhan):
    stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    bdir = os.path.join(pdir or os.path.dirname(path), "_backup_junops", f"{stamp}_{nhan}")
    os.makedirs(bdir, exist_ok=True)
    targets = [path]
    if pdir:  # file gốc ở thư mục dự án phản chiếu dòng thời gian đang mở
        goc = os.path.join(pdir, "draft_content.json")
        if os.path.isfile(goc) and os.path.abspath(goc) != os.path.abspath(path):
            try:
                if load(goc).get("id") == d.get("id"):
                    targets.append(goc)
            except Exception:
                pass
    for t in targets:
        shutil.copy2(t, os.path.join(bdir, os.path.basename(os.path.dirname(t)) + "__" + os.path.basename(t)))
        with open(t, "w", encoding="utf-8") as f:
            json.dump(d, f, ensure_ascii=False, separators=(",", ":"))
    return len(targets), bdir


# ---------------------------------------------------------------- list / analyze
def cmd_list(a):
    for name in sorted(os.listdir(ROOT), key=lambda n: -os.path.getmtime(os.path.join(ROOT, n))):
        p = os.path.join(ROOT, name)
        if not os.path.isfile(os.path.join(p, "draft_content.json")):
            continue
        line = f"{name:24s} sửa lần cuối {datetime.datetime.fromtimestamp(os.path.getmtime(p)):%Y-%m-%d %H:%M}"
        try:
            _, tls = timelines(name)
            line += "  | dòng thời gian: " + ", ".join(f"{t['no']}={t['name'] or t['id'][:8]}" for t in tls)
        except Exception:
            pass
        print(line)


def describe_refs(s, idx):
    out = []
    for r in s.get("extra_material_refs", []):
        if r not in idx:
            continue
        k, m = idx[r]
        if k in SKIP_REFS:
            continue
        if k == "material_animations":
            out += [f"{x['type']}:{x['name']}({x['duration'] / S:.2f}s)" for x in m.get("animations", [])]
        elif k == "audio_fades":
            out.append(f"fade {m['fade_in_duration'] / S:.2f}/{m['fade_out_duration'] / S:.2f}")
        else:
            out.append(k if k != "effects" else f"effect:{m.get('name') or m.get('type')}")
    return out


def cmd_analyze(a):
    path, _ = resolve(a)
    d = load(path)
    idx = index(d)
    print(f"# {path}\nThời lượng {d['duration'] / S:.2f}s · {d['fps']}fps · canvas {d['canvas_config']}\n")
    for ti, tr in enumerate(d["tracks"]):
        print(f"## Track {ti} · {tr['type']} · {len(tr['segments'])} đoạn")
        for s in tr["segments"]:
            x0, x1 = seg_range(s)
            k, m = idx.get(s["material_id"], ("?", {}))
            if k == "texts":
                what = f"CHỮ {text_of(m)!r} size={m.get('font_size')} màu={m.get('text_color')}"
            elif k in ("videos", "audios"):
                what = f"{m.get('type')} {os.path.basename(m.get('path') or '') or m.get('name')} vol={s.get('volume', 1):.2f}"
            else:
                what = f"[{k}] {m.get('name') or m.get('type')}"
            c = s.get("clip") or {}
            extra = ""
            if c and tr["type"] in ("video", "text"):
                extra = f" pos=({c['transform']['x']:.2f},{c['transform']['y']:.2f}) scale={c['scale']['x']:.2f}"
            refs = describe_refs(s, idx)
            print(f"- {x0:7.2f}–{x1:7.2f} ({x1 - x0:5.2f}s) {what}{extra}" + (f"  ⟨{' | '.join(refs)}⟩" if refs else ""))
            for kf in s.get("common_keyframes") or []:
                if kf["property_type"] == "KFTypeScaleX":
                    pts = [(round(x["time_offset"] / S, 2), round(x["values"][0], 3)) for x in kf["keyframe_list"]]
                    print(f"    zoom keyframes: {pts}")
        print()
    main = next((t["segments"] for t in d["tracks"] if t["type"] == "video"), [])
    durs = [seg_range(s)[1] - seg_range(s)[0] for s in main]
    if durs:
        print(f"Track video chính: {len(durs)} cảnh, trung vị {statistics.median(durs):.2f}s, "
              f"≈{len(durs) / (d['duration'] / S) * 60:.0f} cắt/phút")


# ---------------------------------------------------------------- học kho mẫu từ CapCut của người dùng
def duyet_du_an(gioi_han):
    names = [n for n in os.listdir(ROOT) if os.path.isfile(os.path.join(ROOT, n, "draft_content.json"))]
    names.sort(key=lambda n: -os.path.getmtime(os.path.join(ROOT, n)))
    for name in names[:gioi_han]:
        try:
            _, tls = timelines(name)
            paths = [t["path"] for t in tls]
        except Exception:
            paths = [os.path.join(ROOT, name, "draft_content.json")]
        for p in paths:
            if os.path.isfile(p):
                yield name, p


def kieu_chu(m):
    f = m.get("fonts") or []
    font = (f[0].get("title") if f else "") or os.path.basename(m.get("font_path") or "") or "mặc định"
    co_nen = bool(m.get("background_color")) and float(m.get("background_alpha") or 0) > 0
    return (font, round(float(m.get("font_size") or 0), 1), (m.get("text_color") or "").lower(),
            round(float(m.get("background_alpha") or 0), 1) if co_nen else 0.0)


def dong_goi(ttype, s, k, m, refs):
    seg = {kk: vv for kk, vv in s.items() if not kk.startswith("_")}
    return {"track_type": ttype, "segment": seg, "material": [k, m], "refs": [[kk, mm] for kk, mm in refs]}


def cmd_hoc(a):
    chu, am, n_file = {}, {}, 0
    for name, path in duyet_du_an(a.so_du_an):
        try:
            d = load(path)
        except Exception:
            continue
        n_file += 1
        idx = index(d)
        for tr in d["tracks"]:
            for s in tr["segments"]:
                k, m = idx.get(s.get("material_id"), ("?", {}))
                refs = [idx[r] for r in s.get("extra_material_refs", []) if r in idx]
                if tr["type"] == "text" and k == "texts":
                    e = chu.setdefault(kieu_chu(m), {"so_lan": 0, "vi_du": [], "du_an": name, "mau": None})
                    e["so_lan"] += 1
                    t = text_of(m)
                    if t and len(e["vi_du"]) < 3 and t[:40] not in e["vi_du"]:
                        e["vi_du"].append(t[:40])
                    if e["mau"] is None:
                        e["mau"] = dong_goi("text", s, k, m, refs)
                elif tr["type"] == "audio" and k == "audios" and m.get("type") == "sound" \
                        and m.get("path") and os.path.exists(m["path"]):
                    nm = m.get("name") or os.path.basename(m["path"])
                    e = am.setdefault(nm, {"so_lan": 0, "du_an": name, "mau": None})
                    e["so_lan"] += 1
                    if e["mau"] is None:
                        e["mau"] = dong_goi("audio", s, k, m, refs)
    kho = {"tao_luc": datetime.datetime.now().isoformat(timespec="seconds"), "goc": ROOT,
           "chu": {}, "sfx": {}, "bi_danh": {}}
    for i, (key, e) in enumerate(sorted(chu.items(), key=lambda kv: -kv[1]["so_lan"]), 1):
        font, size, mau, nen = key
        e["mo_ta"] = f"{font} · cỡ {size} · màu {mau or '?'}" + (f" · nền {nen}" if nen else "")
        kho["chu"][f"t{i}"] = e
    for i, (nm, e) in enumerate(sorted(am.items(), key=lambda kv: -kv[1]["so_lan"]), 1):
        e["mo_ta"] = nm
        kho["sfx"][f"s{i}"] = e
    ids = list(kho["chu"])
    if ids:
        kho["bi_danh"]["phu_de"] = ids[0]
        # nhấn mạnh: kiểu chữ lớn hơn phụ đề nếu có, không thì kiểu thứ hai
        size0 = float(chu_size(kho["chu"][ids[0]]))
        lon = [i for i in ids[1:] if chu_size(kho["chu"][i]) > size0]
        if lon:
            kho["bi_danh"]["nhan_manh"] = lon[0]
        elif len(ids) > 1:
            kho["bi_danh"]["nhan_manh"] = ids[1]
    os.makedirs(os.path.dirname(a.kho), exist_ok=True)
    json.dump(kho, open(a.kho, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"Đã quét {n_file} dòng thời gian trong {len({v['du_an'] for v in list(chu.values()) + list(am.values())})} dự án.")
    print(f"Tìm thấy {len(kho['chu'])} kiểu chữ và {len(kho['sfx'])} hiệu ứng âm thanh. Đã lưu: {a.kho}")
    if not kho["chu"]:
        print("⚠ Chưa thấy chữ nào trong dự án CapCut của bạn. Mở CapCut, thêm 1–2 dòng chữ (chọn font/màu bạn thích) vào bất kỳ dự án nào, đóng CapCut rồi chạy lại 'hoc'.")
    if not kho["sfx"]:
        print("⚠ Chưa thấy hiệu ứng âm thanh nào đã tải về. Mở CapCut > Âm thanh > Hiệu ứng âm thanh, thêm vài tiếng bạn thích vào bất kỳ dự án nào, đóng CapCut rồi chạy lại 'hoc'.")
    if kho["bi_danh"]:
        print("Mặc định:", kho["bi_danh"], "(đổi bằng lệnh 'chon')")
    print("Chạy 'mau' để xem danh sách.")


def chu_size(e):
    return e["mau"]["material"][1].get("font_size") or 0


def doc_kho(a):
    if not os.path.isfile(a.kho):
        sys.exit("Chưa có kho mẫu. Chạy: python junops_capcut.py hoc")
    return json.load(open(a.kho, encoding="utf-8"))


def cmd_mau(a):
    kho = doc_kho(a)
    print("KIỂU CHỮ (id · số lần bạn đã dùng · mô tả · ví dụ)")
    for i, e in kho["chu"].items():
        print(f"  {i:4s} ×{e['so_lan']:<3d} {e['mo_ta']:50s} ví dụ: {e['vi_du']}")
    print("\nHIỆU ỨNG ÂM THANH (id · số lần · tên)")
    for i, e in kho["sfx"].items():
        print(f"  {i:4s} ×{e['so_lan']:<3d} {e['mo_ta']}")
    print("\nBiệt danh đang dùng:", kho["bi_danh"])


def cmd_chon(a):
    kho = doc_kho(a)
    for ten, v in (("phu_de", a.phu_de), ("nhan_manh", a.nhan_manh), ("chu_to", a.chu_to)):
        if v:
            if v not in kho["chu"]:
                sys.exit(f"Không có kiểu chữ {v}. Chạy 'mau' để xem id.")
            kho["bi_danh"][ten] = v
    json.dump(kho, open(a.kho, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("Biệt danh:", kho["bi_danh"])


def lay_mau(kho, ten, loai):
    ten = kho["bi_danh"].get(ten, ten)
    nguon = kho[loai]
    if ten not in nguon:
        sys.exit(f"Không có mẫu {ten!r} trong kho {loai}. Chạy 'mau' để xem.")
    return nguon[ten]["mau"]


# ---------------------------------------------------------------- ghi dự án: chữ, sfx, zoom
def find_track(d, ttype, a, b, prefer=None):
    cands = [i for i, t in enumerate(d["tracks"]) if t["type"] == ttype]
    if prefer is not None and prefer in cands:
        cands = [prefer] + [c for c in cands if c != prefer]
    for i in cands:
        if all(seg_range(s)[1] <= a + 1e-6 or seg_range(s)[0] >= b - 1e-6 for s in d["tracks"][i]["segments"]):
            return i
    d["tracks"].append({"id": new_id(), "type": ttype, "flag": 0, "attribute": 0,
                        "name": "", "is_default_name": True, "segments": []})
    return len(d["tracks"]) - 1


def add_from_template(d, tpl, start, dur, text=None, x=None, y=None, scale=None, volume=None, track=None):
    ttype = tpl["track_type"]
    seg = copy.deepcopy(tpl["segment"])
    kind, mat = copy.deepcopy(tpl["material"])
    idmap = {mat["id"]: new_id()}
    mat["id"] = idmap[mat["id"]]
    if text is not None:
        content = json.loads(mat["content"])
        content["text"] = text
        st = content["styles"][0]
        st["range"] = [0, len(text.encode("utf-16-le")) // 2]
        content["styles"] = [st]
        mat["content"] = json.dumps(content, ensure_ascii=False)
        if isinstance(mat.get("words"), dict):
            mat["words"] = {"start_time": [], "end_time": [], "text": []}
    d["materials"].setdefault(kind, []).append(mat)
    new_refs = []
    for rk, rm in copy.deepcopy(tpl["refs"]):
        idmap[rm["id"]] = new_id()
        rm["id"] = idmap[rm["id"]]
        d["materials"].setdefault(rk, []).append(rm)
        new_refs.append(rm["id"])
    seg.update(id=new_id(), material_id=mat["id"], extra_material_refs=new_refs, common_keyframes=[], keyframe_refs=[])
    seg["target_timerange"] = {"start": int(start * S), "duration": int(dur * S)}
    if ttype == "audio":
        seg["source_timerange"] = {"start": 0, "duration": int(dur * S * (seg.get("speed") or 1))}
    elif seg.get("source_timerange"):
        seg["source_timerange"]["duration"] = int(dur * S * (seg.get("speed") or 1))
    c = seg.get("clip")
    if c:
        if x is not None:
            c["transform"]["x"] = x
        if y is not None:
            c["transform"]["y"] = y
        if scale is not None:
            c["scale"] = {"x": scale, "y": scale}
    if volume is not None:
        seg["volume"] = seg["last_nonzero_volume"] = volume
    ti = find_track(d, ttype, start, start + dur, track)
    seg["track_render_index"] = ti
    d["tracks"][ti]["segments"].append(seg)
    d["tracks"][ti]["segments"].sort(key=lambda s: s["target_timerange"]["start"])
    d["duration"] = max(d["duration"], int((start + dur) * S))
    return ti


def add_zoom(d, at, points):
    """points: [[giây tính từ 'at', tỉ lệ], ...] — thêm keyframe phóng to vào đoạn video chính đang chạy tại 'at'."""
    vt = next((t for t in d["tracks"] if t["type"] == "video"), None)
    if vt is None:
        raise ValueError("Dòng thời gian chưa có track video")
    for s in vt["segments"]:
        x0, x1 = seg_range(s)
        if x0 <= at < x1:
            src0 = (s.get("source_timerange") or {}).get("start", 0)
            base = src0 + int((at - x0) * S * (s.get("speed") or 1))
            kfs = [{"id": new_id(), "curveType": "FreeCurveInOut", "time_offset": base + int(t * S),
                    "left_control": {"x": 0.0, "y": 0.0}, "right_control": {"x": 0.0, "y": 0.0},
                    "values": [float(v)], "string_value": "", "graphID": ""} for t, v in points]
            ck = s.setdefault("common_keyframes", []) or []
            s["common_keyframes"] = ck
            sx = next((k for k in ck if k["property_type"] == "KFTypeScaleX"), None)
            if sx is None:
                sx = {"id": new_id(), "material_id": "", "property_type": "KFTypeScaleX", "keyframe_list": []}
                ck.append(sx)
            lo, hi = kfs[0]["time_offset"], kfs[-1]["time_offset"]
            if any(lo - 50_000 <= k["time_offset"] <= hi + 50_000 for k in sx["keyframe_list"]):
                raise ValueError(f"Đoạn tại {at}s đã có keyframe zoom trong khoảng này, chọn thời điểm khác")
            sx["keyframe_list"] = sorted(sx["keyframe_list"] + kfs, key=lambda k: k["time_offset"])
            return x0
    raise ValueError(f"Không có đoạn video ở track chính tại {at}s")


def cmd_apply(a):
    path, pdir = resolve(a)
    kiem_tra_dong_capcut(a.dry_run, pdir)
    kho = doc_kho(a) if any(o["op"] in ("chu", "sfx") for o in json.load(open(a.plan, encoding="utf-8"))["ops"]) else None
    plan = json.load(open(a.plan, encoding="utf-8"))
    d = load(path)
    log, vong_sfx = [], []
    ids_sfx = [i for i, e in kho["sfx"].items()
               if (e["mau"]["material"][1].get("duration") or 0) <= 2_500_000] if kho else []
    if kho and not ids_sfx:
        ids_sfx = list(kho["sfx"])  # không có tiếng ngắn thì dùng tạm tất cả (sẽ bị cắt ngắn theo dur)
    for op in plan["ops"]:
        kind = op["op"]
        if kind == "zoom":
            pts = op.get("points")
            if not pts:  # dạng ngắn: tỉ lệ + giữ + vào + ra
                vao, giu, ra, muc = op.get("vao", 0.3), op.get("giu", 1.0), op.get("ra", 0.4), op.get("muc", 1.15)
                pts = [[0, 1.0], [vao, muc], [round(vao + giu, 3), muc], [round(vao + giu + ra, 3), 1.0]]
            x0 = add_zoom(d, op["at"], pts)
            log.append(f"zoom   @ {op['at']}s (đoạn bắt đầu {x0:.2f}s) {pts}")
        elif kind == "chu":
            tpl = lay_mau(kho, op.get("mau", "phu_de"), "chu")
            ti = add_from_template(d, tpl, op["start"], op["dur"], op["text"], op.get("x"), op.get("y"),
                                   op.get("scale"), None, op.get("track"))
            log.append(f"chữ    {op.get('mau', 'phu_de'):10s} {op['start']:7.2f}s +{op['dur']:.2f}s track {ti} {op['text']!r}")
        elif kind == "sfx":
            ten = op.get("mau", "auto")
            if ten == "auto":
                if not ids_sfx:
                    sys.exit("Kho chưa có hiệu ứng âm thanh. Chạy 'hoc' sau khi thêm vài SFX vào CapCut.")
                ung = [i for i in ids_sfx if i not in vong_sfx[-3:]] or ids_sfx
                ten = ung[len(vong_sfx) % len(ung)]
                vong_sfx.append(ten)
            tpl = lay_mau(kho, ten, "sfx")
            dur_mau = (tpl["material"][1].get("duration") or int(1.0 * S)) / S
            dur = min(op.get("dur", dur_mau), dur_mau, 3.0) if ten != op.get("mau") else min(op.get("dur", dur_mau), dur_mau)
            ti = add_from_template(d, tpl, op["at"], dur, None, None, None, None, op.get("volume", 0.32), op.get("track"))
            log.append(f"sfx    {ten:6s} {op['at']:7.2f}s +{dur:.2f}s track {ti} ({kho['sfx'][ten]['mo_ta'][:40]})")
        else:
            sys.exit(f"Không hiểu op {kind!r} (chỉ có: chu, sfx, zoom)")
    print("\n".join(log))
    if a.dry_run:
        print(f"\n(dry-run) {len(log)} thao tác, chưa ghi gì.")
        return
    n, bdir = ghi_du_an(d, path, pdir, "apply")
    print(f"\nĐã ghi {len(log)} thao tác vào {n} file. Backup: {bdir}")


# ---------------------------------------------------------------- ghi các đoạn đã cắt
def cmd_cat(a):
    path, pdir = resolve(a)
    kiem_tra_dong_capcut(a.dry_run, pdir)
    d = load(path)
    idx = index(d)
    vt = next((t for t in d["tracks"] if t["type"] == "video"), None)
    if not vt or not vt["segments"]:
        sys.exit("Dòng thời gian chưa có video. Mở CapCut, kéo video thô vào dòng thời gian, đặt tên dự án rồi đóng CapCut.")
    mau = {}
    for s in vt["segments"]:
        if s["material_id"] not in mau:
            mau[s["material_id"]] = (copy.deepcopy(s), os.path.basename(idx[s["material_id"]][1].get("path") or "").lower())
    edl = json.load(open(a.edl, encoding="utf-8"))
    fps = float(d.get("fps") or 30)

    def f2us(f):
        return int(round(f * S / fps))

    def chon(clip):
        ds = list(mau.items())
        if clip in (None, ""):
            if len(ds) == 1:
                return ds[0]
            sys.exit(f"Dòng thời gian có {len(ds)} file video; hãy ghi 'clip' (một phần tên file) cho từng đoạn trong edl.")
        if isinstance(clip, int):
            return ds[clip]
        for mid, (s, ten) in ds:
            if str(clip).lower() in ten:
                return mid, (s, ten)
        sys.exit(f"Không thấy file video nào khớp {clip!r}. Có: {[t for _, (_, t) in ds]}")

    cu = {r for s in vt["segments"] for r in s.get("extra_material_refs", [])}
    for k in REF_GIU:
        if k in d["materials"]:
            d["materials"][k] = [x for x in d["materials"][k] if x["id"] not in cu]
    segs, pos, prev_b, ban_do = [], 0, {}, []
    for i, e in enumerate(edl, 1):
        mid, (tpl_seg, ten) = chon(e.get("clip"))
        f0 = int(round(e["a"] * fps))
        n = max(1, round((e["b"] - e["a"]) * fps))
        if mid in prev_b and f0 < prev_b[mid]:  # đoạn kề nhau chồng vài khung thì nối khít
            n -= prev_b[mid] - f0
            f0 = prev_b[mid]
        prev_b[mid] = f0 + n
        s = copy.deepcopy(tpl_seg)
        ids = []
        for r in tpl_seg.get("extra_material_refs", []):
            if r in idx and idx[r][0] in REF_GIU:
                rm = copy.deepcopy(idx[r][1])
                rm["id"] = new_id()
                d["materials"].setdefault(idx[r][0], []).append(rm)
                ids.append(rm["id"])
        vol = 10 ** (float(e.get("gain_db", 0)) / 20)
        s.update(id=new_id(), material_id=mid, extra_material_refs=ids, common_keyframes=[], keyframe_refs=[],
                 volume=vol, last_nonzero_volume=vol,
                 source_timerange={"start": f2us(f0), "duration": f2us(f0 + n) - f2us(f0)},
                 target_timerange={"start": f2us(pos), "duration": f2us(pos + n) - f2us(pos)})
        segs.append(s)
        ban_do.append({"stt": i, "file": ten, "dong_thoi_gian": [round(pos / fps, 3), round((pos + n) / fps, 3)],
                       "nguon": [round(f0 / fps, 3), round((f0 + n) / fps, 3)], "ghi_chu": e.get("loi", "")})
        pos += n
    vt["segments"] = segs
    d["duration"] = f2us(pos)
    out_map = os.path.join(os.path.dirname(os.path.abspath(a.edl)), "ban_do_cat.json")
    json.dump(ban_do, open(out_map, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"{len(segs)} đoạn · tổng {pos / fps:.2f}s ({int(pos / fps // 60)}:{pos / fps % 60:05.2f}). Bản đồ cắt: {out_map}")
    if a.dry_run:
        print("(dry-run) chưa ghi gì.")
        return
    n_file, bdir = ghi_du_an(d, path, pdir, "cat")
    print(f"Đã ghi {n_file} file. Backup: {bdir}")
    print("Lưu ý: nếu dòng thời gian còn track âm thanh/video khác (lồng tiếng, B-roll), chúng chưa được cắt theo.")


def main():
    chung = argparse.ArgumentParser(add_help=False)
    chung.add_argument("--root", help="thư mục bản nháp CapCut (mặc định tự tìm)")
    chung.add_argument("--kho", default=KHO_MAC_DINH, help="file kho mẫu (mặc định du_lieu/kho_mau.json)")
    ap = argparse.ArgumentParser(description="Skill JunOps — đọc/ghi dự án CapCut")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("list", parents=[chung])
    sub.add_parser("mau", parents=[chung])
    p = sub.add_parser("hoc", parents=[chung])
    p.add_argument("--so-du-an", type=int, default=12, help="quét tối đa bấy nhiêu dự án gần nhất")
    p = sub.add_parser("chon", parents=[chung])
    p.add_argument("--phu-de")
    p.add_argument("--nhan-manh")
    p.add_argument("--chu-to")
    for name in ("analyze", "apply", "cat"):
        p = sub.add_parser(name, parents=[chung])
        p.add_argument("project", nargs="?")
        p.add_argument("--timeline", default="01")
        p.add_argument("--draft-file", help="trỏ thẳng tới 1 file draft_content.json (để thử trên bản sao)")
        if name in ("apply", "cat"):
            p.add_argument("--dry-run", action="store_true")
        if name == "apply":
            p.add_argument("--plan", required=True)
        if name == "cat":
            p.add_argument("--edl", required=True)
    a = ap.parse_args()
    global ROOT
    if not getattr(a, "draft_file", None):
        ROOT = tim_goc(a.root)
    else:
        ROOT = a.root or ""
    if a.cmd in ("hoc", "list") and not ROOT:
        sys.exit("Cần --root hoặc để skill tự tìm thư mục CapCut.")
    {"list": cmd_list, "analyze": cmd_analyze, "hoc": cmd_hoc, "mau": cmd_mau, "chon": cmd_chon,
     "apply": cmd_apply, "cat": cmd_cat}[a.cmd](a)


if __name__ == "__main__":
    main()
