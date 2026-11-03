---
name: highlight-and-tighten
when: Load at pipeline steps 2-3 (transcribe cleanup, EDL / tighten, target length).
---

# Highlight + Tighten

Mục tiêu: từ raw dài/thô, chọn phần đáng giữ, cắt chết/lặp/ừm à, ra video có nhịp như tham chiếu. Độ dài ra do rubric quyết định (cửa sổ mềm 20-75s và 35-80% raw, `tighten.target`), KHÔNG ép bằng raw hay video tham chiếu.

## Pipeline (`scripts/make_edl.py`, yêu cầu probe.json đã passed)
1. `silencedetect` (-34 dB, >=0.35s) -> khoảng lặng.
2. RMS năng lượng theo cửa sổ (numpy) -> điểm energy 0-1.
3. Gom từ thành cụm (phrase) theo ngắt >=0.25s.
4. Loại filler đầu/cuối cụm (`tighten.fillers`: ờ, ừm, à, kiểu...). Filler đứng một mình = bỏ.
5. Take lặp: các cụm giống nhau >=0.72 (difflib) -> giữ **lần cuối**, ghi `repeat-take` vào dropped.
6. Chấm điểm rubric.
7. Chọn: giữ >= `keepAbove` .42, bỏ < `dropBelow` .30, vùng giữa lấp vào cho đủ cửa sổ mục tiêu.
8. Jump-cut: pad vào 0.04s, ra 0.08s, gộp nếu cách <0.18s, tách đoạn >7s tại điểm lặng, đoạn tối thiểu 0.7s.
9. Đảo hook: cụm điểm >=.70 trong 3s (`hook.maxHookSec`) được đưa lên đầu nếu raw không mở bằng hook. (`--no-hook-reorder` để tắt.)
10. Gán framing theo vòng (wide, mid, wide, mid, wide, tight, wide), đổi tối thiểu mỗi 4.5s, `punch` ở mỗi lần đổi.
11. Ghi `edl.json`, `captions.json` (trang theo `pageRules`), `beats.suggested.json`, `edl_report.md` (từng đoạn giữ/bỏ + lý do).

## Rubric (trọng số, tổng 1.0)
hookiness .22 (từ khóa gây tò mò, câu cảm thán, đầu video) - information .20 (số liệu, tên công cụ, hành động cụ thể) - energy .16 (RMS + tốc độ nói) - clarity .14 (không ừm à, câu trọn) - emotion .10 (cảm thán, nhấn) - novelty .10 (không trùng cụm khác) - payoff .08 (kết quả, CTA). Điểm là heuristic, **luôn đọc edl_report.md** và sửa tay nếu sai ngữ nghĩa.

## Nhịp tham chiếu (đã đo)
Khoảng nghỉ giữa các cụm nói chỉ 0.1-0.2s [M] -> `maxPauseKeepSec` 0.2; 3.2 từ/giây; ~3.7s/shot; 12 hard cut trong 48.6s. Raw người mới nói thường chậm hơn: kỳ vọng bỏ 20-65%.

## Cách dùng
```
python3 scripts/make_edl.py --words public/project/words.json            # mặc định: tighten + hook reorder
python3 scripts/make_edl.py --words ... --keep-all                         # chỉ cắt lặng/filler, không loại nội dung (video đã gọn như tham chiếu)
```
Sửa tay: sửa `edl.json` (srcIn/srcOut/framing/punch). Không cần sửa beats vì chúng ở thời gian nguồn.
Lưu ý: chạy trên chính video tham chiếu (đã gọn) với chế độ mặc định sẽ bỏ ~23% do `ratioOfRaw` - dùng `--keep-all`.

## Hard rules / commands / thresholds (v4.4)
- `python3 scripts/make_edl.py --words public/project/words.json --out public/project --target-sec 30 --tol 2` (`--out` is a DIRECTORY). Result must satisfy V02 `abs(duration - target) <= tol`.
- Read `edl_report.md` (every dropped part has a reason). Keep whole sentences; CTA kept (V16).
- Glossary: `Mai -> Mike` only when capitalised AND an AI-tool word is within the window (`style.config.json -> textCleanup.ambiguousWords.mai`: `requireCap`, `near` AI-tool words, `within` N words, `notNext`, optional `nameVote{enabled,minHits,markers}` = capitalised Mai followed by a subject marker at least `minHits` times; one hit is never enough); add per-video pairs to `public/project/glossary.txt`.
- Source keyframes: `scripts/ensure_keyframes.py` (run by `render.sh`) re-encodes the raw to a <= 1 s GOP; a long-GOP phone raw made a 41 s render take 9m44s (v4.3) vs ~2 min after.
