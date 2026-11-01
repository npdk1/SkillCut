# Phân tích SRT và thiết kế popup có chủ đích

Mục tiêu là biến lời thoại thành điểm nhấn thị giác có ích, không phủ video bằng card. Subtitle vẫn nổi trực tiếp trên hình và không có background.

## Quy trình đọc SRT

1. Chia lời thoại theo ý nghĩa, không chỉ theo timestamp.
2. Gắn một nhãn cho từng ý có tiềm năng nhấn:
   - `hook-list`: chuỗi lợi ích, kết quả hoặc lời hứa.
   - `reason-warning`: nguyên nhân, lỗi thường gặp, cảnh báo.
   - `contrast-exception`: hai trường hợp khác nhau, quy tắc và ngoại lệ.
   - `options`: nhiều cách làm đều hợp lệ.
   - `number-measurement`: lượng, nhiệt độ, thời gian hoặc tỉ lệ cần nhớ.
   - `payoff`: khoảnh khắc hoàn thiện hoặc kết quả đáng chờ.
3. Chỉ chọn ý mà graphic giúp người xem hiểu hoặc nhớ nhanh hơn. Bỏ qua câu nối, lời chào và mô tả đã thấy rõ trong hình.
4. Xem frame tại timestamp đó để tìm vùng trống. Không che mặt, tay, dao, chảo, nguyên liệu chính hoặc subtitle.
5. Sau khi đặt popup, kiểm tra frame xuất hiện, giữa animation và biến mất.

## Ánh xạ nội dung sang hình thức

- `hook-list` → stack 2–3 hàng xuất hiện tuần tự như notification stack.
- `reason-warning` → một reason card: câu hỏi nhỏ, kết luận lớn, mô tả tối đa một dòng.
- `contrast-exception` → hai hàng so sánh, dùng hai accent khác nhau và mũi tên ngắn.
- `options` → 2–3 chip lựa chọn; nhấn phương án đang được minh họa trong video.
- `number-measurement` → stat card lớn cho con số, đơn vị và ghi chú ngắn.
- `payoff` → label hoặc callout nhỏ gần món ăn; không dựng card lớn che thành phẩm.

## Mật độ và nội dung

- Với short nhanh dưới 60 giây, mốc tham khảo là một popup mỗi 5–8 giây. Với video hướng dẫn dài hơn 2 phút, giãn thành khoảng 8–18 giây để tránh cảm giác template và cho món ăn có thời gian tự kể chuyện.
- Không để hai popup lớn cùng lúc.
- Popup dài khoảng 2,5–6 giây tùy lượng thông tin.
- Tiêu đề 2–5 từ; phần giải thích tối đa khoảng 45 ký tự.
- Không lặp nguyên văn subtitle. Ví dụ thoại “bì hay bị dai khô” có thể cô đọng thành `VÌ SAO BỎ BÌ? / DỄ DAI & KHÔ`.
- Với danh sách nói liên tục, reveal từng hàng theo nhịp lời thoại thay vì hiện cả khối một lần.
- Trên timeline dài, luân phiên hình thức theo ý nghĩa (compare, stat, stack, reason) và chừa những đoạn hoàn toàn không có card. Không đổi kiểu chỉ để tạo sự mới lạ.

## Chuyển động Remotion

- Dùng `useCurrentFrame()`, `spring()` và `interpolate()` để animation seek-safe.
- Card vào bằng opacity + translate 18–28 px; stack có thể stagger 4–7 frame mỗi hàng.
- Giữ scale trong khoảng 0.96–1.0. Tránh bounce lớn hoặc xoay card.
- Pattern `notification-stack` là nguồn cảm hứng về reveal tuần tự; khi làm bằng Remotion phải triển khai bằng frame, không phụ thuộc CSS animation.

## Tiêu chí duyệt

- Tắt popup đi thì video vẫn hiểu được nhờ subtitle.
- Bật popup lên thì người xem nắm được cấu trúc hoặc mẹo nhanh hơn.
- Popup có phân cấp rõ, không mang cảm giác một template lặp lại.
- Card không tranh chấp với caption và không che hành động nấu ăn.
