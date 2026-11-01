# Kiến trúc Scene, Nhịp Dựng & Chuyển Cảnh Cho Video Review Nhà Dọc

Video review nhà chất lượng cao không bao giờ giữ một cú one-shot đi bộ dài suốt 9 phút rồi chỉ dán chữ đè lên. Cần thay đổi linh hoạt chế độ hình ảnh theo chức năng câu nói, trong khi voice thoại gốc đóng vai trò là xương sống thời gian liên tục.

---

## 1. Phương Pháp Phân Tầng Raw 9 Phút: Khúc Chính vs Khúc Phụ

Khi tiếp nhận một video raw dài 8–10 phút (thường là một cú quay one-shot đi bộ review nhà từ cổng vào trong), template AI tiến hành phân loại ngữ nghĩa thành 2 nhóm nội dung:

```
Video Raw Đi Bộ 9 Phút
  │
  ├── 1. KHÚC CHÍNH (Direct A-Roll - Giữ hình người dẫn trực tiếp):
  │     ├── Hook mở đầu (0-5s): Tuyên ngôn, định vị phong cách sống ("Châu Âu thu nhỏ giữa lòng Hà Nội").
  │     ├── Giá chào bán & Pháp lý: Con số quyết định giao dịch ("Nhỉnh 12 tỷ", "Sổ đỏ trao tay").
  │     ├── Triết lý & Cảm nhận độc bản: Nhận xét cá nhân về gia chủ, phong thủy hoặc không gian đặc sắc.
  │     └── Tổng kết & Kêu gọi hành động (CTA).
  │     => KỸ THUẬT XỬ LÝ:
  │        • Giữ toàn màn hình người dẫn đang nói.
  │        • Tách lớp người dẫn bằng AI depth matting (U2Net) để đặt chữ 3D (Text Behind Subject) chìm sau lưng.
  │        • Áp dụng nhịp camera punch-in zoom 1.05x đúng từ khóa "12 TỶ" để tạo điểm nhấn thị giác.
  │
  └── 2. KHÚC PHỤ (B-Roll Showcase / Scene Minh Họa - CẮT BỎ CẢNH ĐI BỘ RUNG LẮC):
        ├── Lời chém gió phụ & Cảm thán: "Trông như khách sạn La Carte luôn", "lung linh", "chill quá anh ạ".
        ├── Di chuyển giữa các tầng / Leo cầu thang / Hành lang tường trắng thô.
        ├── Liệt kê chi tiết công năng khô khan: Tủ bếp, bàn ghế, thiết bị vệ sinh, bồn rửa.
        └── Mô tả khoảng cách, quy hoạch: "50m ra ô tô", "gần trường học".
        => KỸ THUẬT XỬ LÝ:
        • THAY THẾ TOÀN BỘ cảnh người dẫn đi bộ rung lắc hoặc nhìn vào tường trắng bằng B-Roll Photo Showcase:
          - Dùng các bức ảnh chụp hoặc footage cận cảnh góc đẹp nhất (Master bedroom, gương sóng xoay, sân thượng).
          - Áp dụng chuyển động Ken Burns zoom chậm (scale 1.0 -> 1.06).
          - Gắn thẻ Editorial Luxury Badge ở góc trên bên trái.
          - Âm thanh và lời thoại gốc tiếp tục phát liên tục bên dưới, không bị ngắt quãng.
        • Nếu cần minh họa khoảng cách/quy hoạch: Chuyển sang Information Scene (Sơ đồ mặt bằng 2D/3D hoặc bản đồ tuyến đường).
```

---

## 2. Nhịp Sóng A-Roll và B-Roll (Alternating Wave Rhythm)

Học từ cấu trúc nhịp của các video review bất động sản triệu view chuẩn quốc tế:
- Nhịp cắt không bao giờ dàn trải đơn điệu mà luân chuyển theo hình sin:
  ```
  A-Roll Hook (10-12s) 
    → B-Roll Montage Chi Tiết (10-12s) 
    → A-Roll Định Giá & Nhận Định (10-12s) 
    → B-Roll Phòng Ngủ / Sân Thượng (10-12s) 
    → A-Roll Chốt Hạ (8-10s) 
    → B-Roll Highlight & Outro (4s)
  ```
