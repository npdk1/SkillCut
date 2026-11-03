# CapCut lưu dự án như thế nào (để Claude hiểu skill này làm gì)

- Mỗi dự án CapCut là **một thư mục** trong: `%LOCALAPPDATA%\CapCut\User Data\Projects\com.lveditor.draft\<tên dự án>`
  (nếu bạn đổi nơi lưu bản nháp, đặt biến môi trường `CAPCUT_DRAFTS` hoặc dùng `--root`).
- Trong thư mục đó có file **`draft_content.json`**: toàn bộ dòng thời gian (các track, đoạn video/âm thanh/chữ, keyframe zoom…).
  Bản CapCut có nhiều dòng thời gian còn có `timeline_layout.json` và thư mục `Timelines\<id>\draft_content.json`.
- Skill **đọc** file này để hiểu video đang ra sao (`analyze`) và **ghi** vào đó để thêm đoạn cắt, chữ, SFX, zoom.
- Mỗi lần ghi, công cụ chép file gốc vào `_backup_junops` trong dự án. Muốn hoàn tác: chép file trong thư mục backup đè lại (khi CapCut đang đóng).

## Những thứ skill lấy từ CapCut của bạn
- **Kiểu chữ:** quét các dòng chữ bạn từng dùng trong các dự án (font, cỡ, màu, nền, hiệu ứng vào/ra) → `hoc` lưu thành kho mẫu `t1, t2…` trên máy bạn (`du_lieu/kho_mau.json`).
- **Hiệu ứng âm thanh:** quét các SFX đã tải về máy qua các dự án của bạn (`s1, s2…`). File âm thanh nằm trong bộ nhớ đệm CapCut của bạn, **không** nằm trong skill.
- Kho mẫu chỉ nằm trên máy bạn, không gửi đi đâu.

## Zoom
Zoom là keyframe phóng to/thu nhỏ gắn vào đoạn video chính, không cần mẫu nào.

## Lưu ý
- Luôn **đóng hẳn CapCut** trước khi ghi; sau khi bạn sửa tay trong CapCut cũng phải đóng trước khi Claude ghi tiếp.
- Công cụ này dựa vào cấu trúc file của CapCut; khi CapCut cập nhật lớn, cấu trúc có thể đổi và công cụ cần chỉnh lại.
