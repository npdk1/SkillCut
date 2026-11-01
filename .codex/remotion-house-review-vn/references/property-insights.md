# Phân tích SRT cho video review nhà

Mục tiêu là chuyển lời nói thành lớp thông tin hỗ trợ quyết định, không biến video thành bảng thông số bán hàng.

## Nhãn nội dung

Chia SRT theo cụm nghĩa rồi gắn nhãn khi graphic thực sự giúp người xem hiểu hoặc nhớ:

- `price-hook`: giá chào bán, giá thuê hoặc chi phí nổi bật.
- `location`: tên phố, dự án, quận hoặc khu vực.
- `proximity`: thời gian hoặc khoảng cách tới hồ, trường, phố chính, ga hoặc tiện ích.
- `property-stat`: diện tích, mặt tiền, số tầng, số phòng, hướng hoặc chiều rộng ngõ.
- `layout-reveal`: tầng trên rộng hơn, phòng ẩn, sân, giếng trời hoặc thay đổi công năng.
- `income-use`: homestay, cho thuê, kinh doanh hoặc dòng tiền; chỉ dùng khi lời thoại hoặc vật liệu có căn cứ.
- `real-world-caveat`: ngõ nhỏ, dây điện, thiếu sáng, vệ sinh chung, cầu thang dốc hoặc hiện trạng cần sửa.
- `payoff-view`: tầm nhìn, ánh sáng, ban công, mặt tiền hoặc khoảnh khắc đẹp nhất của tour.

Bỏ qua câu nối, lời mời camera di chuyển và mô tả mà footage đã thể hiện đủ rõ.

## Ánh xạ sang hình thức

- `price-hook` → số lớn + nhãn loại tài sản hoặc vị trí, xuất hiện đúng khi giá được nói.
- `location` → location tag hoặc headline tên đường; không giả giao diện bản đồ.
- `proximity` → stat thời gian/khoảng cách kèm đường nối đơn giản hoặc hai điểm đầu-cuối.
- `property-stat` → stat card với số lớn, đơn vị nhỏ và nhãn ngắn.
- `layout-reveal` → before/after tầng hoặc sơ đồ khối đơn giản; ghi `minh họa` nếu không phải bản vẽ thật.
- `income-use` → use-case card hoặc dòng tiền; không tự bịa số tiền.
- `real-world-caveat` → fact card gọn, màu trung tính hoặc đỏ tiết chế; giữ giọng điệu đúng lời nói.
- `payoff-view` → callout nhỏ gần chi tiết, tránh card lớn che cảnh.

## Mật độ và lời chữ (Anti-Slop Pruning)

- Trong short dọc 30–60s, chỉ giữ 3–4 mốc đồ họa có giá trị quyết định nhất. Tránh spam popup liên tục 3–4 giây một lần khiến video biến thành slideshow template AI.
- Bỏ qua toàn bộ câu cảm thán, lời khen chung chung ("nhà đẹp quá", "lung linh", "chuẩn khách sạn", "rất nghệ") nếu footage đã cho thấy điều đó.
- Không để hai popup lớn cùng lúc. Chừa các đoạn thở (3–6 giây) chỉ có footage chuyển động và subtitle karaoke.
- Headline popup chỉ từ 2–4 từ khóa; KHÔNG thêm câu mô tả phụ dài dòng lặp lại những gì người xem vừa nghe.
- Giá, diện tích và khoảng cách phải giữ đúng đơn vị. Nếu SRT mơ hồ, giữ cách nói ước lượng như `~20 m` hoặc `khoảng 5 phút`.

## Kiểm tra theo timestamp

- Xem frame ngay trước popup, giữa animation và trước khi biến mất.
- Xác nhận payoff không xuất hiện trước từ khóa được nói.
- Kiểm tra popup không che chi tiết bằng chứng và subtitle không tranh chấp vùng đọc.
- Đối chiếu mọi con số với SRT hoặc vật liệu người dùng trước khi render.
