---
name: feedback-learning
when: Load when the CUSTOMER comments after delivery ("caption too big", "cut too hard"). Not the verify loop (that is feedback.md).
---

# Học từ phản hồi

Khi người dùng nhận xét ("caption to quá", "cắt quá gắt", "thiếu sticker"), chỉ sửa **một file**: `style.config.json` (hoặc `tighten.*`). Quy trình:

1. Ghi phản hồi vào `feedback.log.md` (ngày, câu nguyên văn, key đã đổi, giá trị cũ -> mới).
2. Đổi key tương ứng:
   - caption to/nhỏ -> `layout.<profile>.caption.normal|hero`
   - cắt gắt/lỏng -> `tighten.silence.*`, `jumpCut.*`, `rubric.keepAbove`
   - zoom nhiều/ít -> `framing.levels`, `framing.punch.overshoot`, `layout.*.maxZoom`
   - màu/grade -> `colors.*`, `grade.*`
   - thêm/bớt hiệu ứng -> `beats.json` (không phải config)
3. Render lại đúng vài still/10 giây bị phàn nàn rồi mới render đầy đủ.
4. Nếu phản hồi lặp lại >=2 video, nâng thành mặc định trong `style.config.json` và ghi lý do vào `_note` của key đó. Đánh dấu `[M]` cho giá trị mới đo, `[E]` cho giá trị theo cảm nhận người dùng.
5. Không sửa component để đổi số; nếu cần thêm tham số thì thêm vào config rồi đọc qua `assets/style.ts`.

## Hard rules / commands / thresholds
- Change ONE file only (`style.config.json`, or `tighten.*`), re-render with `scripts/render.sh`, re-run `verify_rules.py` (references/verified.md), deliver only on all-pass.
- Customer feedback never overrides a V-rule (e.g. "put a box behind captions" conflicts with V05: report it, do not silently comply).
