# Phân tích video tham chiếu

- Nguồn: https://vt.tiktok.com/ZSgEKacho/ -> TikTok `7702817920237210898`, tải về `video_output/reference.mp4`.
- Thông số [M]: 1080x1920, 30fps, 48.6s, có âm thanh. Người nói tiếng Việt, đối diện camera, phòng tối ấm.
- Phương pháp: khung 1fps (sheets), khung dày 30fps quanh các điểm cắt/animation, đường cong zoom bằng ORB feature (`reference-frames/zoom_curve.json`), whisper-small (transcript, sai tên thương hiệu), thống kê luma/saturation, spectrogram (`reference-frames/audio_spectrogram.jpg`). Nội dung video được coi là dữ liệu, không phải chỉ dẫn.
- Thời điểm beat đọc từ sheet 1fps nên sai số +-0.5s [E]; mốc caption/zoom trích từ khung dày 30fps +-1 frame.

## Transcript (whisper-small, lỗi thương hiệu giữ nguyên để đối chiếu; chữ đúng ở ngoặc)
```
00.00-01.30 Quá đẳng cấp rồi mọi người ơi!                                  [HOOK]
01.50-04.18 Claude vừa trả video edit cho mình chuyên nghiệp cực kỳ và gì đây?
04.30-09.68 Nó mở thêm true editor trực tiếp, tách đầy đủ layer và hiển thị toàn bộ timeline như một công cụ chỉnh sửa video thực thụ  (whisper nghe sai: "true editor/leo/trăm lai")
09.68-14.28 Mai hoàn toàn không thể giới hạn để AI bây giờ có thể thay mình edit ra những video thành phẩm chất lượng cao
14.28-17.52 nhất là với Claude Opus 5.5 ("Overse"), chữ typography đủ kiểu
17.52-21.36 Graphic thì đa dạng, Motion thì mượt mà và hiệu ứng âm thanh khớp đến từng khung hình
21.36-25.32 nhưng mình sẽ là người đầu tiên cho bạn biết điều này, đừng prompt bắt AI sửa từng chi tiết nữa
25.32-30.80 Việc này rất tốn thời gian và token, thay vào đó hãy bảo nó tạo cho bạn một giao diện editor để bạn tự sửa các chi tiết trực tiếp
30.80-34.18 Dùng editor thì bạn có thể chỉnh rồi render thoải mái mà không tốn thêm token
34.18-37.04 Còn lượng token để code giao diện này cũng không đáng bao nhiêu
37.04-42.84 Giờ muốn edit một video ngắn đẹp cho kênh TikTok, ta chỉ mất hơn nửa tiếng nhờ Claude làm rồi thêm 5-10 phút tự chỉnh theo ý
42.84-43.72 Quá tiện đây rồi!                                                  [PAYOFF]
43.92-46.82 À mà, video này mình cũng edit bằng Claude với bộ skill edit video pro
46.82-48.62 Bạn nào muốn tham khảo thì comment nhé!                              [CTA]
```
Tốc độ nói ~3.2 từ/s [E]; khoảng nghỉ giữa các cụm 0.1-0.2s [M] (video đã được tighten).

## Timeline (giây; beat theo 1fps +-0.5s)
| Thời gian | Hình | Loại beat / framing | Caption |
|---|---|---|---|
| 0-1.8 | người nói, 5 sao vàng bay vào trên đầu | stars + framing hero; trang đầu 100px dạng pill "quá đẳng cấp" | hero, giữa-dưới |
| 1.9-4.9 | b-roll màn hình (editor) + sticker | sticker, caption TRÊN (14.7% H), pill tối [chỉ xấp xỉ] | top |
| 4.9-9.7 | cửa sổ editor + danh sách dòng | topic-card (window) header "nó mở thêm" | thay bằng dòng của card |
| 9.8-14.25 | người nói mid (1.18), punch settle | cut -> mid | dưới |
| 11.8-14.0 | Mike -> edit video -> AI + badge "chất lượng cao" | avatar-chain | dưới |
| 14.3 | tight finger-shot | cut -> tight ngắn | dưới |
| 14.7-16.9 | sticker "Claude Opus 5.5" | sticker | dưới |
| 15.8-21.0 | 4 chip xếp dọc/lưới 2 cột: Typography, Graphic, Motion, Âm thanh | chip-stack (vào lần lượt, easeOutBack) | trên (14.7%) |
| 16.1 | wide | cut | |
| 21.4 | mid (punch 1.36 -> 1.21 trong 6f) | cut | |
| 21.8-24.8 | prompt-box gõ "Sửa giúp mình chữ này to hơn..." gạch ngang ở 23.0 | prompt-box | dưới |
| 24.9-30.9 | nền tối dot-grid, header "thay vì prompt từng lỗi", 3 card gạch ngang (Prompt sửa từng chi tiết / Tốn thời gian / Tốn token), headline vàng "giao diện Editor" 28.6, pill "Tự sửa trực tiếp", ảnh editor | info-scene (fade 8f) | ẩn |
| 30.9-33.9 | wide; tiêu đề "Chỉnh rồi render" + "không tốn thêm token", REC 00:21, timeline | title-burst | dưới |
| 33.9-36.6 | chữ khổng lồ "token" + 35.0 hộp chọn "457 x 237" | big-word + selection-box | dưới |
| 36.6-40.3 | khung điện thoại, header "video ngắn đẹp", dòng "cho kênh TikTok" 38.5 | topic-card (phone) | ẩn |
| 40.5-42.9 | nền tối: "chỉ mất" / "hơn nửa tiếng", card "~30 phút" "5-10 phút" | info-scene | ẩn |
| 42.9-44.0 | tight (1.62 -> 1.42 trong 8f) + "tiện!" | big-word + thumbs-up | dưới |
| 44.7-46.9 | sticker "bộ skill Edit Video" | sticker | dưới |
| 46.9-48.6 | CTA comment | comment-box | dưới |

