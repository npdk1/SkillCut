---
name: junops-edit-capcut
description: Skill JunOps — để Claude edit video ngay trong CapCut bản máy tính (Windows), cho CẢ video ngắn dọc (TikTok/Shorts/Reels) lẫn video ngang dài (YouTube 16:9). Cắt chỗ nói vấp và khoảng lặng, phụ đề (ngắn cho video dọc, theo cả câu cho YouTube), chữ nhấn mạnh, hiệu ứng âm thanh (SFX), zoom in/out vào chữ quan trọng, chữ quan trọng không đè mặt, và motion graphic vẽ bằng code (thẻ tiêu đề, danh sách, con số đếm tăng, thẻ phần). Lần đầu dùng Claude tự cài công cụ cần thiết. Mọi thứ ghi thẳng vào dự án CapCut thật nên người dùng mở CapCut lên sửa lại được. Dùng khi người dùng nói "bắt đầu", "dùng skill JunOps", gửi một thư mục video thô (+ kịch bản) hoặc một file video thô, hoặc nói "edit video này", "dựng video trong CapCut", "edit video YouTube", "video dài", "thêm phụ đề / chữ nhấn mạnh / SFX / zoom", "cắt chỗ nói vấp", "cắt khoảng lặng", "làm motion graphic", "thêm thẻ tiêu đề / con số / danh sách", "học phong cách edit của mình".
---

# Chào mừng bạn đã sử dụng skill JunOps

Skill này giúp Claude edit video trong **CapCut bản máy tính** (video dọc TikTok/Shorts và video ngang YouTube): ghi thẳng vào file dự án CapCut, nên bạn mở CapCut lên vẫn kéo, cắt, đổi chữ, xoá được như video bình thường.

**Cách dùng:** người dùng chỉ cần đưa **thư mục video thô + file kịch bản**, hoặc **chỉ một file video thô** — Claude dẫn từng chặng cho tới khi ra file hoàn chỉnh (xem mục «Dẫn dắt» ngay bên dưới).

**Tính năng cơ bản:** cắt chỗ nói vấp và khoảng lặng · phụ đề · chữ nhấn mạnh · hiệu ứng âm thanh (SFX) · font · zoom in / zoom out · **motion graphic** (4 mẫu, xem mục riêng bên dưới).

**Không có sẵn:** font, SFX, nhạc, hay kiểu chữ nào kèm theo skill. Skill chỉ dùng những gì **đã có trong CapCut của chính bạn** (Claude tự quét và chọn, hoặc bạn chỉ định). Skill **không tách nền**. Motion graphic do skill **tự vẽ bằng code** (kèm 1–2 hình vẽ sẵn hoặc ảnh của bạn).

## ⚖️ LUẬT CẮT GHÉP — ĐỌC `references/LUAT_CAT_GHEP.md` TRƯỚC KHI CẮT (bắt buộc)

Tóm tắt (chi tiết và lý do trong file đó):
1. **Mỗi câu kịch bản đúng 1 lần, không lặp, không ghép chữ lẻ/cắt giữa cụm, có từ điển chữ tiếng Anh/tên riêng.** Cắt xong **phải ghép các đoạn, chép lời lại và đọc toàn bộ một lượt** để bắt câu lặp/thiếu.
2. **Nhịp (khoảng nghỉ đặt ở đầu đoạn kế tiếp):** **video ngắn dọc và YouTube dài dùng CHUNG một bộ luật cắt ghép**, chỉ khác khoảng nghỉ khi sang câu mới: từ ghép **0,01** · đoạn **0,05** · sang câu **0,1 giây** (video ngắn) hoặc **0,5 giây** (YouTube dài). Cắt **sát tiếng nói bằng sóng âm**, không lấy mốc từ bản chép lời. Nghỉ lấy từ im lặng thật; không có thì ngắn hơn và báo người dùng.
3. **Soi bằng sóng âm trước khi ghi:** `python scripts/song_am.py kiem-cat "<video>" edl.json` — xử lý hết cảnh báo (cắt sớm mất chữ cuối, im lặng giữa đoạn, khối âm thanh lẻ là tiếng động).
4. **Phụ đề chỉ hiện lúc có tiếng, tắt ở mọi chỗ ghép video.**
5. **Giọng nói phải to hơn SFX:** `python scripts/song_am.py am-luong "<video>"` rồi đặt âm lượng giọng theo kết quả (vạch cam rải rác ở vài chỗ là đúng); SFX giữ ~−10 dB.
6. **Chữ nhấn không đè mặt:** `python scripts/song_am.py luoi-mat "<video>" --giay ... --zoom ...` rồi **xem ảnh lưới**, đặt chữ ngoài khoảng đỉnh đầu → cằm (ưu tiên trên đầu).
7. **Motion graphic bắt buộc có 1–2 hình** (hình vẽ sẵn hoặc file ảnh thật), không làm thẻ chỉ có chữ.

