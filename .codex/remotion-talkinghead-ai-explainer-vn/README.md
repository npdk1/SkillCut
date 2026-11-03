# Remotion Talking-head AI Explainer VN

Skill dựng video talking-head tiếng Việt kiểu AI/tech explainer bằng Remotion: tự chọn highlight từ transcript, cắt khoảng lặng/ừm à/take lặp thành EDL, caption word-rise vàng–trắng không nền, punch-in wide/mid/tight và bộ beat text-behind, chip-stack, prompt-box, info-card, CTA comment.

## Showcase: Original vs After

Hai video so sánh dưới đây cùng dài khoảng 30 giây (MP4 có âm thanh).

<table>
  <tr>
    <th width="50%">Original</th>
    <th width="50%">After · New Skill</th>
  </tr>
  <tr>
    <td align="center">
      <video src="https://github.com/user-attachments/assets/c989b233-cf42-4c08-b754-017b36919094" controls></video>
    </td>
    <td align="center">
      <video src="https://github.com/user-attachments/assets/85859d9d-cbd7-48df-958d-bf4aeafb2c22" controls></video>
    </td>
  </tr>
</table>

## Thiết kế được áp dụng

- Highlight & Tighten: chấm điểm từng câu theo hook, giá trị và kết; cắt khoảng lặng, ừm à, take lặp; độ dài video ra là kết quả của các đoạn giữ lại, chỉ ép `--target-sec ±2` khi cần.
- Caption Word-rise: `Be Vietnam Pro` 800, trắng + vàng `#F8E277`, từ đang đọc trồi 0.4em trong 5 frame, tối đa 2 dòng × 4 chữ, stroke 8 px + bóng mềm, tuyệt đối không pill/hộp/blur.
- Punch-in 3 mức framing: wide 1.0 / mid 1.18 / tight 1.42; mỗi lần đổi mức punch 1.12x rồi settle 8 frame easeOutCubic, chỉ hard cut, không push-in liên tục.
- Text-behind-speaker: chữ lớn nằm sau người nói, mask person-only, chỉ che 3–10%, mỗi glyph ≥ 70% hiện và đọc được ≥ 90%.
- Hệ beat đa dạng: stars, sticker, chip-stack, avatar-chain, prompt-box, title-burst REC + timeline, info-scene/topic-card, framed-focus và comment-box CTA.
- Icon minh họa + logo thương hiệu thật: Lucide/Tabler/Phosphor và Simple Icons/svgl/Wikimedia; tối đa 4 icon/30 giây, cách nhau ≥ 5 giây, đặt theo vùng trống quanh mặt người nói.
- Chống đè và face-aware: LayoutCollisionGuard + autofix tối đa 3 vòng với ngưỡng 6 px, kiểm caption trên từng frame render.
- Mọi con số phong cách nằm trong `style.config.json`; probe quyết định dọc 9:16, ngang 16:9 hay vuông, composition lấy width/height/fps từ `probe.json`.
- QC tự động: `render.sh` gate overlap + mask + text-behind, rồi `verify-video.mjs` và `verify_rules.py` V01–V23, tối đa 3 vòng sửa trước khi giao.

## Cấu trúc skill

- `SKILL.md`: tổng quan, các ghi chú phiên bản và quy trình chính.
- `AGENTS.md`: pipeline 16 bước bắt buộc và danh sách hard rules.
- `references/verified.md`: bộ V-rule V01–V23 kiểm được bằng máy.
- `references/feedback.md`: mẫu báo cáo từng vòng và `blockers.md`.
- `references/text-behind.md`: mask người, đo occlusion và ngưỡng đọc được của chữ sau lưng.
- `references/illustrations.md`, `references/brand-logos.md`: chọn icon/logo thật, mật độ và vị trí theo vùng trống.
- `references/highlight-and-tighten.md`, `references/orientation-layouts.md`: rubric cắt highlight và quyết định tỉ lệ khung.
- `references/style-system.md`, `references/scene-architecture.md`, `references/quality-control.md`: typography, layer stack, gate QC.
- `assets/`: types, remap EDL, layouts, zones, font và model face detection YuNet.
- `src/`: Composition, Root (calculateMetadata) và các component VideoLayer, Captions, Beats, Icons, Sfx, LayoutCollisionGuard.
- `scripts/`: probe, transcribe, make_edl, make_beats, make_masks, tbs_place, logo_place, render.sh, verify-video.mjs.
- `examples/`: timeline tham chiếu (words, captions, beats, edl, probe).
- `style.config.json`: toàn bộ thông số phong cách trong một file.
- `video_output/original.mp4`: footage gốc 30 giây, có tiếng.
- `video_output/after.mp4`: footage sau khi áp dụng skill, khoảng 30 giây, có tiếng.
