# QC bắt buộc cho video review nhà

Đọc file này trước khi render demo hoặc bản cuối.

## FPS và độ mượt

1. Dùng `ffprobe` đọc `r_frame_rate` và `avg_frame_rate` của footage chính trước khi đăng ký composition.
2. FPS đầu ra không được thấp hơn FPS hiển thị của nguồn. Giữ nguyên FPS nguồn khi chỉ cắt dựng; chọn 60fps khi scene có route, marker, typography hoặc transition cần chuyển động mượt hơn.
3. Nâng composition từ 30 lên 60fps chỉ làm lớp đồ họa mượt hơn; frame footage 30fps vẫn lặp lại. Chỉ gọi footage mượt hơn khi đã dùng optical-flow/frame interpolation có kiểm tra artifact.
4. Mọi timing theo giây phải nhân với `fps` từ `useVideoConfig()`. Không hard-code frame count theo 30fps trong component 60fps.

Sau render chạy:

```powershell
node scripts/verify-video.mjs <source-video> <rendered-video>
```

Script phải fail khi output FPS thấp hơn nguồn, thiếu audio/video hoặc lệch duration A/V quá 0,1 giây.

## Độ phân giải và độ nét

1. Dùng `ffprobe` đọc kích thước nguồn. Không xuất bản giao khách có chiều rộng hoặc chiều cao thấp hơn footage chính, trừ khi người dùng yêu cầu bản proxy.
2. Với video dọc nguồn nhỏ, ưu tiên 1080×1920 hoặc render Remotion bằng `--scale=2` để typography, SVG, map và graphic được raster hóa sắc ở độ phân giải đích. Không phóng MP4 đã render thấp lên sau cùng nếu còn source composition.
3. Upscale không khôi phục chi tiết quang học bị mất. Có thể dùng Lanczos và sharpen nhẹ khoảng `unsharp=5:5:0.2–0.4`; xem frame có tóc, dây điện, gạch và chữ nhỏ để tránh halo/ringing. Không dùng sharpen mạnh để giả chi tiết.
4. Render H.264 delivery ở CRF khoảng 16–19, `yuv420p`, giữ nguyên kích thước pixel và thêm `faststart`. Với bản 2K dọc, kiểm tra bitrate/file size không làm nền map hoặc vùng tối bị block.
5. Sau render, script `verify-video.mjs` phải fail nếu output nhỏ hơn nguồn trên bất kỳ chiều nào.

## Tự kiểm tra va chạm layout

- Copy `assets/LayoutCollisionGuard.tsx` vào project, mount một lần ở composition gốc.
- Gắn `data-layout-role="caption"` và `data-layout-id` cho subtitle; gắn `data-layout-role="overlay"` cho popup/card cần tránh.
- Guard so bounding box của các lớp đang hiển thị. Khi render, collision phải làm render fail với frame và tên hai lớp; trong Studio chỉ cảnh báo để người dựng còn chỉnh được.
- Với map hoặc floor plan, bảo vệ thêm marker, route, label hoặc số liệu quan trọng nếu card có thể che chúng. Va chạm có chủ ý phải được xử lý bằng group/allow-list rõ ràng, không tắt toàn bộ guard.
- Guard phải kiểm tra ít nhất ba loại cặp: `caption↔overlay`, `overlay↔overlay` và `overlay↔protected`. Dùng `protected` cho mặt người dẫn, marker, tên địa điểm hoặc vùng kiến trúc không được che khi vị trí có thể mô tả bằng box.

## Frame QC tự động

Render still ở tối thiểu các điểm sau:

- frame giữa hook;
- đầu, giữa và cuối mỗi information scene;
- frame popup đạt scale lớn nhất;
- subtitle dài nhất và mọi subtitle hai dòng;
- một frame ngay trước và sau transition;
- frame tối nhất hoặc nhiều chi tiết nhất trong footage.

Ghép contact sheet và kiểm tra: chữ không che bằng chứng hình ảnh, không tràn canvas, không đè element khác, route/marker đọc được và attribution vẫn nhìn thấy. Contact sheet không thay cho việc xem playback quanh transition.

## Review về ý nghĩa và mật độ

- Với mỗi popup, tắt riêng popup và hỏi: mất nó thì người xem có mất thông tin quyết định nào không? Nếu không, xóa popup.
- So ba frame đầu–giữa–cuối của từng overlay để bắt camera pan làm sai vị trí; không duyệt chỉ bằng frame đẹp nhất.
- Kiểm tra tỷ lệ diện tích overlay trên frame, khoảng trống vô nghĩa và số lần lặp cùng treatment. Một video dài không nên trở thành chuỗi card giống nhau.
- Đoạn kết phải có ít nhất ba góc highlight khác nhau trước hero/CTA khi source đủ cảnh. Kiểm tra giá đọc được trên cả frame sáng lẫn tối.
- Mỗi vòng feedback của người duyệt được phân loại thành lỗi project hay quy tắc chung; cập nhật skill sau khi sửa và chạy lại contact sheet cùng validator.