## 🧭 DẪN DẮT TỪ ĐẦU ĐẾN KHI RA FILE HOÀN CHỈNH (Claude chủ động)

Người dùng có thể là người mới hoàn toàn. Ngay khi skill được dùng — kể cả khi người dùng chỉ nhắn «bắt đầu», «dùng skill», «edit video», hoặc chỉ gửi một đường dẫn thư mục/file — Claude **chủ động dẫn từng chặng**. Mỗi lượt chỉ nói **một việc** người dùng cần làm, bằng lời đơn giản, rồi chờ. Không bắt người dùng đọc tài liệu.

**Câu mở đầu** (khi người dùng chưa đưa gì): «Chào bạn! Mình sẽ giúp bạn edit video trong CapCut từ đầu đến khi ra **file hoàn chỉnh**. Bạn gửi mình **một trong hai thứ** nhé: (1) **thư mục** chứa video thô + file kịch bản (nếu có), hoặc (2) **chỉ một file video thô**. Kéo thả thẳng vào khung chat là được.»

| Chặng | Claude làm | Người dùng làm |
|---|---|---|
| **1. Nhận đầu vào** | Chạy `python scripts/quet_dau_vao.py "<thư mục hoặc file>"`. Tóm tắt 2–3 dòng: có mấy video, dọc hay ngang (→ mục A hay B), có kịch bản không. Chỉ hỏi những gì không tự biết: **nhiều video thì làm riêng hay ghép theo thứ tự tên**, **file nào là kịch bản**, **không có kịch bản thì có muốn dán ý chính không** (không bắt buộc). | Gửi thư mục/file; trả lời 1–2 câu |
| **2. Chuẩn bị máy** | Làm mục «Lần đầu dùng» bên dưới (chỉ lần đầu). | Bấm đồng ý khi Claude hỏi quyền chạy lệnh |
| **3. Tạo dự án CapCut** | Nói **đúng từng thao tác** rồi chờ. Sau khi người dùng nhắn «xong», chạy `python scripts/junops_capcut.py list` để chắc dự án có video và CapCut đã đóng. | **Việc duy nhất làm tay trước khi edit:** «Mở CapCut → Dự án mới → kéo file *<tên file>* vào dòng thời gian (nhiều video: kéo lần lượt theo thứ tự) → đặt tên dự án (ví dụ VIDEO 01) → **đóng hẳn CapCut**, chờ ~30 giây → nhắn mình *xong* kèm tên dự án.» |
| **4. Claude edit** | Theo mục A (dọc) hoặc B (YouTube): chép lời → **có kịch bản thì dùng kịch bản để chọn đúng lần nói cho từng câu** (thường là lần nói sau cùng), không kịch bản thì chọn lần trơn nhất → đưa **danh sách giữ/bỏ ngắn gọn** để duyệt → cắt → phụ đề → zoom → chữ nhấn → SFX. Hỏi người dùng có muốn **motion graphic** không; gợi ý chỗ hợp từ kịch bản (tiêu đề mở đầu, chỗ liệt kê, chỗ có con số, chỗ đổi phần). Mỗi bước: xem trước (`--dry-run`) → người dùng đồng ý → ghi. Báo tiến độ «Chặng 4 — bước x/y». | Duyệt danh sách giữ/bỏ; trả lời «ừ/đổi chỗ này» |
| **5. Xem và chỉnh** | Dặn: «Mở CapCut → mở dự án *<tên>* → bấm phát xem. Chỗ nào chưa ưng thì tự kéo/đổi chữ trong CapCut, hoặc nhắn mình sửa — **nhớ đóng CapCut trước khi nhắn**.» Sửa theo yêu cầu cho đến khi người dùng ưng. | Xem video, nói chỗ cần sửa |
| **6. Xuất file hoàn chỉnh** | Dặn cách xuất (bên cạnh). Khi người dùng gửi đường dẫn file đã xuất: chạy `python scripts/kiem_tra.py "<file>"`, báo kết quả (khung đen/đứng hình), nhắc **xem lại bằng mắt** trước khi đăng. Kết thúc bằng tên + nơi lưu file hoàn chỉnh. | «Trong CapCut bấm **Xuất** (Export) → 1080p (4K nếu video gốc 4K), 30 hoặc 60 khung/giây → chọn thư mục lưu → Xuất», rồi gửi đường dẫn file |

