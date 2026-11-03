# Luật cắt ghép — bắt buộc đọc trước khi cắt (rút từ phiên thử 28–29/10/2026, đã kiểm chứng trên video thật)

Luật này **thắng** mọi gợi ý cũ trong skill. Mọi con số "nghỉ" ở dưới là **giây**.

## 1. Bốn quy tắc kiểm tra (áp dụng cho MỌI video có kịch bản)
1. **Mỗi câu kịch bản xuất hiện đúng 1 lần** trong video cuối. Người nói quay nhiều lần cùng một câu → chọn **lần nói trơn nhất (thường là lần cuối)**, bỏ các lần còn lại.
2. **Không lặp.** Sau khi cắt xong, nối các đoạn lại thành một file âm thanh, **chép lời lại** (`chep_loi.py`) rồi đọc từ đầu tới cuối: chỗ nào một cụm/câu xuất hiện hai lần là lỗi (hay gặp: cuối đoạn này còn dư vài chữ đã là đầu đoạn kế).
3. **Không ghép chữ lẻ, không cắt giữa cụm.** Mỗi đoạn là một cụm/câu trọn vẹn. Không lấy "sau" từ chỗ này ghép với "đó" từ chỗ khác. Nếu chữ đầu của một lần nói bị vấp thì bắt đầu đoạn ở chữ sạch kế tiếp, không vá bằng chữ từ lần nói khác.
4. **Từ điển chữ tiếng Anh/tên riêng.** Máy chép lời nghe sai (CapCut → "cấp cút", Claude → "kho", "cốt"…). Lập bảng "máy nghe → chữ đúng" từ kịch bản và dùng nó khi đối chiếu và khi viết phụ đề. Không tự đoán, không bịa chữ.

## 2. Nhịp cắt (khoảng nghỉ đặt ở ĐẦU đoạn kế tiếp)
**Video YouTube dài dùng ĐÚNG luật của video ngắn; chỗ khác duy nhất là nghỉ khi sang câu mới dài hơn (0,5 thay vì 0,1).**

| Loại video | từ ghép | đoạn (giữa các ý) | sang câu mới |
|---|---|---|---|
| **Ngắn dọc** (TikTok/Shorts/Reels) — nhịp dồn dập | **0,01** | **0,05** | **0,1** |
| **YouTube dài** — chỉ khác ở cột này | **0,01** | **0,05** | **0,5** |

- Cắt **sát tiếng nói**: khung bắt đầu/kết thúc lấy từ **đường sóng âm** (`song_am.py khoi`), đuôi chỉ chừa 1 khung hình. **Không lấy mốc từ bản chép lời** (bản chép lời lệch cả giây, từng làm mất chữ cuối và để lọt khoảng lặng).
- Khoảng nghỉ **lấy từ im lặng thật ngay trước tiếng đầu** của đoạn trong video gốc. Không có im lặng thật thì nghỉ ngắn hơn (đừng chèn khung đen). Báo người dùng những chỗ đó.
- Khoảng lặng nằm **giữa** hai chữ trong cùng đoạn (người nói ngập ngừng) → cắt bỏ luôn khúc lặng, giữ nguyên hai chữ.

## 3. Soi từng đoạn bằng sóng âm trước khi ghi (`song_am.py kiem-cat <video> edl.json`)
Công cụ in cảnh báo; **mỗi cảnh báo phải xử lý hoặc giải thích** trước khi ghi vào CapCut:
- **CẮT SỚM** — tiếng còn kéo dài sau mốc cuối → mất chữ cuối câu (đã từng mất chữ "chưa"). Kéo mốc cuối ra hết khối tiếng.
- **IM LẶNG GIỮA ĐOẠN** > 0,2 giây → cắt bỏ khúc đó.
- **KHỐI LẺ** < 0,3 giây đứng riêng rồi im → thường là hơi thở/tiếng click, **không phải chữ**. Cắt riêng khối đó đưa vào `chep_loi.py`: không ra chữ thì bỏ. **Không bao giờ** tự coi khối lẻ là một chữ của câu.
- Sau khi cắt: ghép các đoạn, chép lời lại, đọc toàn bộ một lần (quy tắc 2).

## 4. Phụ đề bám theo tiếng
- Phụ đề **chỉ hiện lúc có tiếng**, tắt khi im lặng. Chia chữ theo tỉ lệ ký tự **trên thời gian có tiếng** (bỏ khoảng lặng), không kéo dài dòng này sang dòng sau để lấp chỗ trống.
- **Tắt phụ đề ở mọi chỗ ghép video** — sau chỗ ghép chắc chắn là một ý khác. Mỗi đoạn có phụ đề riêng; dòng không được vắt qua chỗ ghép.
- Các dòng phụ đề không chồng nhau (dù 1 ms sẽ sinh thêm track chữ lẻ).

