---
name: scene-architecture
when: Load at pipeline step 5 (beats) and when adding / moving an overlay.
---

# Kiến trúc scene

## Stack (dưới -> trên)
1. **VideoLayer**: raw.mp4 qua EDL, framing + punch + grade (`OffthreadVideo`, mỗi segment một `Sequence`, `startFrom` = srcIn).
2. **Beats under**: `broll`, `info-scene`, `topic-card` (phủ nền/che người nói).
3. **Beats over**: `stars`, `sticker`, `avatar-chain`, `chip-stack`, `prompt-box`, `title-burst`, `big-word`, `selection-box`, `comment-box`.
4. **Captions**: đọc `captions.json`, bỏ qua trang nằm dưới info-scene/topic-card.
5. **Sfx** (tắt mặc định).
6. **LayoutCollisionGuard**: chỉ trong Studio; cảnh báo khi overlay đè vùng `safe` hoặc đè caption.

## Dữ liệu dự án (public/project/, thời gian theo RAW = source time)
- `probe.json` (gate) - `edl.json` (segments, srcIn/srcOut) - `captions.json` - `beats.json` - `raw.mp4` + ảnh media.
- Tất cả thời gian trong beats/captions là **thời gian nguồn**. `assets/remap.ts` (`buildTimeline`, `srcToOutFrame`, `mapInterval`) đổi sang frame đầu ra; beat bắt đầu/kết thúc trong đoạn bị cắt sẽ tự kẹp vào đoạn giữ lại gần nhất. Vì vậy sửa EDL không cần dời tay từng beat.
- `Root.tsx -> calculateMetadata` tính width/height/fps từ probe, durationInFrames = tổng các segment.

## Beats (type -> trường)
| type | trường chính | ví dụ trong tham chiếu |
|---|---|---|
| stars | t0,t1 | 0-1.8s năm sao vàng trên hero caption |
| sticker | label?, side | 1.9-4.9; 14.7-16.9 "Claude Opus 5.5"; 44.7-46.9 |
| topic-card | header, media{src,kind window/phone}, lines[{t,text,pill,hl,slot,until}] | 4.9-9.7 cửa sổ editor; 36.6-40.3 điện thoại |
| avatar-chain | left, chip, right, badge | 11.8-14.0 "Mike -> edit video -> AI" |
| chip-stack | items[{t,title,sub,icon}] | 15.8-21.0 Typography/Graphic/Motion/Âm thanh |
| prompt-box | text, strikeAt | 21.8-24.8 gõ prompt rồi gạch ngang |
| info-scene | header, headline, cards[{t,text,sub,strike,icon}], pill, media | 24.9-30.9; 40.3-42.9 nền tối dot-grid; headline vàng ~2.05x header, hiện ngay dưới header lúc 28.45s / 40.5s (headline.t = từ đầu - headlineLeadSec) |
| title-burst | title, sub, rec, timeline | 30.9-33.9 "Chỉnh rồi render" + timeline |
| big-word | text | 33.9-36.6 "token"; 42.9-44 "tiện!" |
| selection-box | label, size | 35.0-36.6 hộp chọn 457 x 237 |
| comment-box | text | 46.9-48.6 CTA |

Mẫu đầy đủ: `examples/reference.beats.json`. Gợi ý tự động: `beats.suggested.json` (hook -> stars; từ khóa payoff -> big-word; cuối -> comment-box).

## Quy tắc đặt beat
- Hook (0-1.3s): hero caption + stars. Không đặt gì khác.
- Mỗi 3s có ít nhất một thay đổi thị giác (đổi framing hoặc beat mới).
- Chỉ một beat "to" (info-scene/topic-card/title-burst/big-word) cùng lúc; chip/sticker/selection-box có thể chồng lên người nói nhưng tránh vùng mặt (`layout.safe`).
- Payoff: big-word 1 từ + sticker/thumb-up. Outro: sticker thương hiệu + comment-box 1.5-2s, không fade.

## Hard rules / commands / thresholds (v4.4)
- Framed-focus (phone / app window): at most `max(1, floor(duration_sec/30))` per video (1 for 30 s, 2 for 60 s), never adjacent (gap >= `autoBeats.framedFocus.minGapSec` 15 s) (V14). Headline = stroked yellow text (`info.pillFilled=false`), no filled pill (V05).
- Layout collisions: 6 px gate (`check_overlaps.mjs`), CTA comment-box never dropped.