**Nói thẳng 2 điều** (đúng ở chặng 3 và 6, không giấu): Claude **không tự tạo dự án CapCut** và **không tự bấm Xuất** — hai việc đó người dùng bấm trong CapCut; mọi thứ ở giữa là Claude làm.

**Quy tắc dẫn dắt:** luôn nói «Chặng x/6» ngắn gọn + đúng **một** việc người dùng cần làm · dùng tên nút đúng như trong CapCut · không hỏi lại điều tự quét được · người dùng lạc hướng thì kéo về chặng đang dở · nếu người dùng gửi thứ không phải video/kịch bản thì hỏi lại · công cụ tự từ chối ghi khi CapCut đang mở, đừng vượt qua.

## Lần đầu dùng — Claude TỰ làm, người dùng KHÔNG phải gõ lệnh cài đặt

Khi người dùng nhờ edit video lần đầu (hoặc chưa có file `du_lieu/kho_mau.json` trong thư mục skill), Claude **tự** làm theo thứ tự, chạy lệnh từ thư mục của skill này, và chỉ báo ngắn gọn:

1. **Cài công cụ:** `python scripts/cai_dat.py --cai` (tự cài faster-whisper, pillow, numpy; thiếu ffmpeg thì tự chạy `winget install -e --id Gyan.FFmpeg`). Người dùng chỉ bấm đồng ý khi hỏi quyền chạy lệnh. Nếu vừa cài ffmpeg xong mà vẫn báo thiếu → bảo người dùng **mở lại cửa sổ Claude** rồi làm tiếp. Lần đầu chép lời sẽ tải mô hình tiếng Việt vài trăm MB — nói trước để người dùng yên tâm chờ.
2. **Học CapCut của người dùng:** `python scripts/junops_capcut.py hoc` rồi `mau`. Nếu báo **chưa có kiểu chữ hoặc SFX nào** thì chỉ nói đúng một câu: «Bạn mở CapCut, ở BẤT KỲ dự án nào thêm 1 dòng chữ (đúng font/màu bạn thích) và 1 hiệu ứng âm thanh, rồi đóng hẳn CapCut và nhắn mình *xong*» — sau đó chạy lại `hoc`.
3. **Quay lại dòng chặng ở trên:** tiếp tục chặng 3 (tạo dự án CapCut). Không giải thích dài.

Người dùng **không cần** nhắn câu «cài giúp mình các công cụ…». Dùng `chon --phu-de t2 --nhan-manh t5` nếu người dùng muốn đổi kiểu chữ phụ đề / chữ nhấn mạnh.

## A. Mỗi video NGẮN DỌC (TikTok / Shorts / Reels) — Claude làm theo thứ tự

