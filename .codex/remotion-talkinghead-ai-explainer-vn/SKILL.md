---
name: remotion-talkinghead-ai-explainer-vn
description: Dựng video talking-head tiếng Việt kiểu "AI/tech explainer" cho TikTok/Reels/Shorts bằng Remotion từ footage raw + transcript - tự chọn highlight, cắt khoảng lặng/ừm à/take lặp (EDL), caption word-rise vàng-trắng, punch-in framing wide/mid/tight, chip-stack, prompt-box, scene tối dạng info-card, title REC + timeline, sticker, comment CTA. Hỗ trợ dọc 9:16, ngang 16:9, vuông và mọi tỉ lệ khác nhờ bước probe bắt buộc. Dùng cho video giới thiệu công cụ AI, tips công nghệ, review phần mềm, người nói đối diện camera; không dùng cho video house tour, vlog không lời, hay dự án có brand guideline khác.
---

# Remotion Talking-head AI Explainer VN (v4.5.1)

> **ĐỌC `AGENTS.md` TRƯỚC - đó là điểm vào duy nhất.** Nó có quy trình bắt buộc 16 bước (probe -> transcribe/cleanup -> EDL/tighten -> masks -> beats -> captions -> text-behind -> illustrations -> logos -> render -> verify -> feedback -> fix -> re-verify -> deliver) và nói rõ phải đọc `references/*.md` nào ở từng bước. Mỗi file reference có frontmatter (`name`, `when`), luật cứng, lệnh, ngưỡng.
> **BẮT BUỘC (không được bỏ):** `references/verified.md` (V-rule máy kiểm được, lệnh `verify_rules.py`) và `references/feedback.md` (mẫu báo cáo mỗi vòng `out/verify/feedback_round<N>.md` + mẫu `out/blockers.md`). Tối đa 3 vòng rewrite; chỉ giao khi mọi V-rule đạt, nếu không thì ghi `blockers.md` và báo cáo, KHÔNG giao.
> Không đẩy lên GitHub, không upload ở bất kỳ bước nào của template.

## v4.5.1 (gap/priority/V05b)
- Icon gap is start-to-start >= 5 s (`density.gapMode`), cap 4 per 30 s, `concepts.<c>.priority` (customer-talk/sales = 10) beats generic concepts. V05b `--source` = the ORIGINAL UNPATCHED raw; waivers only by explicit user decision. See references/illustrations.md, quality-control.md.

## v4.5 NOTES (icon density, side by person mask, subtitle-removal patch)
1. **V21 mật độ icon:** <= 1 icon / 7.5 s (<= 4 trong 30 s), khoảng cách end->start >= 5 s, cùng concept cách >= 15 s; giữ concept mạnh nhất (`autoBeats.illustration.density`).
2. **V22 bên icon:** chọn theo mask người của CẢ cửa sổ icon (slot trên/giữa/dưới, cả 2 bên, kích thước tới ~120 px, chừa >= 6 px); không ép đè; nếu không bên phải nào trống thì ở lại trái và ghi `_sideReason`.
3. **V23 mảng blur sau khi xoá sub:** `verify_rules.py --blur-scan <raw>.mp4` -> nếu có patch thì `scripts/reinpaint_patch.py` (re-inpaint không gian từ video gốc, cùng số frame/audio), ghi `out/patch_manifest.json`, chạy lại blur-scan + verify với `--source`. Cover bằng caption KHÔNG đủ. Xem `AGENTS.md` bước 1b / `references/quality-control.md`.
4. `python3 scripts/check_template_rules.py --project public/project --target-sec 30` chạy V21-V23 (không đụng `verify_rules.py`).

