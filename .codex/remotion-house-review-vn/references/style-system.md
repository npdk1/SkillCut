# Hệ thống thiết kế video review nhà dọc chuẩn Luxury Realtor

Các thông số dưới đây dùng cho canvas gốc 576×1024 (chuẩn tỉ lệ 9:16). Với kích thước 1080×1920, nhân các giá trị pixel theo tỉ lệ 1.875.

---

## 1. Cấu Trúc Phân Tầng Remotion (Layer Architecture)

Để đạt được chất lượng hình ảnh sang trọng, sâu và không bị lỗi dán đè phẳng (template slop), Remotion composition phải tuân thủ nghiêm ngặt thứ tự layer sau:

```
[Mặt trên cùng]
Layer 7: Subtitle Karaoke (Chữ vàng kinetic pop, stroke 2.6px, text-shadow đa tầng)
Layer 6: In-Scene Overlays (Stat Rail, Hero Price, Minimal Chip)
Layer 5: Cinematic Vignettes (Gradient mờ trên/dưới bảo vệ vùng đọc chữ)
Layer 4: B-Roll Photo Showcase (Cắt cảnh show ảnh minh họa khi vào khúc phụ)
Layer 3: Host Cutout (Alpha mask của người dẫn, che đè lên Layer 2)
Layer 2: Behind-Subject 3D Typography (Hook mở đầu, Hero Price neo sâu trong cảnh)
Layer 1: Background Footage (<OffthreadVideo /> toàn cảnh có punch-in zoom)
[Đáy composition]
```

---

## 2. Typography (Bộ 3 Phông Chữ Đẳng Cấp - Font Triad)

Học từ các video Realtor chuẩn triệu view (như Gladia By The Waters), không dùng một phông đơn điệu mà kết hợp tinh tế 3 kiểu phông:

1. **Luxury Serif (Branding & Phong cách)**: Tải font Serif có chân sang trọng (`Playfair Display` hoặc `Cormorant Garamond`) cho tên dự án, khu vực hoặc phong cách kiến trúc (`CHÂU ÂU`, `TÂN CỔ ĐIỂN`, `GLADIA`).
   - Cỡ chữ: 54–78 px.
   - Trọng lượng: 900 (Black).
   - Letter-spacing: `0.04em – 0.06em`.
   - Hiệu ứng: Stroke mỏng tối màu kết hợp drop shadow sâu: `textShadow: '0 8px 32px rgba(0,0,0,0.95), 0 2px 8px rgba(0,0,0,0.9)'`.

2. **Handwritten Cursive Script (Nhấn cảm xúc)**: Phông viết tay uốn lượn mềm mại (`Dancing Script` hoặc script tương đương) màu vàng chanh `#FFEA31` hoặc đỏ rượu vang cho các từ nghệ thuật ("Mảnh ghép", "thu nhỏ", "tự tay thiết kế", "4 Tầng").
   - Cỡ chữ: 34–56 px.
   - Góc xoay: `transform: rotate(-6deg)` đến `-8deg`.
   - Hiệu ứng: Glow viền nhẹ `0 0 16px rgba(255, 234, 49, 0.7)`.

3. **Modern Geometric Sans (`Be Vietnam Pro`)**: Dành cho phụ đề karaoke, số liệu kỹ thuật, vị trí và nhãn phụ trợ.
   - Cỡ chữ: 11–16 px (nhãn/tag), 32–36 px (số liệu), 30–34 px (subtitle).
   - Trọng lượng: 700–900.
   - Letter-spacing: `0.15em – 0.25em` (với nhãn viết hoa).

---

## 3. Kỹ Thuật Chữ Chìm 3D Sau Chủ Thể (Text Behind Reviewer / Depth Occlusion)

Đây là kỹ thuật cốt lõi tạo chiều sâu điện ảnh cho video.

### Quy Trình Tạo Mask Alpha:
1. Dùng Python với thư viện `rembg` (model `u2net`) để tách mask nền của người dẫn trên đoạn footage mở đầu (thường là 2–3 giây đầu khi người dẫn bước từ xa lại gần):
   ```python
   import rembg, cv2
   session = rembg.new_session('u2net')
   # Resize 288x512 để xử lý nhanh ~0.2s/frame, sau đó upscale về 576x1024
   small = cv2.resize(frame, (288, 512))
   mask = rembg.remove(small, session=session, only_mask=True)
   mask = cv2.resize(mask, (576, 1024), interpolation=cv2.INTER_LINEAR)
   # Lưu dưới dạng ảnh RGBA trong suốt
   b, g, r = cv2.split(frame)
   rgba = cv2.merge([b, g, r, mask])
   cv2.imwrite(f'public/cutouts/f_{frame_no:03d}.png', rgba)
   ```