0. **Xác nhận đầu vào với người dùng:** tên dự án CapCut (đã tạo, đã kéo video thô vào dòng thời gian), dòng thời gian được phép sửa (mặc định: dòng trống hoặc một bản sao, KHÔNG sửa bản đã chốt), có kịch bản không. Nhắc người dùng **đóng hẳn CapCut** (chờ vài chục giây).
1. **Chép lời:** `python scripts/chep_loi.py "<video thô>"` → đọc file `_loi.txt`.
2. **Chọn đoạn giữ lại:** mỗi câu chọn **lần nói trơn nhất (thường là lần nói sau cùng)**, bỏ lần nói vấp/hụt, bỏ khoảng lặng dài. Có thể bắt đầu bằng `python scripts/tao_edl_bo_lang.py <file_loi.json>` rồi sửa `edl.json` bằng tay. **Cho người dùng xem danh sách giữ/bỏ và chờ duyệt** trước khi ghi.
3. **Ghi các đoạn đã cắt:** `python scripts/junops_capcut.py cat "<dự án>" --edl edl.json --dry-run`, thấy ổn thì bỏ `--dry-run`. Lệnh này tạo `ban_do_cat.json` (giây video thô ↔ giây dòng thời gian).
4. **Phụ đề tự động:** `python scripts/tao_phu_de.py <file_loi.json> ban_do_cat.json` → `plan_phu_de.json`.
5. **Chữ nhấn mạnh, SFX, zoom:** tự viết `plan.json` (mẫu bên dưới). Mốc thời gian trong plan là **giây trên dòng thời gian SAU khi cắt**: đổi từ giây trong lời gốc bằng `python scripts/doi_moc.py ban_do_cat.json <giây thô>`.
6. **Ghi:** `python scripts/junops_capcut.py apply "<dự án>" --plan plan.json --dry-run` rồi chạy thật (gộp `plan_phu_de.json` vào `plan.json` hoặc chạy lần lượt).
7. **Người dùng mở CapCut xem, sửa tay nếu cần, rồi xuất.** Sau khi xuất: `python scripts/kiem_tra.py <video.mp4>`.

### Mẫu plan.json
```json
{"ops": [
  {"op": "chu", "mau": "nhan_manh", "start": 3.0, "dur": 1.2, "text": "TỪ QUAN TRỌNG"},
  {"op": "chu", "mau": "phu_de",    "start": 5.0, "dur": 2.0, "text": "câu phụ đề"},
  {"op": "sfx",  "at": 3.0},
  {"op": "sfx",  "at": 5.0, "mau": "s2", "volume": 0.25},
  {"op": "zoom", "at": 10.0, "muc": 1.15, "giu": 1.0, "vao": 0.3, "ra": 0.4}
]}
```
- `chu`: `mau` là `phu_de`, `nhan_manh`, `chu_to` hoặc id kiểu chữ (t1, t2…). Tuỳ chọn `x`, `y`, `scale`.
- `sfx`: `mau` bỏ trống/`auto` = tự lấy lần lượt trong kho SFX của người dùng (không lặp liền nhau); hoặc id (s1, s2…).
- `zoom`: phóng to rồi trả về cũ ở đoạn video chính đang chạy tại `at` (dạng đầy đủ: `points` = [[giây, tỉ lệ], …]).

## Video ngang dài (YouTube) khác video dọc ở đâu

**Có gì khác video dọc (mục A):**
- Phụ đề mỗi lần hiện **cả một câu** (dài quá thì tách 2 lần hiện), chữ **trắng** — không cắt vụn 4 chữ.
- **Zoom ở chỗ cắt cảnh:** các đoạn kề nhau xen kẽ cỡ khung (vd 100% → 112% → 100% → 122%) để chỗ cắt trông như đổi góc máy.
- **Zoom vào chỗ nói quan trọng:** phóng nhẹ rồi trả về, tính theo cỡ khung của đoạn đó.
- **Chữ quan trọng** đặt ở phía đối diện khuôn mặt, không đè lên mặt.

## B. Mỗi video NGANG DÀI (YouTube 16:9) — luôn `--dry-run` xem trước, người dùng đồng ý mới ghi

