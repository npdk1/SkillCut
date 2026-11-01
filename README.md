<div align="center">

<img src="./assets/logo.svg" alt="SkillCut" width="96" height="96" />

# SkillCut

**Templates & skill files that turn raw footage into million-view short clips — handed straight to your AI.**

[![MIT License](https://img.shields.io/badge/license-MIT-22c55e?style=flat-square)](./LICENSE)
[![AI Ready](https://img.shields.io/badge/AI-Claude%20%7C%20Codex%20%7C%20Antigravity-0ea5e9?style=flat-square)](#-works-with-your-ai)
[![Language](https://img.shields.io/badge/docs-EN%20%7C%20VI-a855f7?style=flat-square)](#-tiếng-việt)
[![Live Demo](https://img.shields.io/badge/demo-index.html-f59e0b?style=flat-square)](./index.html)

[Live landing page](./index.html) · [Skill library](#-skill-library) · [Quick start](#-quick-start) · [Tiếng Việt](#-tiếng-việt)

</div>

---

## What is SkillCut?

SkillCut is a **library of video-editing templates and skill files for AI assistants** — not an editing app, and not a framework to learn.

You hand your AI three things:

1. the raw footage,
2. the subtitle file (`.srt` / `.txt`),
3. the skill file for the style you want.

You get back a finished **9:16 clip at 4K 60fps**: silence trimmed, karaoke captions burned in, motion and rhythm already applied.

---

## Before / After

Same raw footage. The first clip is untouched; the second was cut by SkillCut.

### Original — raw, unedited

<video src="https://github.com/user-attachments/assets/97c8308d-15a9-43be-83d9-f1db0beb2747" controls muted loop></video>

Uncut pauses, uneven audio, no captions, no rhythm.

### After SkillCut — 8.5s of silence removed

<video src="https://github.com/user-attachments/assets/5c9b257f-e231-416c-8c22-bd231318a648" controls muted loop></video>

Bare karaoke captions, step badges, on-beat cuts, 4K 60fps.

> Local copies live in [`assets/`](./assets) (`original.mp4`, `after.mp4`).

---

## What the skills actually do

| Capability | What changes in the output |
|---|---|
| **VAD silence cutting** | Voice Activity Detection finds every pause and trims it — 100% automatic |
| **Bare karaoke captions** | Word-level highlighting, outlined so it never covers the subject |
| **Step badges & insights** | "Step 1: Prep", "Pro tip…" tagged automatically at the right cue |
| **Narrative motion** | Speed-ramp, whip-pan, punch-in, dolly, auto-zoom — chosen by the skill |
| **Music ducking** | Lofi / bed music drops under the voice without a manual keyframe |
| **4K 60fps export** | Ready to post, no re-edit pass |

---

## Skill library

| Skill | Industry | Motion signature |
|---|---|---|
| [`good-skills/remotion-food-short-vn`](./good-skills/remotion-food-short-vn) | Food & F&B | Macro shots + fast cuts, bare yellow captions |
| [`good-skills/remotion-house-review-vn`](./good-skills/remotion-house-review-vn) | Real estate / house tours | Seamless fly-through + 3D floor plan |
| [`.codex/skills/seecut-vn`](./.codex/skills/seecut-vn) | Talking-head / social | Motion cards, proof boards, layered captions |

Each skill is a **markdown file**. Read it, edit it, or write your own — the folder is the product.

### Other industries on the roadmap

Travel (speed-ramp on the bass) · Study (Pomodoro timer, split-screen) · Education (kinetic diagrams)
· Architecture (CAD dimension lines, editorial grade) · Tech reviews (neon spec sheets).

---

## Quick start

```bash
git clone https://github.com/npdk1/SkillCut.git
cd SkillCut
```

Then either:

- **See the demo** — open [`index.html`](./index.html) in a browser (no build step, no dependencies).
- **Use a skill** — point your AI assistant at the folder, e.g.:

```text
Read good-skills/remotion-food-short-vn/SKILL.md and build a 9:16 clip
from ./raw/garlic-noodles.mp4 with ./raw/garlic-noodles.srt
```

<details>
<summary>Works with any AI assistant</summary>

- **Claude Code** — load the skill into the session and hand over the footage + `.srt`.
- **Codex (OpenAI)** — reads the skill, builds the timeline, exports with your preset.
- **Antigravity (Google)** — pick an industry template, send footage and subtitles.

Any assistant that can read a skill file works. No editing software required.

</details>

---

## Project structure

```text
SkillCut/
├── index.html                                  # product landing page (EN / VI, dark / light)
├── assets/
│   ├── original.mp4                            # raw footage used in the comparison
│   └── after.mp4                               # SkillCut output
├── good-skills/
│   ├── remotion-food-short-vn/                 # food / F&B skill
│   └── remotion-house-review-vn/               # house tour / real estate skill
├── .codex/skills/seecut-vn/                    # talking-head social skill (VI port)
├── remotion-edit/                              # reference composition
├── remotion-house-review/                      # reference composition
└── LICENSE
```

---

## Contributing

New skill presets are the most useful contribution.

1. Copy an existing skill folder and rename it: `your-industry-vn`.
2. Rewrite `SKILL.md` — description, when to use it, motion rules, caption rules, QC checklist.
3. Add **one** before/after sample (or a frame sheet) so reviewers can judge the look.
4. Open a pull request describing the industry and the motion signature.

---

## License

Released under the **MIT License** — free for personal and commercial use, modification and redistribution.
See [LICENSE](./LICENSE).

---

<div align="center">

## 🇻🇳 Tiếng Việt

</div>

**SkillCut** là kho **template và skill dựng video** để giao cho trợ lý A.I làm thay bạn. Không phải phần mềm dựng phim, không phải framework cần học.

Bạn đưa cho A.I ba thứ: **video thô**, **file phụ đề** (`.srt` / `.txt`), và **file skill** ứng với phong cách bạn muốn. Nhận về clip dọc **9:16, 4K 60fps** đã cắt sạch khoảng lặng, phụ đề karaoke không nền và motion theo đúng ngành.

### Kho skill hiện có

| Skill | Ngành | Chuyển động đặc trưng |
|---|---|---|
| `remotion-food-short-vn` | Ẩm thực & F&B | Macro + nhịp cắt nhanh, phụ đề vàng không nền |
| `remotion-house-review-vn` | Bất động sản / tour nhà | Flycam liền mạch + floor-plan 3D |
| `seecut-vn` | Talking-head / mạng xã hội | Motion card, bảng chứng thực, chữ nhiều lớp |

Các ngành đang mở rộng: Du lịch (speed-ramp theo nhịp bass), Học tập (đồng hồ Pomodoro, split-screen), Giáo dục (diagram vẽ nét), Kiến trúc (đường CAD, tông tạp chí), Công nghệ (spec-sheet neon).

### Bắt đầu

```bash
git clone https://github.com/npdk1/SkillCut.git
cd SkillCut
```

- **Xem demo:** mở [`index.html`](./index.html) bằng trình duyệt — không cần build, không cần cài gì.
- **Dùng skill:** trỏ trợ lý A.I vào thư mục skill, ví dụ:

```text
Đọc good-skills/remotion-food-short-vn/SKILL.md và dựng clip 9:16
từ ./raw/garlic-noodles.mp4 với ./raw/garlic-noodles.srt
```

### Đóng góp

1. Copy một thư mục skill có sẵn, đổi tên theo ngành: `ten-nganh-vn`.
2. Viết lại `SKILL.md`: mô tả, khi nào dùng, quy tắc motion, quy tắc phụ đề, checklist QC.
3. Thêm **một** mẫu before/after (hoặc frame sheet) để người review đánh giá được phong cách.
4. Mở pull request mô tả ngành và chuyển động đặc trưng.

### Giấy phép

Phát hành theo **MIT License** — miễn phí cho cả mục đích cá nhân và thương mại, được sửa và phân phối lại. Xem [LICENSE](./LICENSE).

<div align="center">

Made by [npdk1](https://github.com/npdk1)

</div>