## v4.4 NOTES
1. Caption: KHÔNG nền (không pill/hộp/blur); đọc được nhờ stroke >= 6 px (config 8) + bóng mềm. Headline framed-focus/info-scene/topic-card cũng là chữ vàng có stroke (`beats.infoScene.pillFilled=false`).
2. Text-behind: cụm từ phải đủ nghĩa (lint `badFragments`/`badEdgeWords`), tràn thì xuống dòng 2 (layout wrap: dòng 1 sau đỉnh đầu, che 3-10%, glyph >= 70%, đọc được >= 90%), đo trên mask CHỈ người bằng `command_person_only` trong `_tbs.json` (`scripts/tbs_manifest.py`).
3. Icon: chọn bên theo chỗ trống, đa dạng, không che mặt/caption/logo (`_sideReason` trong `_icons.json`). Phone/window frame tối đa `max(1, floor(duration_sec/30))`, không liền kề (V14). Logo chỉ bỏ sau khi đã thử thêm slot/cỡ.
4. Mai -> Mike chỉ khi có ngữ cảnh công cụ AI, cấu hình ở `textCleanup.ambiguousWords.mai`.
5. Hiệu năng render dọc: `scripts/ensure_keyframes.py` (GOP <= 1 s) chạy trong `render.sh`; render thử 29.6 s ~ 105-115 s. Kiểm mặt caption trên TỪNG khung: `scripts/check_caption_face.py` (V04).
6. Bằng chứng: `scripts/make_evidence.py` ra `_contact.jpg`, `_tbs.json`, `_still_*`, `_icons.json`, `_beats.json` cho `verify_rules.py`.
7. Biết trước: V05 flat-panel có thể báo nhầm ở beat framed-focus (xem AGENTS.md "Known tool behaviour").

---


Template này được trích từ MỘT video đã dựng xong (TikTok `7702817920237210898`, 1080x1920, 30fps, 48.6s). Mục tiêu: dùng lại 95-100% phong cách đó cho footage raw mới. **Mọi con số phong cách nằm trong một file: `style.config.json`.** Video mới chỉ đổi 4 thứ: raw footage, transcript, EDL (cut list) và `beats.json`.

Ký hiệu độ tin cậy trong config và tài liệu: **[M]** đã đo, **[E]** ước lượng, **[U]** không đo được. Các khoảng trống còn lại nằm ở `style.config.json -> gaps[]` và cuối `analysis.md`.

## 0. QUY TRÌNH BẮT BUỘC (đúng thứ tự, không đảo)

```
STEP 0  python3 scripts/probe_video.py <raw.mp4> [--target native|vertical] [--reframe blurfill|crop]   -> public/project/probe.json
STEP 1  python3 scripts/transcribe.py public/project/raw.mp4 [--out dir|file] (deterministic: float32, temp 0, forced vi; 0 segment => exit 1 (nonzero))   (render-env venv, faster-whisper medium, text_cleanup + từ điển thương hiệu trong style.config.json) -> words.json
STEP 2  python3 scripts/make_edl.py --words public/project/words.json                                     -> edl.json, captions.json, beats.suggested.json, edl_report.md
STEP 3  python3 scripts/make_beats.py --words public/project/words.json --edl public/project/edl.json  -> beats.json tự sinh (chỉ cần duyệt), placeholder editor.png/phone.png tự tạo
STEP 3a python3 scripts/make_masks.py public/project   (CHỈ khi có beat `text-behind-speaker`; BẮT BUỘC verify người nói + chọn chỗ trống, xem mục TEXT-BEHIND; tách người cho từng beat -> public/project/masks/<id>/mask_00000.png; cần render-env/person_mask.py + rembg/onnxruntime)
STEP 3b duyệt public/project/beats.json (xem examples/reference.beats.json), sửa edl.json nếu cần
STEP 4  npm run studio   (xem trước)  ->  scripts/render.sh out/final.mp4  (KHÔNG dùng `npm run render` trần: render.sh chạy cổng overlap bắt buộc, 0 overlap mới render) ->  node scripts/verify-video.mjs out/final.mp4
```

