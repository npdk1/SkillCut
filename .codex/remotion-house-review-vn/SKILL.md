---
name: remotion-house-review-vn
description: Dựng hoặc chỉnh video review nhà ở dọc bằng Remotion từ footage và SRT tiếng Việt, gồm subtitle karaoke ngắn, popup giá-vị trí-thông số, scene bản đồ và QC tự động về FPS, audio và va chạm layout. Dùng cho video môi giới, house tour, review căn hộ hoặc nhà phố; không dùng cho video kiến trúc ngang, quảng cáo bất động sản dựng hoàn toàn từ ảnh hay dự án phải giữ nguyên brand guideline khác.
---

# Remotion House Review VN

Tạo video review nhà dọc đạt chuẩn Luxury Realtor (triệu view): hình ảnh chân thực, nhịp sóng cuốn hút, kỹ thuật Text-Behind-Subject (chữ 3D sau lưng người dẫn) và B-Roll Photo Showcase thay thế các cảnh đi bộ thô, loại bỏ hoàn toàn template slop.

## 1. Trước khi dựng

- Xem ít nhất năm khung hình đại diện cho mở đầu, mặt tiền/vị trí, lối vào, không gian bên trong và điểm hạn chế. Không suy luận toàn bộ video từ thumbnail.
- Làm sạch marker kỹ thuật trong SRT như `[cite: 1]`; không đưa chúng lên hình.
- Xác định vùng mặt người dẫn, lối đi, kiến trúc và chi tiết đang được mô tả để graphic không che bằng chứng hình ảnh.
- Với video raw dài (8–10 phút), mặc định dựng demo 20–30 giây đầu để duyệt ngôn ngữ hình ảnh trước khi làm toàn bộ.
- Bóc tách SRT theo cấu trúc nhịp sóng: **Khúc Chính (Direct A-Roll)** vs **Khúc Phụ (B-Roll Showcase / Minh họa)**.

## 2. Hệ thống hình ảnh & Layering Stack

Đọc [references/style-system.md](references/style-system.md) khi tạo hoặc sửa subtitle, typography, title, popup hay vùng an toàn.

### A. Cấu Trúc Phân Tầng Remotion (Layer Architecture)
Một composition chuẩn Luxury Realtor gồm 7 lớp xếp chồng nghiêm ngặt:
1. **Layer 1 (Đáy - Main Footage)**: `<OffthreadVideo />` cho A-Roll hoặc `<Img />` cho B-roll montage kèm hiệu ứng camera punch-in zoom (1.05x).
2. **Layer 2 (Không gian 3D - BehindHostText)**: Chữ 3D khổng lồ (Hook mở đầu, Hero Price) neo sâu trong phối cảnh hành lang/căn nhà.
3. **Layer 3 (Tiền cảnh người dẫn - HostCutout)**: Alpha mask cutout người dẫn (tạo bằng `rembg`/U2Net) che đè lên Layer 2, tạo hiệu ứng chiều sâu tự nhiên (Text-Behind-Subject).
4. **Layer 4 (B-Roll Photo Showcase Cutaways)**: Khi vào khúc phụ (mô tả tiện nghi, chém gió), cắt sang ảnh chụp kiến trúc đẹp nhất với hiệu ứng Ken Burns drift (1.05x) và luxury badge, giữ audio liên tục.
5. **Layer 5 (Cinematic Vignettes)**: Gradient mờ trên/dưới bảo vệ vùng đọc chữ mà không làm tối căn phòng.
6. **Layer 6 (In-Scene Typography Overlays)**: Stat Rail và Hero Price nổi tự nhiên, KHÔNG dùng hộp chữ nhật bo góc tối màu (slop box).
7. **Layer 7 (Trên cùng - Subtitle Karaoke & Collision Guard)**: Subtitle chữ vàng kinetic pop từ-theo-từ và `<LayoutCollisionGuard />`.

### B. Bộ 3 Phông Chữ Đẳng Cấp (Font Triad)
Tải phông từ `@remotion/google-fonts` (sử dụng mẫu tại [assets/font.ts](assets/font.ts)):
- **Luxury Serif (`Playfair Display`)**: Dành cho phong cách kiến trúc, thương hiệu và headline mở đầu (`CHÂU ÂU`, `TÂN CỔ ĐIỂN`, `GLADIA`).
- **Handwritten Cursive Script (`Dancing Script`)**: Màu vàng chanh `#FFEA31` hoặc đỏ rượu vang uốn lượn nghiêng (-6° đến -8°) cho từ nhấn cảm xúc (`thu nhỏ`, `tự thiết kế`, `4 Tầng`).
- **Modern Geometric Sans (`Be Vietnam Pro`)**: Dành cho phụ đề karaoke, số liệu kỹ thuật (`51 m²`, `12 TỶ`) và nhãn phụ trợ (weight 600–900).