## 5. Âm lượng giọng và SFX
- Giọng thô thường nhỏ, SFX (−10 dB, volume ~0,3) lại to hơn giọng → **tăng giọng**. Đo bằng `song_am.py am-luong <video>`: mức tăng sao cho 99,9% tiếng nói lên khoảng −6,5 dB (CapCut tối đa +15 dB). Dấu hiệu đúng: sóng âm có **vạch cam rải rác ở vài chỗ** (không đầy). Đặt cùng mức cho mọi đoạn video chính (`volume` của đoạn).
- SFX luôn nhỏ hơn giọng; mỗi lúc một tiếng; xoay vòng nhiều loại.

## 6. Chữ nhấn / chữ lớn không đè mặt
- Trước khi đặt chữ: `song_am.py luoi-mat <video> --giay <các giây chữ hiện> --zoom <mức zoom lúc đó>` → **mở ảnh lưới xem** mặt nằm ở % chiều cao nào (đỉnh đầu → cằm; khi người nói cúi đầu cằm xuống thấp hơn).
- Chữ nhấn **không được nằm trong khoảng đỉnh đầu → cằm** (kể cả khi cúi/nghiêng). Ưu tiên **trên đầu** (video dọc ≈ 19% từ trên xuống), chỗ trống cả ở mọi khung. Không đủ chỗ thì đặt dưới cằm, cách ≥ 5% chiều cao.
- Phụ đề dưới thường nằm ngay dưới cằm: kiểm tra nó cũng không đè khi người nói cúi.

## 7. Motion graphic bắt buộc có hình
- Mỗi motion graphic phải có **1 hoặc 2 hình** (hình vẽ sẵn: `tia-sang, thu-muc, dong-thoi-gian, video, chat, tick, mui-ten-len`, hoặc **file ảnh thật** — ảnh chụp màn hình, logo, ảnh lấy từ web). **Không làm thẻ chỉ có chữ.**
- Chọn hình **đúng nghĩa câu đang nói**. Thêm `"anh": ["tia-sang", "dong-thoi-gian"]` trong `mg.json` (hoặc `--anh "a|b"` khi xem thử). Quên khai báo → công cụ tự gắn hình mặc định và cảnh báo.
- MG phủ kín khung sẽ che mặt, phụ đề và chữ nhấn ở đoạn đó — nói rõ cho người dùng, hỏi có muốn thẻ nhỏ nền trong suốt không.

## 8. Quy trình nhanh
chép lời → chọn đoạn (kịch bản + từ điển) → **đo sóng âm lấy mốc** → `kiem-cat` → người dùng duyệt danh sách giữ/bỏ → `cat` → ghép lại, chép lời lại, đọc toàn bộ → phụ đề bám tiếng (tắt ở chỗ ghép) → zoom → `luoi-mat` đặt chữ nhấn → SFX → đặt âm lượng giọng bằng `am-luong` → motion graphic có hình → `kiem` → người dùng xem trong CapCut.

## 9. Bài học từ phiên thử (vì sao có các luật trên)
- **Mốc từ bản chép lời không đủ chính xác:** nó từng làm mất chữ cuối câu ("chưa") và để lọt khoảng lặng ~1 giây vào video. Mốc phải lấy từ sóng âm.
- **Không suy đoán một khối âm thanh lẻ là chữ.** Một khối 0,11 giây từng bị tưởng là chữ "Bước" nhưng thực ra là tiếng động; chữ thật nằm ở khối sau. Chép riêng khối đó để kiểm chứng.
- **Người nói quay nhiều lần cùng một câu:** lần cuối thường trơn nhất, nhưng phải đọc lại bản đã ghép mới biết có lặp hay không; từng lặp "Cuối cùng", "Bước bốn" vì chọn đoạn còn dư vài chữ đầu/đuôi.
- **Chữ đặt cố định dễ đè mặt:** vị trí mặt đổi theo zoom và cúi đầu; đo bằng ảnh lưới trước khi đặt.
- **Giọng thô nhỏ, SFX mặc định to hơn giọng:** luôn đo và tăng giọng.
- **Đừng ghi vào dự án khi người dùng chưa duyệt danh sách giữ/bỏ**, và CapCut phải đóng hẳn; ghi hỏng thì khôi phục từ `_backup_junops`.