- **KHÔNG được dựng, cắt hay đặt overlay trước khi `public/project/probe.json` tồn tại** (`gate: "passed"`). `make_edl.py`, composition (`Root.tsx`) và `verify-video.mjs` đều từ chối chạy nếu thiếu.
- Hỏi người dùng nền tảng đích nếu raw ngang/vuông: giữ nguyên tỉ lệ (`--target native`) hay xuất dọc 9:16 (`--target vertical`, mặc định blur-fill).
- Độ dài video ra là **kết quả** (tổng các đoạn giữ lại), không ép bằng raw hay bằng video tham chiếu.

## BRAND LOGOS (MANDATORY step)
Khi transcript nhắc tới thương hiệu/sản phẩm nổi tiếng (ChatGPT, OpenAI, Claude, Anthropic, Gemini, Stripe, SQLite, GitHub, Cursor, Notion, Figma, YouTube, TikTok, Remotion, Python, Node.js, ...) agent **PHẢI** lấy logo THẬT và hiển thị bằng beat `brand-logo` (đừng bao giờ tự vẽ/bịa logo).
1. Phát hiện: chạy `make_beats.py` -> dòng `BRAND LOGOS MISSING (...)`; tự đọc transcript (ASR nghe sai: 'chát GPT', 'cớt', 'sờ quy lai', 'du túp'); thêm brand/alias mới vào `style.config.json -> brandLogos.brands`.
2. Lấy logo - **thử đủ mọi nguồn theo thứ tự trước khi bỏ cuộc**: Simple Icons -> svgl.app -> Wikimedia Commons -> trang chính thức/press kit -> favicon 256 (cuối cùng). `scripts/fetch_logo.sh <slug> [simple-icons-slug] [domain] [svgl query]` tự làm 1,2,5 -> `public/project/logos/<slug>.svg|png`; 3,4 làm tay bằng curl. Không có nguồn nào -> ghi `NOT FOUND` vào Registry, bỏ qua beat, báo user.
3. So với Registry trong `references/brand-logos.md`: mới -> thêm dòng; đã có -> chỉ thay khi tốt hơn (SVG > PNG, vector > raster, độ phân giải cao hơn, nguồn chính thức > favicon, SVG hợp lệ/sạch); thay thì ghi nguồn, màu, ngày, `previous:`. Nếu là SVG và cần dùng làm component, thêm/cập nhật `src/components/brands/<Name>Logo.tsx` (tuỳ chọn).
4. Chạy lại `make_beats.py` (beat `brand-logo` ở lần nhắc đầu tiên, tối đa ~1 logo / 4s, thắng `sticker` thương hiệu chung chung). Chi tiết + Registry: `references/brand-logos.md`.

## ILLUSTRATIONS (v4.2 - MANDATORY step)
Khi lời nói nhắc tới một **khái niệm vẽ được** (giao tiếp với khách hàng -> hai người đang nói chuyện; sale/bán -> thẻ giá/giỏ hàng; tiền; tăng trưởng/phát triển; thời gian; AI; học tập; tài liệu; công việc; ý tưởng; mục tiêu; họp nhóm; dữ liệu; email), agent **PHẢI** cho một icon minh họa bật lên (beat `illustration`, `src/components/Beats.tsx` -> `Illustration`: thẻ tối viền màu, icon + nhãn, pop-in + lắc nhẹ). Không bao giờ để ô trống/placeholder.
1. Phát hiện: `make_beats.py` tự dò bảng từ khoá -> khái niệm `style.config.json -> autoBeats.illustration.concepts` (so khớp NGUYÊN TỪ, **có dấu** - gấp dấu sẽ nhầm 'bán' = 'bạn'; từ viết hoa như 'AI' khớp phân biệt hoa/thường vì 'ai' tiếng Việt = 'who'). Đọc lại transcript tìm khái niệm bảng chưa có (ASR sai thì sửa glossary) và thêm một dòng `concepts` mới.
2. Lấy icon - thứ tự nguồn: icon mã nguồn mở THẬT trước (`scripts/fetch_icon.sh <slug> lucide:<tên> tabler:<tên> ph:<tên> mi:<tên> iconify:<prefix>/<tên>`; Lucide ISC -> Tabler MIT -> Phosphor MIT -> Material Symbols Apache-2.0 -> Iconify), rồi mới tới **SVG tự vẽ** (`assets/illustrations/*.svg`, ví dụ `two-people-talking.svg` cho giao tiếp - Lucide chỉ có bong bóng chat, không có "hai người nói chuyện"). Script tự đổi màu về trắng, ghi nguồn + giấy phép vào `public/project/illustrations/icons.json`.
3. So sánh + ghi: đối chiếu bản đồ khái niệm -> icon ở `references/illustrations.md` (mới -> thêm dòng; đã có -> chỉ thay khi icon tốt hơn: đúng nghĩa hơn, nét sạch hơn, giấy phép rõ).
4. Đặt vị trí: `logo_place.place(strict=True)` (cùng mô hình thẻ với brand-logo, ưu tiên bên TRÁI/PHẢI mặt, trên caption). Không có chỗ không che mặt / không đè beat khác => **bỏ beat và log lý do** (không "ít chồng nhất"). Chuỗi ngắn "giao tiếp, sale, tài liệu" => icon sau thay icon trước ở cùng ô. Gate overlap vẫn kiểm lại bằng hộp DOM (`data-guard="illustration"`). Chi tiết: `references/illustrations.md`.