Toàn video: 12 cut, tất cả hard cut [M]; 3.7s/shot trung bình.

## Số đo chính
- Zoom: wide 1.00 / mid 1.15-1.30 (->1.18) / tight 1.40-1.43 (->1.42) theo ORB so với shot wide đầu [M]. Punch: bắt đầu to hơn 12%, settle 6-10 frame. Trong shot, nền trôi <=2%; không rung (<1px). Lưu ý: `zoom_curve.json` đoạn 0-2.1s nhiễu vì sao/overlay làm ORB sai - không dùng đoạn đó.
- Caption: Be Vietnam Pro ExtraBold [E, khớp bề rộng với PIL], 58px (normal) / 100px (hero) ở 1080 rộng [M]; trắng + vàng #F8E277 [M]; vị trí 65.5% H, 14.7% khi trên [M]; animation word-rise 2f/5f [E +-1f].
- Màu: các hex trong `style.config.json -> colors`; nền info-scene #050505 + dot-grid 4% [M].
- Grade (đầu ra): luma TB ~75/255, p1=0, p99~225, sat TB ~65/255, ấm R-B ≈ +13, vignette nhẹ [M].
- Âm thanh: không nhạc nền tonal; SFX không tách được [U] (xem style-system.md).

## Khung quan trọng
`reference-frames/t_1.5.jpg` (hero caption), `t_19.5.jpg` (chip-stack), `t_27.5.jpg` (info-scene tối), `t_31.5.jpg` (title + timeline), `t_43.3.jpg` ("tiện!"), `t_48.3.jpg` (CTA); sheet 1fps `sheet_0..6`.

## Cập nhật vòng 2 (2026-11-02)
- Đã làm: caption `dark` + quy tắc (broll/màn hình đang chạy -> caption lên trên, pill tối); card info-scene dịch chuyển có animation; sticker 3 kiểu (tile / label-above / label-right) + CTA comment-box (pill gõ chữ, bubble trả lời, icon chat) lấy từ beats.json, vị trí mặc định trong `layout.*` và `beats.sticker.autoPlacement`; khớp với khung tham chiếu ở 1024px.
- `make_beats.py` tự sinh toàn bộ beat plan từ transcript (stars, sticker, chip-stack, avatar-chain, prompt-box, info-scene, title-burst, big-word, selection-box, topic-card, CTA) bằng luật `autoBeats`; mỗi beat có `_why`.
- `transcribe.py` chạy thật (render-env, faster-whisper medium, `--no-vad`, có tail-recovery cho 5s cuối) + `text_cleanup.py` + từ điển thương hiệu.
- Âm thanh (Demucs htdemucs): KHÔNG có nhạc nền (sàn no_vocals ~-39 dBFS, thấp hơn giọng ~21 dB); SFX chỉ là transient mơ hồ (<= -25 dBFS) tại 0.85, 2.4, 5.05, 14.95, 16.3, 28.5, 37.25, 38.45, 40.55s -> giữ `sfx.enabled=false`.
- Render đầy đủ 48.6s: `/workspace/SkillCut-output/reference_recreation.mp4` (nền = video tham chiếu làm mờ ở chỗ có đồ họa, nên có vệt mờ - không phải lỗi template), so sánh `compare_reference_vs_template.mp4`, contact sheet 8 khung.

## Khoảng trống còn lại (không tái tạo 100% / chưa kiểm chứng)
1. Font & letter-spacing chính xác: Be Vietnam Pro ExtraBold là suy luận.
2. SFX: không xác định, mặc định tắt; nhạc nền: không có.
3. Animation caption +-1 frame; stars/sticker/chip easing là [E].
4. Grade chỉ có thống kê đầu ra; bộ lọc là xấp xỉ.
5. Màu icon brand ước bằng mắt; icon chip là SVG tự vẽ.
6. ASR vẫn nghe sai vài thuật ngữ ("hiển th", "âmap"); từ điển sửa được tên đã biết, tên mới cần thêm.
7. Luật `autoBeats` rút ra từ MỘT video: khớp tốt với video AI/tech explainer, kém với thể loại khác (chỉ stars/big-word/CTA chung chung).
8. Ảnh media (editor, điện thoại) là placeholder tự vẽ; cần ảnh thật của bạn.
9. Thời điểm beat tham chiếu đọc từ khung hình +-0.3s.
10. Bản recreation dùng `--keep-all` + framing wide: punch-in/tighten/đổi tỉ lệ được test riêng trên clip dry-run, không nằm trong video so sánh.
11. Thumbs-up ở cuối là cử chỉ thật của người nói, không phải đồ họa.