- Nhịp sóng này giữ trọn sự chú ý của người xem (high retention), cho phép khán giả vừa kết nối với cá tính của reviewer, vừa được chiêm ngưỡng không gian ngôi nhà mà không cảm thấy bị bội thực thông tin.

---

## 3. Chuyển Cảnh & Nhịp Camera (Camera Punch-in Zoom)

1. **Camera Punch-in Zoom (Tạo nhịp đập cho video)**:
   - Một video đi bộ dài thường bị cảm giác tĩnh lặng và đều đều. Tại các mốc cao trào (đặc biệt là lúc công bố giá bán "Nhỉnh 12 tỷ"):
   - Sử dụng `spring()` hoặc `interpolate()` để phóng to khung hình nhẹ (từ `1.0` lên `1.05`), tâm zoom hướng vào người dẫn hoặc góc nhìn căn phòng.
   - Nhịp zoom này ngay lập tức kích hoạt sự tập trung của người xem.

2. **Cắt Cảnh Dứt Khoát (Hard Cut) & Flash Nhẹ**:
   - Chuyển từ A-Roll sang B-Roll hoặc giữa các shot B-Roll nên là **hard cut** sạch (tương đương 90% các cut trong video chuyên nghiệp).
   - Có thể thêm hiệu ứng flash trắng cực nhanh trong 2 frame (`opacity 0.4 -> 0`) tại ranh giới cut để tăng cảm giác thời thượng và sang trọng.

---

## 4. Cấu Trúc Mã Nguồn Remotion Cho Photo Showcase

Mẫu component B-Roll Photo Showcase chuẩn (`assets/PhotoShowcase.tsx`):

```tsx
import React from 'react';
import {Img, interpolate, staticFile, useCurrentFrame} from 'remotion';
import {sansFont, serifFont, scriptFont} from './font';

export const PhotoShowcase: React.FC = () => {
  const frame = useCurrentFrame();

  // Active trong đoạn thoại phụ (ví dụ: frame 510 đến 654)
  if (frame < 510 || frame >= 654) return null;

  const isShot1 = frame < 582;
  const progress = isShot1 ? (frame - 510) / (582 - 510) : (frame - 582) / (654 - 582);

  const scale = isShot1
    ? interpolate(progress, [0, 1], [1.0, 1.06])
    : interpolate(progress, [0, 1], [1.06, 1.01]);

  const imgSrc = isShot1
    ? staticFile('showcase/showcase_mirror.jpg')
    : staticFile('showcase/showcase_rooftop.jpg');

  return (
    <div style={{position: 'absolute', top: 0, left: 0, width: '100%', height: '100%', zIndex: 25}}>
      <div style={{width: '100%', height: '100%', transform: `scale(${scale})`}}>
        <Img src={imgSrc} style={{width: '100%', height: '100%', objectFit: 'cover'}} />
      </div>

      {/* Editorial Luxury Badge */}
      <div style={{position: 'absolute', top: 70, left: 32}}>
        <div style={{fontFamily: sansFont, fontSize: 11, fontWeight: 800, color: '#FFEA31', letterSpacing: '0.24em'}}>
          {isShot1 ? 'HOTEL LUXURY SUITE' : 'KHÔNG GIAN NGHỈ DƯỠNG'}
        </div>
        <div style={{fontFamily: serifFont, fontSize: 30, fontWeight: 900, color: '#FFFFFF'}}>
          {isShot1 ? 'Gương Sóng Nghệ Thuật' : 'Vườn Ban Công Chill'}
        </div>
        <div style={{fontFamily: scriptFont, fontSize: 34, fontWeight: 700, color: '#FFEA31', transform: 'rotate(-4deg)'}}>
          {isShot1 ? 'Phong Cách La Carte' : 'Chuẩn Biệt Thự Mini'}
        </div>
      </div>
    </div>
  );
};
```

---

## 5. Quy Tắc Giữ Trục Âm Thanh (Audio Continuity)

- **Không bao giờ cắt audio khi chuyển cảnh B-Roll**:
  `<Audio src={videoSrc} />` phải chạy xuyên suốt toàn bộ composition.
  Khi màn hình chuyển sang ảnh tĩnh hoặc thước phim B-roll đặc tả, tiếng nói cười, hơi thở và nhịp điệu của reviewer vẫn tiếp tục tự nhiên. Điều này tạo cảm giác người xem đang được dắt đi tham quan căn nhà một cách liền mạch và sống động.