## TEXT-BEHIND (v4.2 - MANDATORY verify)
Chữ nằm SAU người nói chỉ được đặt vào **nền trống**, không để người nói che chữ. Quy trình bắt buộc, chi tiết ở `references/text-behind.md`:
1. `make_beats.py` chỉ đề xuất cửa sổ trong MỘT đoạn EDL ổn định (sau khi punch lắng, không zoom ramp, >= 1.4s); mọi lần bỏ qua đều log lý do (`_skips` trong beats.json).
2. `make_masks.py` tách người nói (person mask) rồi quét vị trí/cỡ chữ/cách ngắt dòng (1 dòng ~0.55, 2 dòng ~0.75, trái/phải/giữa) chọn chỗ nền trống; đo bằng **`text_occlusion.py` của Render (CÔNG CỤ CHUẨN, không viết công cụ cạnh tranh; thiếu thì dùng fallback cùng giao diện/ngưỡng và ghi `_tool`)**.
3. Cổng: trung bình >= **90%** đọc được VÀ khung xấu nhất >= **90%** (bị che <= 10%). Không có vị trí nào đạt => KHÔNG render chữ bị che: beat đổi thành `big-word` (headline thường, `_fallbackFrom`). `render.sh` chạy lại `tbs_place.py --check` trên mask đã warp theo zoom (`out/tbs_canvas/<id>`) - fail thì autofix đổi sang headline.
4. Xem still tại giữa cửa sổ beat bằng mắt trước khi giao.


