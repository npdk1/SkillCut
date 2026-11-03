---
name: style-system
when: Load at pipeline steps 2 and 6 (captions) and before editing any look number in style.config.json.
---

# Style system (đọc từ style.config.json)

Nguồn: video tham chiếu 1080x1920, 30fps, 48.6s. [M]=đo, [E]=ước, [U]=không đo được.

## Màu
vàng nhấn `#F8E277` [M] (chữ vàng + pill + viền chip), chữ pill `#0D0F0F`, trắng `#FFFFFF`, chip `#1F2021` viền vàng 75%, info-card `#241F1B` viền trắng 10%, nền tối `#050505` + glow `#26211C` + dot-grid trắng 4%, gạch ngang card `#F5E7A7`, gạch prompt-box `#E5384F` [E], màu cam brand `#D97757` [E - thay bằng icon thật của bạn].

## Font
Be Vietnam Pro 800 (heavy) / 700 / 500, letter-spacing -0.02em [E]. Cỡ chữ ở 1080 rộng: normal 58, hero 100, sub 44. Tất cả cỡ khác nhân theo `layout[x]` (xem orientation-layouts.md), không hard-code trong component.

## Caption
- Mỗi trang tối đa 2 dòng x 4 chữ, <=22 ký tự/dòng, 0.8-3.4s/trang, ngắt khi gap >=0.25s.
- Dòng 1 trắng, dòng 2 vàng (hoặc pill vàng với từ khóa). Trang 0-1.3s dùng cỡ hero dạng pill.
- Animation: word-rise, mỗi chữ trễ 2 frame, dài 5 frame, trồi 0.4em từ dưới lên trong vùng clip đáy, fade 3 frame [E ±1f]. Trang cũ biến mất 1-2 frame (cut). KHÔNG pop/scale.
- Bóng: blur 10, offsetY 4, alpha .55. Không viền chữ.
- Vị trí: tâm dòng 1 ở 65.5% chiều cao khi người nói chiếm khung; 14.7% khi vùng dưới có đồ họa (`beats.captionAnchor`). Caption bị ẩn khi đang có info-scene/topic-card (header đã là chữ).

## Framing / chuyển động
Ba mức zoom theo từng shot: wide 1.0, mid 1.18, tight 1.42 [M]. Mỗi lần đổi mức, shot mới bắt đầu to hơn 12% rồi settle trong 8 frame easeOutCubic [M]. Vòng lặp: wide, mid, wide, mid, wide, tight, wide; đổi mỗi 4.5-9s, shot >=2s. Không drift, không rung [M]. Với raw chất lượng thấp, zoom bị giới hạn bởi `qualityCap` (1.8) và `layout.maxZoom`.

## Cắt
Chỉ hard cut [M]. Scene tối fade-in 8 frame trên frame cuối đã blur. Không SFX chuyển cảnh trừ khi bật.

## Grade
Áp lên footage người nói: brightness .96, contrast 1.06, saturate 1.05, sepia .06, vignette .12 [E, từ thống kê output: luma TB 75/255, p1=0, p99~225, ấm R-B≈+13]. Tắt bằng `grade.enabled=false` nếu raw của bạn đã grade.

## Âm thanh
Giữ audio raw nguyên. SFX/nhạc [U]: spectrogram không có lớp nhạc nền; vài tiếng "ping" ứng viên (0.7-1.95s sao, 14.7-15.7s tile Claude, 43.2-44.1s, 45.3-45.8s, 48.3-48.5s) nhưng có thể là hài giọng nói. Mặc định TẮT. Khi bật (`audio.sfx.enabled`), cue đặt theo quy tắc (whoosh khi đổi framing -3f, pop khi beat vào, ping cho stars/sticker/big-word, type cho prompt-box/comment-box), KHÔNG phải số đo. Nhạc: để file ở `public/sfx/music.mp3`, volume gợi ý .08, duck .04 dưới giọng (điển hình, chưa đo).

## Hard rules / commands / thresholds (v4.4)
- Captions: `caption.background.enabled = false` (no pill / box / blur / white panel); readability = `caption.stroke.widthPx` (>= 6, default 8) + soft shadow (V05). Line 1 white, line 2 punch phrase yellow text.
- All numbers come from `style.config.json`; `verify.*` holds the V-rule thresholds. Never hard-code a style number in src/.
- v4.5: a leftover subtitle-removal patch in the raw counts as a box behind captions (V23): re-inpaint it (`references/quality-control.md` v4.5), do not rely on the caption block to hide it.
