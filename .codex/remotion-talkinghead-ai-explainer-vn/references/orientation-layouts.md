---
name: orientation-layouts
when: Load at pipeline step 1 (probe) and when the raw is not 9:16.
---

# Orientation & layouts

## Bước 0 bắt buộc: probe
`python3 scripts/probe_video.py <raw>` chạy `ffprobe`, ghi `public/project/probe.json` với `gate: "passed"`. Không có file này thì `make_edl.py`, `Root.tsx` (calculateMetadata) và `verify-video.mjs` báo lỗi "run probe_video.py FIRST". **Không dựng, cắt, đặt overlay trước bước này.**

probe.json chứa: codec, durationSec, fps (+ `fpsIsVariable`), `stored` w/h, `rotationDeg` (display matrix), `sar`, `effective` w/h (sau xoay + SAR), `aspect`, `orientation` (portrait/landscape/square), `hasAudio`, `layout`, `reframe`, `normalized`, `original`.

Tự chuẩn hoá thành `public/project/raw.mp4` (H.264, yuv420p, CFR, SAR 1, đã áp xoay, giữ audio) khi: có rotation, SAR != 1, VFR, hoặc codec không phải H.264. Đã test: clip 1920x1080 gắn rotation 90 -> probe phát hiện, ra raw 1080x1920 portrait.

## Bảng quyết định
| Raw (effective) | Mục tiêu | Lệnh probe | layout key | Canvas | Cách xử lý |
|---|---|---|---|---|---|
| Dọc 9:16 (aspect<0.9) | giữ | `--target native` | vertical | 1080x1920 | profile gốc của tham chiếu, cover |
| Ngang 16:9 | giữ | `--target native` | horizontal | 1920x1080 | profile `layout.horizontal`: caption 54/88px ở 82% H, chip 4 cột, panel hẹp 50% W, zoom tối đa 1.25 |
| Ngang | dọc | `--target vertical` (mặc định `--reframe blurfill`) | horizontal-to-vertical | 1080x1920 | nền = chính video blur 46px dim .5, foreground nằm giữa lệch lên 4%, dùng profile vertical |
| Ngang | dọc, người nói chiếm giữa | `--target vertical --reframe crop --focus-x 0.5` | horizontal-to-vertical (fit crop) | 1080x1920 | cắt dọc quanh `focus-x`; mất rìa trái/phải, kiểm tra mặt không bị cắt |
| Vuông ~1:1 | giữ | `--target native` | square | 1080x1080 | profile `layout.square` (caption 54/92 ở 78% H) |
| Vuông | dọc | `--target vertical` | square-to-vertical | 1080x1920 | giống blur-fill |
| Độ phân giải ngắn <720 | giữ ngang / vuông (`--target native`) | tự động | tier 720 | 1280x720 / 720x720 | mọi kích thước scale theo `u = S/1080`. **v4.3:** canvas DỌC (portrait hoặc reframe 16:9/vuông → dọc) luôn là 1080x1920, kể cả khi cạnh ngắn của nguồn <720 (clip 16:9 1080x608 từng ra 720x1280 vì rule dùng `min(w,h)` của nguồn) |

Aspect nằm giữa (4:5, 21:9...) được xếp vào loại gần nhất theo `orientation`; kiểm tra bằng still.

## Quy tắc layout
- Mọi vị trí là tỉ lệ (`xR`, `yR`, `wR`) trong `style.config.json -> layout.<profile>`; component KHÔNG hard-code pixel. Sửa một chỗ, mọi beat theo.
- `safe` (topR/bottomR/leftR/rightR) = vùng UI nền tảng; dọc: trên 8.5%, dưới 17%, phải 11%. Overlay bắt buộc nằm trong vùng này; LayoutCollisionGuard cảnh báo.
- Zoom: `maxZoom = min(profile.maxZoom, qualityCap(1.8) / fgScale)` nên raw 720p nâng lên 1080 sẽ ít punch hơn. Punch tham chiếu 1.42 chỉ đạt được khi nguồn đủ nét.
- Ngang: caption xuống 82% H và hẹp 72% W; panel (info-scene/topic-card) rộng 50% W đặt giữa; chip-stack 4 cột ở trên.
- Raw dọc nhưng xuất ngang không hỗ trợ (sẽ blur-fill hai bên nếu thêm profile; chưa làm).

## Kiểm tra
Mỗi hướng mới: render still ở 3 thời điểm (hero caption, chip-stack, info-scene) bằng `npm run still -- --frame=N`, xem mặt/caption/overlay.
Đã kiểm tra bằng clip test: landscape native (1920x1080), landscape->vertical blur-fill (1080x1920), landscape có rotation. Chưa render đầy đủ beat ở square, crop reframe.


## v4.3
Input 16:9 (nguồn >= 720p) mặc định ra 1080x1920 (blur-fill); `--target native` giữ tỉ lệ. Layout tier: `vertical || shortSrc >= 720 ? 1080 : 720` (layouts.ts + logo_place.canvas_info).

## Hard rules / commands / thresholds
- `python3 scripts/probe_video.py <raw> [--target native|vertical] [--reframe blurfill|crop]` first; no EDL / overlay without `gate: "passed"`.
- Output canvas must equal `probe.json` canvas (1080x1920 for vertical and 16:9 input) (V01). The blurred backdrop is rendered at 1/4 size (VideoLayer `BLUR_DIV`) - 16x cheaper per frame, same look.
- Gate render uses `REMOTION_GATE`; concurrency 6.