## v4.3 NOTES (từ review của Demo/Render)
1. **Text-behind**: bị che 3-10% (`textBehind.tuneMinOcclusion` 0.03, tối đa 0.10), đọc được >= 90% mean + worst. `make_masks.py` thử: `text_occlusion.py --suggest WxH --text ... --range S,E --require-behind` (render đúng chuỗi `text` trả về, có thể chứa `\n`; exit 4 = không có chỗ) -> tìm nội bộ -> **crown-tracking** (dịch y theo đỉnh đầu từng khung, làm mượt + giới hạn tốc độ; file `public/project/tbs_track_<id>.json`, kiểm bằng `--track`) -> cửa sổ khác ít chuyển động đầu hơn -> beat khác (vd "Tài liệu") với cỡ nhỏ / tách 2 dòng -> bỏ và ghi log. Sau khi đặt vẫn chặn ở 0.10.
2. **make_masks.py nằm trong quy trình** (README + STEP 3a). `render.sh` thiếu masks => tự chạy + banner; `STRICT_TBS=1` => dừng.
3. **autofix_overlaps.py không bao giờ bỏ CTA/comment-box** (`autoBeats.collision.protected`): dời caption lên trên hoặc dời CTA (`dy`). 3 vòng không xong => `exit 2` + `RENDER ABORTED`.
4. **Logo**: va chạm -> thử slot/thời điểm khác (`brandLogos.retryOffsetsSec`, `relocateMaxSec`), dedupe với sticker/phần tử cùng thương hiệu.
5. `Mai` -> `Mike` chỉ khi Viết hoa + gần từ khoá AI (`textCleanup.ambiguousWords.mai`); `Opus 5 .5` -> `Opus 5.5`.
6. Input 16:9 => canvas 1080x1920 (tier 1080 khi nguồn >= 720p hoặc dọc).
7. Icon minh hoạ to hơn: card = logo.size x scales [1.12, 1.03, 0.95, 0.90], icon = 0.70 card (~157-196px), vẫn face-aware.
8. Giới hạn đã biết: beat text-behind chỉ trong MỘT đoạn EDL không cắt/zoom >= 1.4s; footage cận mặt chiếm gần hết khung nên icon không có chỗ -> bỏ (log) thay vì đè mặt.

## 1. Trước khi dựng

- Xem ít nhất 5 khung hình đại diện của raw (mở đầu, 3 điểm giữa, kết). Xác định vùng mặt/tay người nói để overlay không che.
- Đọc `edl_report.md`: mọi đoạn bị bỏ có `reason` (filler, repeat-take, low-energy, off-topic, over-window). Nghe lại những đoạn điểm sát ngưỡng.
- Whisper hay nghe sai tên thương hiệu. `scripts/text_cleanup.py` đã xoá token rác (LAUGHS, CJK) và sửa theo từ điển `textCleanup.brand` trong `style.config.json`; tên mới thì thêm vào từ điển rồi xem lại captions.json một lần.
- Raw dài (>3 phút): dựng demo 30s đầu để duyệt style trước.

## 2. Hệ thống hình ảnh

Chi tiết: [references/style-system.md](references/style-system.md). Tóm tắt (đều đọc từ `style.config.json`):

| Hạng mục | Quy tắc đã đo |
|---|---|
| Cắt | Chỉ hard cut [M]. Không whip/fade/flash. Dark scene fade-in 8 frame |
| Nhịp | ~3.7s/shot [M]; có thay đổi thị giác mới (framing/beat) ít nhất mỗi 3s; không tĩnh >4s |
| Framing | 3 mức: wide 1.0 / mid 1.18 / tight 1.42 [M]; mỗi lần đổi mức: punch-in 1.12x rồi settle 8 frame easeOutCubic [M]; KHÔNG push-in liên tục, KHÔNG rung |
| Caption | Be Vietnam Pro 800, trắng + vàng #F8E277, word-rise (2 frame/chữ, 5 frame, trồi 0.4em, clip đáy) [E ±1f], đổ bóng; tối đa 2 dòng x 4 chữ; dòng 1 trắng, dòng 2 vàng/pill; trang đầu cỡ hero 100px dạng pill; kiểu `dark` (pill tối) khi một beat broll/màn hình đang chạy - caption lên trên cùng; vị trí 65.5% H (trên) hoặc 14.7% H khi dưới bị đồ họa chiếm |
| Overlay beats | stars, sticker, chip-stack, avatar-chain, prompt-box (gạch ngang), title-burst (REC + timeline), big-word, selection-box, comment-box, info-scene, topic-card, broll |
| Grade | low-key ấm nhẹ [E] (xem `grade`) |
| Âm thanh | Giữ audio raw. Nhạc nền: Demucs xác nhận KHÔNG có (sàn -39 dBFS). SFX: chỉ có transient mơ hồ [U] nên mặc định TẮT; bật qua `audio.*` |

## 3. Layer stack (giống remotion-house-review-vn)