### C. 4 Hình Thức Đồ Họa Riêng Biệt (Chống Template Slop)
Tuyệt đối không dùng cùng một kiểu card chữ nhật bo góc tối màu cho mọi loại thông tin:
1. **Cinematic Hook**: Chữ 3D lớn mở đầu neo chìm sau lưng người dẫn (`assets/BehindHostText.tsx`).
2. **Stat Rail**: Thanh số liệu ngang với số khổng lồ (36–44px) và vạch chia mỏng `rgba(255,255,255,0.25)`.
3. **Hero Price**: Chữ số giá bán nổi bật màu vàng kim 3D (`NHỈNH 12 TỶ`) kết hợp camera punch-in zoom.
4. **Minimal Tag/Chip**: Pill mỏng bo tròn thanh lịch (`padding: 6px 14px`, `border-radius: 999px`) cho điểm nhấn độc bản.

### D. Nhịp Điệu & Khoảng Thở (Pacing)
- Chừa khoảng thở tối thiểu 3–6 giây giữa các đợt graphic để người xem ngắm trọn vẹn ngôi nhà.
- Popup chỉ xuất hiện khi mang dữ liệu quyết định (giá, diện tích, tầng, pháp lý); loại bỏ hoàn toàn popup cho câu cảm thán sáo rỗng.

## 3. Quy Trình Dựng Video Raw Dài (9 Phút): Khúc Chính vs Khúc Phụ

Đọc [references/scene-architecture.md](references/scene-architecture.md) khi phân chia A-roll, B-roll và scene minh họa:

```
Video Raw 9 Phút (One-shot đi bộ dài)
  ├── KHÚC CHÍNH (Direct A-Roll - Giữ hình người dẫn):
  │     ├── Hook mở đầu: Tuyên ngôn định vị + Chữ 3D chìm sau lưng (Text Behind Subject).
  │     ├── Giá chào bán & Pháp lý: Con số quyết định + Camera punch zoom 1.05x.
  │     └── Tổng kết & Kêu gọi hành động (CTA).
  │
  └── KHÚC PHỤ (B-Roll Showcase / Minh Họa - CẮT BỎ CẢNH ĐI BỘ RUNG LẮC):
        ├── Lời chém gió phụ ("như khách sạn", "rất nghệ"): Chuyển cảnh sang B-Roll Photo Showcase
        │   (dùng ảnh đặc tả gương xoay, phòng ngủ master, sân thượng chill với Ken Burns zoom).
        ├── Chuyển tầng, đi cầu thang, hành lang thô: Cắt sang chuỗi montage B-roll 1.5–2.5s
        │   hoặc scene minh họa (sơ đồ mặt bằng 2D/3D, bản đồ tuyến đường).
        └── Voice và âm thanh gốc tiếp tục phát liên tục bên dưới, không bị ngắt quãng.
```

- Nhịp sóng xen kẽ chuẩn: `A-Roll (10-12s) -> B-Roll montage (10-12s) -> A-Roll (10-12s) -> B-Roll kết (4s) -> Outro (1s)`.

## 4. Chuyển Động & Mã Nguồn Mẫu (Remotion Assets)

- Dùng các component mẫu đã kiểm thử trong thư mục `assets/`:
  * `assets/BehindHostText.tsx`: Mẫu typography 3D chìm sau lưng người dẫn.
  * `assets/HostCutout.tsx`: Mẫu render frame cutout alpha bóc tách chủ thể.
  * `assets/PhotoShowcase.tsx`: Mẫu chuyển cảnh show ảnh kiến trúc với Ken Burns và luxury badge.
  * `assets/LayoutCollisionGuard.tsx`: Automated guard ngăn va chạm chữ và phụ đề lúc render.
  * `assets/font.ts`: Cấu hình tải Google Fonts chuẩn tiếng Việt.
- Dùng `useCurrentFrame()`, `useVideoConfig()`, `interpolate()` và `spring()`; không dùng CSS animation hay transition.
- Đổi mọi thời lượng giây sang frame bằng `Math.round(seconds * fps)`.

## 5. Kiểm Tra và Bàn Giao (QC Bắt Buộc)

Đọc [references/quality-control.md](references/quality-control.md) trước khi render hoặc bàn giao:

1. Chạy `npx tsc --noEmit` xác nhận không có lỗi TypeScript.
2. Kiểm tra layout guard không có va chạm giữa overlay và subtitle karaoke.
3. Render bằng `npx remotion render src/index.ts HouseReview <output.mp4> --pixel-format=yuv420p --crf=18`.
4. Chạy script kiểm định:
   ```powershell
   node remotion-house-review-vn/scripts/verify-video.mjs <source-video> <rendered-video>
   ```
   Xác nhận: FPS đầu ra >= FPS nguồn, độ phân giải bằng hoặc lớn hơn nguồn, và độ lệch A/V dưới 0,1 giây.
5. Tạo contact sheet trích xuất 6 khung hình then chốt (Hook behind-text, Stat, Hero Price, B-Roll 1, B-Roll 2, Detail) để nghiệm thu trước khi giao bản full.

## 6. Học Từ Phản Hồi

Đọc [references/feedback-learning.md](references/feedback-learning.md) sau mỗi vòng người dùng sửa và duyệt thiết kế để đồng bộ quy tắc mới vào bộ tài liệu skill.
