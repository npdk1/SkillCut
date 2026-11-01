# Đồng bộ phản hồi & bài học thiết kế vào bộ template

Tài liệu này lưu lại các quy tắc thiết kế dùng chung đã được chuẩn hóa qua các vòng review thực tế, nhằm nâng cấp bộ template Remotion House Review VN lên chuẩn Luxury Realtor cao cấp nhất.

---

## 1. Bài Học Cốt Lõi: Chống Template Slop & Triển Khai Chuẩn Luxury Realtor

### A. Quy Tắc 1: Loại Bỏ Triệt Để Mẫu Hộp Chữ Nhật Đồng Dạng (Anti-Slop Box)
- **Vấn đề cũ**: Mọi loại dữ liệu (giá, số tầng, diện tích, câu khen) đều dùng chung một kiểu card chữ nhật bo góc tối màu dán đè lên video. Điều này tạo cảm giác template AI giá rẻ ("slop").
- **Quy tắc chuẩn hóa**: Phải sử dụng 4 hình thức đồ họa riêng biệt:
  1. `Cinematic Hook`: Typography 3D mở đầu không khung viền.
  2. `Stat Rail`: Thanh số liệu ngang với chữ số khổng lồ và vạch chia mỏng.
  3. `Hero Price`: Chữ số giá bán nổi bật màu vàng hoàng kim với chiều sâu 3D hoặc đặt sau lưng người dẫn.
  4. `Minimal Tag/Chip`: Pill mỏng bo tròn thanh lịch cho điểm nhấn độc bản ("Gia chủ tự thiết kế").

### B. Quy Tắc 2: Đồ Họa 3D Chìm Sau Chủ Thể (Text Behind Reviewer)
- **Vấn đề cũ**: Chữ lớn dán đè lên mặt hoặc cơ thể người dẫn khi họ bước đi trong ngõ hoặc trong nhà.
- **Quy tắc chuẩn hóa**: Sử dụng AI matting tách lớp alpha của người dẫn (`rembg`/U2Net).
  - Đặt chữ 3D (Hook, Hero Price) ở lớp giữa (Layer 2).
  - Đặt cutout người dẫn ở lớp trên (Layer 3).
  - Người dẫn tự nhiên che khuất phần giữa của dòng chữ, tạo chiều sâu phối cảnh chân thực.

### C. Quy Tắc 3: Phân Tầng Khúc Chính vs Khúc Phụ (B-Roll Photo Showcase)
- **Vấn đề cũ**: Một video raw dài 8–10 phút nếu để nguyên một cú one-shot đi bộ thì khán giả sẽ phải nhìn cảnh người dẫn leo cầu thang thô, đi hành lang hoặc nhìn vào tường trắng khi chém gió.
- **Quy tắc chuẩn hóa**:
  - **Khúc Chính (Direct A-Roll)**: Giữ hình người dẫn khi nói câu hook, pháp lý, giá bán, nhận định độc bản.
  - **Khúc Phụ (B-Roll Showcase / Minh họa)**: CẮT BỎ CẢNH ĐI BỘ RUNG LẮC khi người nói chém gió phụ ("như khách sạn La Carte luôn", "view rất chill"). Cắt dứt khoát sang các bức ảnh chụp hoặc footage B-roll đẹp nhất (phòng ngủ master, gương xoay nghệ thuật, sân thượng chill) với chuyển động Ken Burns zoom chậm và luxury badge. Lời nói và tiếng cười gốc tiếp tục phát liên tục bên dưới.

### D. Quy Tắc 4: Bộ 3 Phông Chữ Đẳng Cấp (Font Triad)
- **Luxury Serif (`Playfair Display`)**: Headline & Phong cách kiến trúc.
- **Handwritten Cursive Script (`Dancing Script`)**: Từ nhấn cảm xúc màu vàng kim `#FFEA31` uốn lượn nghiêng -6° đến -8°.
- **Modern Geometric Sans (`Be Vietnam Pro`)**: Subtitle karaoke và thông số kỹ thuật.

---

## 2. Quy Trình Cập Nhật Khi Có Phản Hồi Mới

1. **Phân loại phản hồi**:
   - `Quy tắc dùng chung`: Áp dụng cho mọi video review nhà (ví dụ: font, nhịp cắt, B-roll showcase) -> Cập nhật vào `SKILL.md` và các file `references/`.
   - `Tùy chọn phong cách`: Có thể tái sử dụng theo yêu cầu từng khách hàng -> Ghi chú thành lựa chọn có điều kiện.
   - `Sửa riêng video`: Chỉ sửa trên project code hiện tại, không ghi thành luật chung.
2. **Kiểm tra và kiểm định**:
   - Chạy `npx tsc --noEmit` xác nhận code sạch.
   - Chạy `node scripts/verify-video.mjs` xác nhận thông số kỹ thuật (A/V drift < 0.1s).