1 Footage (EDL, framing, grade) - 2 Beats "under" (broll, info-scene, topic-card) - 3 Beats "over" (chips, sticker, prompt ...) - 4 Captions - 5 Sfx/Music - 6 `LayoutCollisionGuard` (chỉ Studio). Tài liệu: [references/scene-architecture.md](references/scene-architecture.md).

## 4. Highlight + Tighten

Rubric chấm điểm, luật cắt khoảng lặng, jump-cut, đảo hook: [references/highlight-and-tighten.md](references/highlight-and-tighten.md). Ngưỡng ở `style.config.json -> tighten`.

## 5. Hướng (orientation)

Bảng quyết định dọc/ngang/vuông, blur-fill vs crop, vùng an toàn, giới hạn zoom: [references/orientation-layouts.md](references/orientation-layouts.md). Composition lấy width/height/fps/layout từ `probe.json` (`calculateMetadata`), không hard-code.

## 6. QC & học từ phản hồi

[references/quality-control.md](references/quality-control.md), [references/feedback-learning.md](references/feedback-learning.md), [references/content-insights.md](references/content-insights.md). Chạy `npx tsc --noEmit` và `node scripts/verify-video.mjs` trước khi giao.

## 7. Tệp

```
style.config.json        MỘT file cấu hình toàn bộ phong cách (+ gaps)
assets/                  types, remap (EDL<->output time), layouts (probe->layout), style, font
src/                     index, Root (calculateMetadata), Composition, components/{VideoLayer,Captions,Beats,Icons,Sfx,LayoutCollisionGuard,anim}
scripts/                 probe_video.py, transcribe.py, text_cleanup.py, make_edl.py, make_beats.py, make_placeholders.py, verify-video.mjs
public/project/          dữ liệu dự án (probe/edl/captions/beats/raw.mp4/ảnh media)
examples/                reference.{words,captions,beats,edl,probe}.json - timeline của video tham chiếu
reference-frames/        khung hình + sheet 1fps của video tham chiếu
video_output/reference.mp4
analysis.md              timeline đo đạc chi tiết + khoảng trống
```

## v3 notes
Pipeline order unchanged. New knobs: `transcribe.vad/recovery/hallucination`, `textCleanup.properNouns/properAliases` + per-video `public/project/glossary.txt`, `tighten.preset` (light/normal/tight), `autoBeats.generic`, `autoBeats.captionAnchorDefaults`, `screenBroll`. Generic beats never replace keyword beats; they only fill gaps. Known gaps: ASR garble of rare proper nouns (use glossary), screen-b-roll detector is a heuristic, `--no-vad` is not recommended.