0. **Xác nhận đầu vào:** tên dự án CapCut (đã kéo video thô vào dòng thời gian), dòng thời gian được phép sửa (dòng trống/bản sao, KHÔNG sửa bản đã chốt), có kịch bản không. Nhắc người dùng **đóng hẳn CapCut**.
1. **Chép lời + cắt ghép** như mục A (`chep_loi.py` → chọn đoạn giữ → `junops_capcut.py cat`). Với YouTube **áp đúng luật cắt ghép của video ngắn** (xem `references/LUAT_CAT_GHEP.md`), chỉ khác nghỉ sang câu mới là **0,5 giây** (thay vì 0,1); nghỉ ở đầu đoạn kế tiếp, lấy từ im lặng thật; bỏ khoảng lặng dài và lần nói vấp; mỗi câu chọn lần nói trơn nhất (thường là lần sau cùng). Mốc cắt lấy từ sóng âm (`song_am.py`), xem `references/LUAT_CAT_GHEP.md`. Cho người dùng xem danh sách giữ/bỏ và chờ duyệt.
2. **Phụ đề theo câu:**
   `python scripts/youtube_junops.py phu-de-cau "<dự án>" --loi <file_loi.json> --ban-do ban_do_cat.json --dry-run` → xem vài dòng mẫu → bỏ `--dry-run`.
   Chữ trắng mặc định; muốn giữ màu kiểu chữ đã học: `--mau-chu giu`. Độ dài tối đa: `--toi-da 64`.
3. **Zoom ở chỗ cắt cảnh:** `python scripts/youtube_junops.py zoom-noi "<dự án>"` (đổi vòng cỡ khung bằng `--muc 1.0,1.12,1.0,1.22`). **Làm bước này trước bước 4.**
4. **Zoom vào chỗ nói quan trọng:** đổi giây trong lời sang giây dòng thời gian bằng `doi_moc.py`, rồi
   `python scripts/youtube_junops.py zoom-chu "<dự án>" --diem 12.5,31.0,58.2` (mặc định phóng thêm 12%, vào 0,3s, giữ 1s, ra 0,4s; tối đa 1,5 lần). Không zoom liên tục: tối đa ~4–5 chỗ mỗi phút, cách nhau ít nhất 5 giây.
5. **Chữ quan trọng không đè mặt:**
   - **Xem mặt người nói nằm ở đâu trong khung:** lấy một khung hình từ video thô (`ffmpeg -ss 5 -i "<video>" -frames:v 1 khung.jpg`) rồi mở ảnh xem; hoặc **hỏi người dùng** "bạn ngồi bên trái, giữa hay bên phải khung hình?".
   - Viết `chu.json`: `[{"at": 12.5, "dur": 1.5, "text": "TỪ QUAN TRỌNG"}]` (mỗi chữ tối đa 1–4 từ).
   - `python scripts/youtube_junops.py chu-quan-trong "<dự án>" --chu chu.json --mat trai|giua|phai` — `--mat` là phía **mặt đang ở**; chữ tự đặt phía đối diện (mặt ở giữa thì chữ luân phiên trái/phải). Có thể ghi đè từng chữ bằng `x`, `y` trong json.
   - Chỉ nhấn 1–2 từ quan trọng nhất của câu, không lạm dụng.
6. **SFX:** dùng `junops_capcut.py apply` như mục A (plan.json, op `sfx` để `mau` tự xoay vòng). Mỗi lúc một tiếng, nhỏ (volume ~0,3), đặt ở chỗ cắt cảnh/chữ hiện.
7. **Motion graphic (tuỳ chọn):** theo mục «Motion graphic» bên dưới — `python scripts/mg_junops.py chen "<dự án>" --mg mg.json --dry-run`. Video ngang tự vẽ khung 1920×1080. Mở đầu dùng `tieu-de`, đổi phần dùng `the-phan`, chỗ nói con số dùng `so-lieu`. Làm **sau** bước cắt + zoom.
8. **Kiểm tra:** `python scripts/youtube_junops.py kiem "<dự án>"`. Người dùng mở CapCut xem, sửa tay, xuất; sau đó `python scripts/kiem_tra.py <video.mp4>` (khung đen/đứng hình).

Thứ tự chạy: **cắt → phụ đề → zoom-noi → zoom-chu → chữ quan trọng → SFX → motion graphic → kiểm tra.** Không chạy lại `zoom-noi` sau khi đã `zoom-chu` (phải khôi phục backup rồi làm lại theo thứ tự).

## Motion graphic (4 mẫu vẽ bằng code)

Skill **tự vẽ** motion graphic bằng code (hình minh hoạ cũng vẽ bằng code, hoặc dùng file ảnh thật của người dùng) rồi đặt lên một track riêng tên «MG JunOps» ở **trên cùng** dòng thời gian — người dùng kéo, cắt, xoá được như mọi đoạn khác. 4 mẫu:

