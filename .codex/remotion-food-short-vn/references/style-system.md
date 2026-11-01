# Hệ thống thiết kế video món ăn dọc

Các thông số dưới đây dùng cho canvas gốc 576×1024. Với kích thước khác, nhân theo tỉ lệ chiều rộng.

## Subtitle trực tiếp trên hình

- Vị trí: `left/right: 34px`, `bottom: 82–104px`.
- Mỗi page khoảng 24–32 ký tự, thường 1–2 dòng.
- Chữ: 34–36 px, weight 900, line-height 1.08–1.14, tracking âm nhẹ.
- Màu thường: `#FFFDF7`; từ đang đọc: `#FFD329`.
- Tách chữ khỏi nền bằng `WebkitTextStroke: 2.2–2.6px rgba(0,0,0,.92)` và drop shadow. Không thêm background, padding panel, border hay border-radius.
- Tất cả từ giữ cùng cỡ. Chỉ đổi màu từ đang đọc để tránh reflow và cảm giác karaoke rẻ tiền.
- Vào page mới bằng opacity + translate dọc 12–16 px trong khoảng 6–10 frame.

## Nhãn công đoạn

- Đặt trên trái: khoảng `left: 28px`, `top: 46px`.
- Vạch dọc accent rộng 5 px, cao khoảng 42 px.
- Dòng nhỏ: `BƯỚC 03`, 12–14 px, tracking 2 px, màu accent.
- Dòng chính: 22–24 px, uppercase, trắng, weight 900.
- Không dùng emoji hoặc pill kính đen trừ khi brief yêu cầu rõ.

## Title mở đầu

- Title card nên kéo dài khoảng 1,5–2,5 giây rồi dọn sạch để vào nội dung.
- Trong thời gian title card, ẩn nhãn bước, subtitle và popup. Không để ba hệ chữ tranh nhau trên cùng frame.
- Nếu footage có người hoặc hậu cảnh nhiều chi tiết, có thể dim nhẹ và blur khoảng 5–8 px; trả blur về 0 trước khi nội dung chính xuất hiện.
- Có thể canh giữa khi nền đã blur/dim, hoặc canh trái ở vùng trống khi chủ thể vẫn cần nhìn rõ.
- Kicker nhỏ + gạch ngang, title chính trắng, dòng hương vị/món sốt màu accent. Tối đa ba tầng: kicker, title, supporting line.
- Title nên fade/translate ngắn rồi biến mất hoàn toàn; nhãn bước và subtitle chỉ bắt đầu sau điểm kết thúc title.

## Outro

- Giữ khung thành phẩm nhìn rõ.
- Chỉ phủ gradient tối dần ở nửa dưới.
- Canh trái, neo bằng vạch dọc accent; title khoảng 36–40 px.
- Tránh màn tối đặc và card nằm giữa làm mất hình món ăn.

## Dấu hiệu cần sửa

- Pill tròn xuất hiện ở cả title, step và subtitle.
- Emoji dùng như nhãn mặc định thay vì có mục đích.
- Từ karaoke phóng to làm cả dòng nhảy.
- Background subtitle che chảo hoặc nguyên liệu.
- Ba khối chữ đều canh giữa và dùng cùng một hiệu ứng.
- Title, nhãn bước và subtitle cùng xuất hiện trong 1–3 giây đầu.
- Accent vàng chiếm quá nhiều diện tích; chỉ dùng để định hướng mắt.