2. Trong Remotion:
   - **Lớp BehindHostText (Layer 2, zIndex: 15)**: Đặt chữ lớn tại vị trí tọa độ Y ngang vai và đầu của người dẫn (thường là `top: 380px – 410px`).
   - **Lớp HostCutout (Layer 3, zIndex: 20)**: Sử dụng `<Img src={staticFile(`cutouts/f_${frame}.png`)} />` phủ khít 100% kích thước canvas.
   - **Kết quả**: Đầu, vai và thân áo của reviewer tự nhiên che khuất các ký tự ở giữa, tạo cảm giác chữ gắn chặt vào bức tường hoặc lơ lửng trong con ngõ thực tế.

---

## 4. Chuyển Cảnh B-Roll Show Ảnh Minh Họa (B-Roll Photo Showcase)

Khi kịch bản chuyển sang **Khúc Phụ (Secondary Conversation)** — như chém gió, cảm thán tiện ích ("như khách sạn La Carte luôn", "view rất chill") hoặc mô tả không gian mà camera đi bộ đang quay thô vào tường trắng/cầu thang:

1. **Cắt Cảnh Dứt Khoát (Hard Cut / Quick Flash)**:
   - Thay thế video thô bằng ảnh chụp kiến trúc độ nét cao (Master bedroom, phòng tắm gương sóng xoay, ban công sân thượng).
   - Hiệu ứng chuyển cảnh: 2 frame flash trắng nhẹ (`opacity 0.4 -> 0`) hoặc cut nhanh tạo nhịp dứt khoát.

2. **Chuyển Động Ken Burns Mượt Mà**:
   - Sử dụng `interpolate()` để tạo chuyển động zoom chậm từ `1.0` lên `1.06` (hoặc ngược lại) với tâm zoom hướng vào chi tiết nội thất đắt giá.

3. **Thẻ Thông Tin Sang Trọng (Editorial Luxury Badge)**:
   - Đặt ở góc trên bên trái (`top: 70px`, `left: 32px`):
     * Dòng 1: Tag danh mục viết hoa, font Sans nhỏ vàng (`KHÔNG GIAN NGHỈ DƯỠNG`, letter-spacing 0.24em).
     * Dòng 2: Tên không gian font Serif lớn trắng (`Phòng Ngủ Master` / `Vườn Ban Công Chill`).
     * Dòng 3: Điểm nhấn cảm xúc font Script uốn lượn vàng (`Chuẩn Khách Sạn 5 Sao` / `Chuẩn Biệt Thự Mini`).

4. **Âm Thanh Xuyên Suốt (Continuous Audio Bridge)**:
   - Audio lời nói và tiếng cười của 2 reviewer tiếp tục phát liên tục bên dưới qua `<Audio src={videoSrc} />`, giúp việc cắt cảnh thị giác hoàn toàn tự nhiên mà không gây giật mình cho người nghe.

---

## 5. Subtitle Karaoke Động

- **Vị trí**: `left/right: 32px`, `bottom: 76–92px`.
- **Độ dài**: Mỗi page 3–7 từ, ưu tiên 1 dòng, tối đa 2 dòng.
- **Phông chữ**: `Be Vietnam Pro`, weight 900, size 31–34 px, `letterSpacing: -0.02em`.
- **Hiệu ứng chữ đọc**:
  * Từ bình thường: Màu trắng `#FFFFFF`.
  * Từ đang nói (Active Word): Đổi sang màu vàng hoàng kim `#FFD21C` kết hợp phóng to nhẹ (`scale: 1.08x`) và glow viền.
  * Viền chữ (Stroke): `-webkit-text-stroke: 2.6px #000000; paint-order: stroke fill;`.
  * Text shadow: `0 3px 12px rgba(0,0,0,0.95), 0 1px 3px rgba(0,0,0,0.9)`.
- **Tuyệt đối không dùng panel mờ hoặc hộp xám dán đè dưới subtitle.**

---

## 6. Hệ Thống 4 Hình Thức Đồ Họa Riêng Biệt (Chống Slop Box)

1. **Cinematic Hook** (`assets/BehindHostText.tsx`): Chữ 3D mở đầu chìm sau người dẫn, không đóng khung hộp.
2. **Stat Rail**: Thanh số liệu ngang với số khổng lồ (36–44 px) và vạch chia mỏng `rgba(255,255,255,0.25)`.
3. **Hero Price**: Con số giá bán `NHỈNH 12 TỶ` màu vàng kim lớn (54px), stroke tối màu, text shadow 3D sâu kết hợp nhịp camera punch zoom 1.05x.
4. **Minimal Tag/Chip**: Pill mỏng bo tròn thanh lịch (`padding: 6px 14px`, `border-radius: 999px`) cho điểm nhấn độc bản ("Gia chủ tự thiết kế", "Sổ đỏ trao tay").

---

## 7. Nhịp Điệu & Khoảng Thở (Pacing)

- Tuyệt đối không để popup xuất hiện liên tục không ngừng nghỉ.
- Giữa các đợt popup phải có khoảng nghỉ tối thiểu 3–6 giây **CHỈ CÓ FOOTAGE VÀ SUBTITLE** để người xem chiêm ngưỡng không gian nhà thật.
- Bỏ hoàn toàn các popup cho câu cảm thán sáo rỗng ("chuẩn khách sạn", "rất đẹp", "lung linh") nếu footage đã cho thấy điều đó.