**Mọi MG bắt buộc có 1–2 hình** (trường `anh`): tên hình vẽ sẵn `tia-sang`, `thu-muc`, `dong-thoi-gian`, `video`, `chat`, `tick`, `mui-ten-len`, hoặc đường dẫn **file ảnh thật** (ảnh chụp màn hình, logo, ảnh lấy từ web). Chọn hình đúng nghĩa câu đang nói. Quên khai báo → công cụ tự gắn hình mặc định và cảnh báo. Ví dụ: `"anh": ["tia-sang", "dong-thoi-gian"]`.

| `loai` | Hiện gì | Trường cần |
|---|---|---|
| `tieu-de` | thẻ tiêu đề lớn + gạch nhấn + dòng phụ | `chu`, (`phu`) |
| `danh-sach` | tiêu đề + 2–6 ý hiện lần lượt | `chu` (tiêu đề), `muc` (mảng các ý) |
| `so-lieu` | con số lớn **đếm tăng dần** (85%, 1.250.000, 3,5 tỷ…) + nhãn | `so`, (`chu` = dòng nhỏ phía trên, `phu` = nhãn phía dưới) |
| `the-phan` | thẻ phần/chương «PHẦN 02» + tên phần | `so`, `chu`, (`phu`, `nhan`) |

Quy trình (Claude làm, **luôn xem trước bằng `--dry-run`**):
1. Hỏi người dùng cần MG ở đâu: những **giây** trên dòng thời gian (sau khi đã cắt), loại nào, chữ gì. Gợi ý: mở đầu (`tieu-de`), chỗ liệt kê nhiều ý (`danh-sach`), chỗ nói con số (`so-lieu`), chuyển phần (`the-phan`). Ít thôi — mỗi phút tối đa 1–2 MG.
1b. **HỎI MÀU TRƯỚC KHI VẼ (bắt buộc, chỉ hỏi một lần cho cả video):** hỏi người dùng **màu nền** và **màu chữ** muốn dùng, đưa **5 gợi ý** và nói rõ **1 cái khuyến nghị**:

   | # | Bảng màu (`--bang-mau`) | Nền | Chữ | Nhấn | Hợp khi |
   |---|---|---|---|---|---|
   | 1 ⭐ **khuyến nghị** | `toi-vang` | đen | trắng | **vàng** | Hầu hết video: tương phản cao, đọc rõ trên điện thoại, nổi bật con số/từ khoá |
   | 2 | `toi-xanh` | xanh đậm | trắng | xanh dương | Chủ đề công nghệ, tài chính, chuyên nghiệp |
   | 3 | `toi-xanh-la` | xanh rêu đậm | trắng | xanh lá | Sức khoẻ, môi trường, tăng trưởng |
   | 4 | `toi-do` | nâu đỏ đậm | trắng | đỏ cam | Cảnh báo, khuyến mãi, nội dung mạnh |
   | 5 | `sang` | kem sáng | đen | cam | Video nền sáng, phong cách nhẹ (dễ chói nếu video gốc tối) |

   Người dùng muốn màu riêng thì cho `--nen "#RRGGBB"` (nền), `--chu-mau "#RRGGBB"` (chữ), `--nhan "#RRGGBB"` (nhấn). Người dùng không có ý kiến → dùng **#1**. Vẽ thử một mẫu bằng màu đã chọn (`ve ... --anh-xem`) cho họ xem rồi mới ghi.
2. Viết `mg.json` (xem mẫu bằng `python scripts/mg_junops.py mau-json`):
   `[{"at": 12.0, "loai": "danh-sach", "chu": "Cần chuẩn bị", "muc": ["Máy tính", "Tài khoản Claude"], "dur": 4}]`
   Thêm `"trong_suot": true` để MG **phủ lên video** (nền trong suốt, xuất .mov); mặc định MG **che kín khung** như một thẻ chuyển cảnh.
