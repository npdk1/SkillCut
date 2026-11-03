# HaiGiang Auto Edit CapCut

> Skill cộng đồng đóng góp từ kênh YouTube **[Hai Giang](https://www.youtube.com/@haigiangvideo)** — video hướng dẫn: **[AI không chỉ xuất clip sẵn nữa, nó dựng thẳng timeline CapCut](https://www.youtube.com/watch?v=ezhxedVFbrs)** (9:18, 23/10/2026).

Skill giúp AI (Claude Desktop, Codex, Antigravity...) **dựng thẳng vào dự án CapCut bản máy tính**: kịch bản, lồng tiếng, ảnh minh hoạ, cắt cảnh, zoom, nhạc nền, hiệu ứng âm thanh và phụ đề — tất cả nằm trên timeline thật, từng lớp, mở CapCut lên sửa tay tiếp như bình thường.

Điểm khác biệt so với "AI xuất clip sẵn": đầu ra không phải một file video đóng cứng, mà là **project CapCut đầy đủ layer** để bạn tiếp tục sáng tạo.

## Quy trình 5 bước (theo video)

| Bước | Việc | Ai làm |
|---|---|---|
| 1 | **Viết kịch bản** — chốt nội dung, nhịp cảnh trước khi làm gì khác | Claude |
| 2 | **Lồng tiếng** — chọn giọng, nghe thử, tải file | Claude + connector (video dùng ElevenLabs; skill này dùng giọng Higgsfield) |
| 3 | **Sửa mốc thời gian theo lồng tiếng** — dò khoảng lặng, khớp từng cảnh với câu thoại | Claude |
| 4 | **Tạo ảnh minh hoạ** — tạo ảnh tham chiếu khoá nhân vật/bối cảnh, rồi tạo cả bộ ảnh | Claude + Higgsfield |
| 5 | **Dựng trong CapCut** — cắt cảnh, zoom, nhạc, SFX, phụ đề, ghi thẳng vào project | Claude |

Mỗi bước nên có **điểm dừng để duyệt**. Cho AI chạy một mạch từ đầu đến cuối thì sai ở kịch bản sẽ kéo theo toàn bộ phần sau.

## Làm được gì

| Nhóm | Chi tiết |
|---|---|
| **Định dạng** | 16:9 cho YouTube, 9:16 cho TikTok / Reels / Shorts |
| **Ngôn ngữ** | Tiếng Anh và tiếng Việt, phụ đề dùng font Be Vietnam Pro đủ dấu |
| **Kịch bản** | Có nghiên cứu nguồn, hook 10–15 giây đầu (9:16: 2 giây đầu), câu ngắn, chia cảnh theo nhịp |
| **Lồng tiếng** | Chọn giọng có preview, tạo theo từng cảnh, ghép thành một file, canh đúng độ dài |
| **Canh thời gian** | Whisper lấy mốc từng từ; không có Whisper thì canh theo khoảng lặng (sai số ~0,2 giây) |
| **Hình ảnh** | Ảnh tham chiếu giữ nhân vật nhất quán, prompt từng cảnh, kiểm tra contact sheet, retake ảnh lỗi |
| **Dựng CapCut** | Cắt đúng chỗ ngừng nghỉ, zoom nhẹ, SFX đúng beat, nhạc nền dưới giọng, phụ đề vừa khung an toàn |
| **Kiểm tra** | Build xong có báo cáo cảnh báo, preview still từng phụ đề, render preview MP4 trước khi cài |

## Yêu cầu

- **Claude Desktop** có quyền chạy code và đọc/ghi thư mục trên máy.
- **Connector Higgsfield** còn credit — dùng để tạo ảnh và giọng đọc. Không có connector thì không tạo được media.
- **CapCut bản máy tính** trên Mac hoặc Windows (không phải app điện thoại / web).
- **Python 3.9+**. Lần đầu chạy `python3 scripts/check_env.py --whisper` sẽ tự cài `numpy`, `Pillow`, `scipy`, `ffmpeg` và model Whisper nếu thiếu.
- Thư mục nhạc + hiệu ứng âm thanh riêng (tuỳ chọn). Không có thì bỏ qua phần nhạc/SFX.

## Cách dùng

1. Tải thư mục này về, hoặc clone repo SkillCut.
2. Trong Claude Desktop: **Customize → Skills → Add / Upload skill**, chọn `SKILL.md` (hoặc cả thư mục).
3. Mở CapCut PC, tạo **dự án mới**, kéo toàn bộ ảnh + file lồng tiếng vào, đặt tên dự án **không dấu, viết liền**, rồi **thoát hẳn CapCut**.
4. Trong Claude, yêu cầu dựng video và trỏ tới thư mục dự án CapCut + thư mục media. Ví dụ:

```text
Đọc .community/HaiGiang-AutoEditCapcut/SKILL.md và dựng video 9:16
từ thư mục C:\Users\Admin\Videos\CapCut Automation\AI lam video
```

5. Claude sẽ hỏi ngôn ngữ, độ dài, phong cách, chủ đề; viết kịch bản; tạo giọng; canh thời gian; tạo ảnh; rồi ghi timeline. Bạn duyệt kịch bản, duyệt ảnh nhân vật, nghe thử giọng và xem preview.
6. Mở CapCut kiểm tra. Nếu media bị **bôi đỏ / mất kết nối**, chọn **Link media** và trỏ lại đúng file trong thư mục dự án — Claude tạo bản media mới nên CapCut chưa có quyền đọc.

> Luôn đóng hẳn CapCut trước khi Claude ghi project. CapCut đang mở sẽ ghi đè timeline lúc thoát.

## Cấu trúc

- `SKILL.md` — quy trình 11 bước, checkpoint, luật bắt buộc khi dựng.
- `references/setup.md` — công cụ, 3 cách AI truy cập máy, đường dẫn thư mục CapCut trên Mac/Windows, bảng chi phí.
- `references/script-and-voice.md` — luật viết kịch bản, chọn giọng, tạo và ghép lồng tiếng, tiếng Việt, kịch bản video dọc.
- `references/visuals.md` — menu phong cách, shot list, ảnh tham chiếu nhân vật, prompt ảnh, QA, khung hình dọc.
- `references/capcut-edit.md` — tin nhắn bàn giao, cấu trúc project CapCut, tìm nhạc/SFX, định dạng edit plan, kỹ thuật dựng, build/QA, cài project.
- `references/troubleshooting.md` — lỗi thường gặp và cách sửa.
- `scripts/` — checklist môi trường, ghép/canh lồng tiếng, chia cảnh, chuẩn hoá ảnh, quét thư viện nhạc, dựng và kiểm tra project, preview, cài project, đóng gói offline.
- `assets/` — template object CapCut, font phụ đề (Metropolis, Be Vietnam Pro Bold), từ khoá SFX, bộ cài Mac/Windows.
- `Tư liệu hướng dẫn.pdf` — tài liệu hướng dẫn đi kèm.

## Giới hạn cần biết

- Chỉ dựng trên **CapCut desktop**. CapCut cập nhật có thể đổi định dạng file project.
- Cần **Claude Desktop + connector Higgsfield**. Bản web không ghi được vào ổ đĩa.
- AI **không nghe được âm thanh** — mọi quyết định về lời nói dựa trên bản chép lời.
- Ảnh do AI tạo **không chứa chữ**; phụ đề được thêm riêng trong CapCut.
- Tên dự án phải **không dấu**. Đổi tên sau khi dựng có thể làm lệch đường dẫn media.
- Chi phí thay đổi theo gói và credit; luôn xem báo giá trước khi tạo ảnh/giọng.

## Nguồn & ghi công

- Kênh gốc: **[youtube.com/@haigiangvideo](https://www.youtube.com/@haigiangvideo)**
- Video nguồn: **[AI không chỉ xuất clip sẵn nữa, nó dựng thẳng timeline CapCut](https://www.youtube.com/watch?v=ezhxedVFbrs)**
- TikTok: [@haigiangvideo](https://www.tiktok.com/@haigiangvideo) · Instagram: [@haigiangvideo](https://www.instagram.com/haigiangvideo) · Fanpage: [Hai Giang Media](https://www.facebook.com/haigiangmedia)
- Skill này được đóng góp vào SkillCut từ kênh trên.

## License

MIT, xem [`LICENSE`](./LICENSE). Không liên kết hay được CapCut / Anthropic / Higgsfield chứng nhận.
