# JunOps Edit CapCut

Skill giúp AI (Claude Code, Codex, Antigravity...) **edit video trực tiếp trong dự án CapCut bản máy tính trên Windows** — cả video ngắn dọc (TikTok / Shorts / Reels) lẫn video ngang dài (YouTube 16:9).

Mọi thứ được ghi thẳng vào file dự án CapCut thật, nên sau khi AI làm xong bạn vẫn mở CapCut lên kéo, cắt, đổi chữ, xoá như một video bình thường.

## Làm được gì

| Nhóm | Chi tiết |
|---|---|
| **Cắt ghép** | Cắt chỗ nói vấp và khoảng lặng, chọn lần nói trơn nhất cho từng câu, ghép đoạn theo luật sóng âm |
| **Phụ đề** | Tự chép lời (faster-whisper, chạy trên máy), phụ đề ngắn 4 chữ cho video dọc, phụ đề theo cả câu cho YouTube |
| **Nhấn mạnh** | Chữ quan trọng, zoom in/out đúng lúc, chữ không đè lên mặt |
| **Âm thanh** | Hiệu ứng âm thanh (SFX) lấy từ kho có sẵn trong CapCut của bạn, tự cân âm lượng giọng nói |
| **Motion graphic** | 4 mẫu vẽ bằng code: thẻ tiêu đề, danh sách, con số đếm tăng, thẻ phần — nằm trên track riêng, sửa/xoá được |
| **Học gu** | Đọc lại phần bạn sửa tay trong CapCut để lần sau làm theo |

Skill **không tách nền**, **không kèm font/SFX/nhạc** — chỉ dùng những gì đã có trong CapCut của chính bạn.

## Yêu cầu

- **Windows** + **CapCut bản máy tính** (đã thử với bản desktop; CapCut cập nhật có thể đổi định dạng file).
- **Python 3.9+**.
- **ffmpeg** (script tự cài bằng `winget` nếu thiếu).

Lần đầu dùng, AI tự chạy `python scripts/cai_dat.py --cai` để cài `faster-whisper`, `pillow`, `numpy` và ffmpeg. Bạn chỉ cần bấm đồng ý khi được hỏi quyền chạy lệnh. Lần chép lời đầu tiên sẽ tải model tiếng Việt vài trăm MB.

## Cách dùng

1. Clone repo và mở thư mục này.
2. Đưa AI **thư mục chứa video thô + file kịch bản** (nếu có), hoặc **chỉ một file video thô**.
3. AI dẫn bạn qua 6 chặng: nhận đầu vào → chuẩn bị máy → tạo dự án CapCut → edit → xem và chỉnh → xuất file.

Ví dụ câu lệnh:

```text
Đọc .community/junops-edit-capcut/SKILL.md và edit video trong ./raw/thanh-nuoc.srt
```

Hai việc bạn phải làm tay trong CapCut: **tạo dự án mới và kéo video thô vào dòng thời gian**, và **bấm Xuất** khi xong. Ở giữa, AI làm hết. Nhớ **đóng hẳn CapCut** trước khi AI ghi file.

## Cấu trúc

- `SKILL.md` — quy trình đầy đủ, luật cắt ghép, hướng dẫn từng bước cho video dọc và YouTube.
- `references/LUAT_CAT_GHEP.md` — luật cắt ghép bắt buộc (nhịp nghỉ, sóng âm, ghép câu).
- `references/CAPCUT_LUU_DU_AN.md` — cấu trúc file dự án CapCut.
- `references/PHONG_CACH_GOI_Y.md` — gợi ý phong cách mặc định.
- `references/PHONG_CACH_YOUTUBE.md` — phong cách riêng cho video ngang dài.
- `scripts/` — công cụ Python: chép lời, cắt, phụ đề, zoom, SFX, motion graphic, kiểm tra file xuất.
- `HUONG_DAN_CAI_DAT_VA_SU_DUNG.pdf` — hướng dẫn cài đặt và sử dụng cho người mới.

## Giới hạn cần biết

- Chỉ hỗ trợ **CapCut desktop trên Windows**.
- Chép lời có thể nghe sai tên riêng và chữ tiếng Anh — luôn xem lại phụ đề.
- `kiem_tra.py` chỉ bắt khung đen/đứng hình, không bắt lỗi chính tả hay chữ đè mặt.
- `cat` chỉ cắt track video chính; track lồng tiếng/B-roll không tự cắt theo.
- Motion graphic chỉ có 4 mẫu đơn giản; hiệu ứng phức tạp vẫn làm tay trong CapCut.
- AI không nghe được âm thanh — mọi quyết định về lời nói dựa trên bản chép lời.

## License

MIT-style, xem [`LICENSE`](./LICENSE). Không liên kết hay được CapCut/Anthropic chứng nhận.