3. **Xem thử một mẫu trước** khi ghi: `python scripts/mg_junops.py ve tieu-de --chu "..." --anh-xem` (ra ảnh ghép 3 khung `_xem.jpg`) — đưa người dùng xem, ưng mới ghi.
4. `python scripts/mg_junops.py chen "<dự án>" --mg mg.json --dry-run`, rồi bỏ `--dry-run`. Màu: `--bang-mau toi-vang|toi-xanh|toi-xanh-la|toi-do|sang` hoặc `--nen "#101018" --nhan "#FFC828"`. Khung (dọc/ngang) tự theo dự án. Cần `pillow`, `numpy`, `ffmpeg`.
5. Các file MG được lưu ở `Videos\JunOps_MG\<tên dự án>`. **Đừng xoá/đổi tên thư mục này** — CapCut đọc video từ đó.

Giới hạn: chỉ 4 mẫu có sẵn, hiệu ứng đơn giản (hiện/trượt/đếm số), font là font có sẵn trong máy (đổi bằng `--font`). MG quá độ dài dòng thời gian sẽ bị cảnh báo.

## Gợi ý phong cách (mặc định, người dùng đổi tuỳ ý)

- **Phụ đề:** mỗi dòng **tối đa 4 chữ**, đặt giữa khung hình; một cụm quan trọng mỗi dòng nhấn màu khác.
- **Chữ nhấn mạnh:** chỉ dùng cho 1–2 từ quan trọng nhất của câu, không lạm dụng.
- **Zoom:** zoom vào đúng lúc người nói nhắc **chữ quan trọng**, mức 1,10–1,20; không zoom liên tục (người xem dễ chóng mặt).
- **SFX:** nhỏ (volume khoảng 0,2–0,35), mỗi lần một tiếng, không để nhiều tiếng giống nhau liền nhau.
- Chi tiết thêm: `references/PHONG_CACH_GOI_Y.md`.

## Luật an toàn (bắt buộc)

1. **Đóng hẳn CapCut khi ghi.** Công cụ từ chối ghi nếu CapCut đang mở (CapCut sẽ ghi đè phần vừa làm khi đóng).
2. **Luôn có backup** trong `<dự án>/_backup_junops/<giờ>_<việc>`; lỗi thì chép file trong đó đè lại.
3. `apply` chỉ **thêm** chữ/SFX/zoom, không xoá hay sửa đoạn có sẵn. `cat` thay các đoạn của track video chính bằng các đoạn đã cắt (cần backup, đã tự làm). Lần đầu hãy thử trên một dự án nháp hoặc bản sao.
4. Người dùng vừa sửa tay trong CapCut thì phải đóng CapCut trước khi Claude ghi tiếp.

## Giới hạn cần nói thẳng

- Chỉ **CapCut bản máy tính trên Windows** đã thử. CapCut cập nhật có thể đổi cách lưu file khiến công cụ cần chỉnh lại.
- Máy chép lời có thể **nghe sai tên riêng và chữ tiếng Anh**; mốc chữ chỉ gần đúng → vẫn cần nghe lại và xem lại phụ đề.
- `kiem_tra.py` chỉ bắt khung đen/đứng hình, **không** bắt được chữ sai chính tả, chữ đè lên mặt, hay cảnh không hợp lời nói → người dùng xem lại bằng mắt.
- `cat` chỉ cắt track video chính; track âm thanh/video khác (lồng tiếng, B-roll) không tự cắt theo.
- Chép lời có thể nghe sai tên riêng/chữ tiếng Anh → xem lại phụ đề; mốc chữ chỉ gần đúng.
- Vị trí "không đè mặt" là **ước lượng theo phía mặt đang ở** — luôn xem lại trong CapCut, kéo chữ nếu cần.
- `zoom-noi` đổi cỡ khung của TỪNG đoạn video chính; nếu bạn đã chỉnh cỡ khung thủ công thì nó sẽ đè lên (có backup).
- Motion graphic chỉ có 4 mẫu đơn giản; muốn hiệu ứng phức tạp hơn thì làm tay trong CapCut.
- Claude **không nghe được âm thanh**; mọi quyết định về lời nói dựa vào bản chép lời.

## Học từ chỉnh sửa của người dùng

Khi người dùng sửa tay xong và **đóng CapCut**: dùng `python scripts/junops_capcut.py analyze "<dự án>"` để đọc lại, so với bản Claude làm, rồi ghi sở thích mới (cỡ chữ, vị trí, mức zoom, tiếng SFX bị bỏ…) vào `du_lieu/so_thich.md` để lần sau làm theo.
