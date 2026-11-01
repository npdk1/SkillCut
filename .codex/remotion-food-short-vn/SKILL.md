---
name: remotion-food-short-vn
description: Dựng hoặc chỉnh video món ăn dọc bằng Remotion theo phong cách editorial Việt Nam, gồm phụ đề karaoke không nền, nhãn công đoạn gọn và title card tránh cảm giác template AI. Dùng cho clip nấu ăn/Reels/TikTok; không dùng cho video ngang, phim quảng cáo nhiều cảnh hoặc thiết kế cần giữ nguyên bộ nhận diện có sẵn.
---

# Remotion Food Short VN

Tạo video món ăn dọc rõ, cuốn và ưu tiên hình món ăn. Giữ lựa chọn framework của người dùng; skill này bổ sung ngôn ngữ thiết kế, không thay thế quy trình Remotion hiện có.

## Trước khi sửa

- Xem ít nhất ba khung hình: mở đầu, giữa và thành phẩm.
- Xác định vùng mặt, tay, chảo và món ăn để chữ không che hành động chính.
- Với video dài, dựng composition demo 30 giây trước. Chỉ render toàn bộ sau khi hướng thiết kế được chấp nhận hoặc người dùng yêu cầu rõ.

## Hệ thống hình ảnh mặc định

Đọc [references/style-system.md](references/style-system.md) khi tạo hoặc thay đổi subtitle, nhãn bước, title mở đầu hay outro.

Đọc [references/srt-insight-popups.md](references/srt-insight-popups.md) khi người dùng muốn AI tự phân tích SRT để chọn câu cần nhấn mạnh, popup hoặc graphic giải thích.

- Phụ đề nổi trực tiếp trên video, không có hộp nền, pill, blur panel hoặc border.
- Nhấn từ đang đọc bằng một màu accent; giữ nguyên cỡ chữ để dòng không nhảy.
- Nhãn công đoạn dùng số bước và vạch màu, canh trái. Tránh emoji và pill tròn nếu người dùng không yêu cầu.
- Title mở đầu tối đa ba tầng thông tin. Nếu giữ footage nét, ưu tiên canh trái hoặc bất đối xứng để không che mặt.
- Với title card riêng 1,5–2,5 giây, có thể canh giữa trên footage blur/dim; trong đoạn này phải ẩn step label, subtitle và popup, rồi trả video về trạng thái nét trước khi vào nội dung.
- Outro giữ món ăn làm hero; dùng gradient nhẹ phía dưới và một vạch dọc làm neo thị giác.
- Popup chỉ bổ sung cấu trúc mà subtitle chưa thể hiện: lợi ích, nguyên nhân, đối chiếu, lựa chọn hoặc số liệu. Không chép lại nguyên câu thoại vào card.

## Chuyển động

- Dùng `useCurrentFrame()`, `useVideoConfig()`, `interpolate()` và `spring()`; không dùng CSS animation/transition.
- Chuyển động chữ nên ngắn: opacity kết hợp translate 12–32 px. Không phóng to từng từ subtitle.
- Mọi giá trị giây phải đổi qua `fps` tại component.

## Kiểm tra và bàn giao

1. Chạy ESLint và TypeScript.
2. Kiểm tra trực quan ít nhất ba frame của demo; ưu tiên frame có mặt, thao tác tay và thành phẩm.
3. Render demo H.264/AAC 30 giây ở đúng độ phân giải nguồn.
4. Kiểm tra bằng `ffprobe`: fps đúng, có cả audio/video và thời lượng audio–video lệch dưới 0,1 giây.
5. Sau một lần sửa thiết kế đã qua kiểm tra, cập nhật skill tái sử dụng mà người dùng chỉ định. Chỉ ghi lại quy tắc đã được quan sát hoặc duyệt; không biến một lỗi riêng lẻ thành quy tắc chung.

Khi dự án có thư mục `good-skills/remotion-food-short-vn`, đồng bộ các quyết định thiết kế đã xác nhận vào skill đó sau mỗi vòng sửa và chạy `quick_validate.py` trước khi bàn giao.