## v4.1 notes (collision, face-aware, 2 beat mới)
- **Cổng overlap BẮT BUỘC**: `scripts/render.sh` chạy `node scripts/check_overlaps.mjs public/project` (LayoutCollisionGuard lấy hộp DOM `data-guard` mỗi 2 frame, mọi loại beat x caption x mặt) + `check_logo_faces.py`. Hộp giao nhau > **6px** (cả hai trục, một ngưỡng duy nhất `OVL_PX = 6`) => v4.2: `autofix_overlaps.py` tự sửa tối đa 3 vòng (caption lên đỉnh / bỏ beat ưu tiên thấp) rồi mới `RENDER ABORTED`; không có cờ bỏ qua, không dedupe.
- **Zones** (`assets/zones.ts`): mỗi loại beat khai báo vùng màn hình (`beatRects`); Captions tự dời lên/xuống theo vùng đang bị chiếm; `make_beats.py` dùng cùng bảng vùng (một resolver chung). **Quy tắc viết tay**: `timeline:true` của title-burst chỉ dùng khi cửa sổ đó KHÔNG có caption đè vùng timeline.
- **Face-aware**: `scripts/detect_faces.py` (YuNet ONNX, fallback Haar; `opencv-python-headless==4.10.0.84`) -> `public/project/faces.json`. title/chip/prompt/comment được dịch `dy` khỏi mặt; nếu cận mặt không còn chỗ sạch thì chọn vị trí ít chồng nhất (log "least-overlap") và bỏ timeline nếu title bị đẩy lên nó. Logo thương hiệu: đặt bằng `logo_place.py` (không che mặt; `check_logo_faces.py` kiểm lại, dung sai hộp DOM 10%). Giả định MỘT mặt chính.
- **Cụm từ tiêu đề/chủ đề** (`scripts/vi_phrases.py`): 2-5 từ nguyên cụm (pyvi tuỳ chọn; không có pyvi vẫn chạy bằng luật + từ điển), không cắt giữa cụm, so sánh nhất 'cập nhật' không còn bị nhầm (so khớp theo từ, không gấp dấu), avatar-chain 'thay thế' không còn kích hoạt nhầm.
- **`framed-focus`** (khung thiết bị): footage thu nhỏ trong khung cửa sổ/điện thoại + header lớn + dòng vàng/pill; tự chọn ở khoảnh khắc mạnh (~1 / 20-30s, `autoBeats.framedFocus`). Caption bị ẩn dưới beat này. Lưu ý: chữ trong khung lấy từ transcript, ASR sai ('vắt triển tiếp') sẽ lộ ra -> duyệt `beats.json`.
- **`text-behind-speaker`**: chữ to nằm SAU người nói (mask người qua CSS `mask-image` luminance). Cần `python3 scripts/make_masks.py public/project` (gọi `person_mask.py`, ~3.6 fps CPU; chỉ xử lý cửa sổ của từng beat). Chữ đặt ở đỉnh đầu (`autoBeats.textBehind.centerAboveFaceTopFaceH`) để đầu che ít nhất; chữ ngắn <= 12 ký tự; không kiểm mặt (cố ý chồng sau mặt). Thiếu mask => render lỗi (không tự bỏ beat): luôn chạy make_masks.py sau make_beats.py, và chạy lại sau mỗi lần make_beats.py đổi cửa sổ beat.
- Yêu cầu thêm: `opencv-python-headless==4.10.0.84`, `onnxruntime`/`rembg` (chỉ cho text-behind), pyvi (tuỳ chọn). Giới hạn: một mặt, Haar kém ở góc nghiêng, sticker chưa face-aware, tự chọn ít beat hơn dựng tay (ưu tiên chất lượng hơn số lượng, ~6/phút so với 20/phút tham chiếu).
- **Glossary (sửa ASR) áp dụng TRƯỚC khi dựng chữ**: `public/project/glossary.txt` (`sai => đúng`, mỗi dòng một cặp) được `transcribe.py` áp lúc tạo words.json, và `make_edl.py` (caption) + `make_beats.py` (header/dòng của beat) áp lại khi nạp words.json (`text_cleanup.reapply_glossary`, idempotent) nên sửa glossary sau khi đã transcribe vẫn đúng mà không chạy lại whisper. Project đã có edl.json/captions.json: `python3 scripts/apply_glossary.py public/project` (sửa tại chỗ words.json + captions.json, giữ timing; backup `words.pre_glossary.json`) rồi chạy lại make_beats.py. Lỗi thường gặp đã đưa vào `textCleanup.properAliases`: 'vắt triển' -> 'phát triển'. Luôn quét toàn bộ captions + beat text tìm lỗi nghe nhầm trước khi render.
- **Độ đọc được của text-behind-speaker**: `make_masks.py` đo phần chữ KHÔNG bị người che (raster chữ x mask thật) cho từng y và đặt `beat.y` ở y thấp nhất mà trung bình >= `autoBeats.textBehind.tuneMinReadable` (0.62), sàn `tuneMinTopR` (0.065 H, tránh sát mép). Đo thực tế: đặt thấp hơn (cổ/vai) CHỈ tệ hơn (còn 20-50% đọc được) vì thân rộng hơn đầu; vị trí tối ưu là dòng đỉnh đầu. Chữ rộng 0.97 W (`beats.textBehind.maxWidthR/glyphEm` đã hiệu chỉnh). Log 'BELOW target' => chọn cụm ngắn hơn hoặc chấp nhận.


## v4.2 notes
- **Illustration beat** (mục ILLUSTRATIONS), **text-behind verify** (mục TEXT-BEHIND, ngưỡng 90%/90% đo bằng `text_occlusion.py`), `scripts/fetch_icon.sh`, `assets/illustrations/`.
- **Một ngưỡng overlap = 6px** (`OVL_PX` trong LayoutCollisionGuard, `check_logo_faces.py`, `render.sh`, `autofix_overlaps.py`). Gate đo hộp DOM của MỌI beat (kể cả caption, info-card/topic-line, illustration); thẻ logo/illustration chồng mặt thật > 6px là lỗi, caption/element phủ > 10% mặt là lỗi.
- **`make_beats.py` dùng cùng resolver vùng + vùng mặt như gate**: placement strict, không còn "least-overlap" (không có chỗ thì bỏ/di chuyển beat và log). `render.sh` có vòng autofix (<= 3 vòng, `scripts/autofix_overlaps.py`, log `out/autofix.json`), sau đó mới abort.
- **Text-behind tự kích hoạt** (trước đây không bao giờ): log mọi lần skip (cửa sổ ngắn / title-burst hay framed-focus chiếm / CTA / cắt) vào stderr + `_skips`; hiệu ứng trượt vào không còn bắt đầu ngoài khung.
- **Sửa ASR cho cả caption**: `textCleanup.asrFixes` (vô điều kiện: 'xửa từng' -> 'sửa từng', 'vắt triển' -> 'phát triển') + `contextFixes` (theo từ lân cận: 'claw' -> Claude gần code/anthropic/prompt; 'hấp' -> 'khớp' trong 'âm thanh hấp đến từng khung', 'hấp' -> 'hợp' trong 'kết hợp/phù hợp') áp cho words.json VÀ captions.json (`apply_glossary.py` chạy không cần glossary.txt). Rule theo ngữ cảnh: kiểm lại với audio.
- **Logo Claude/TikTok tự tải** (`brandLogos.autoFetch`, `fetch_logo.sh` có mirror unpkg).
- Giới hạn: một mặt chính; canvas == source (mask text-behind giả định cùng khung); `text_occlusion.py` không biết zoom nên mask được warp sang khung composition trước khi đo; cửa sổ text-behind phải nằm trong một đoạn EDL ổn định; concept ngoài bảng cần thêm dòng `concepts`.

## v4.3.1 NOTES (3 regressions fixed)

1. **Length**: `python3 scripts/make_edl.py --words ... --target-sec 60 --tol 2` iterates a speech budget (best whole sentences, duration-weighted score + `tighten.conceptBonus` for sentences that say an illustration concept) until the kept length is 58-62s - use the long raw, the pipeline finds the material.
2. **Icons**: the placement ladder in `references/illustrations.md` (big icon in a face-free slot -> shoulder/edge/above-caption slot -> smaller down to ~120px -> compact pill -> reframe the segment to wide). Never drop an icon only because the big size does not fit.
3. **Text-behind**: `tbsMinHoldSec` 0.8s + windows may span a jump cut with the same framing (`references/text-behind.md`). The CTA comment-box is never dropped by the face-aware shift (reframe to wide, else the least-overlap slot).

## v4.3.2 NOTES (hidden letters + icon vs text-behind)
- Every text-behind glyph must stay >= 70 % visible on every frame: `text_occlusion.py ... --max-glyph 0.30` (exit 5) in tbs_place, make_masks and the render gate. See references/text-behind.md "v4.3.2". A beat that cannot meet this AND mean occlusion >= 3 % is dropped to a plain headline (logged) - never ship a swallowed letter.
- An illustration never shares a concept (8 s window) or time with a text-behind beat; the text-behind wins (references/illustrations.md "v4.3.2").
