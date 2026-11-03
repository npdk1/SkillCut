# -*- coding: utf-8 -*-
"""Skill JunOps — chép lời nói thành chữ kèm mốc giây (chạy trên máy bạn, không gửi video đi đâu).

python chep_loi.py <video hoặc âm thanh> [--ra <file.json>] [--model <tên>] [--ngon-ngu vi]

Ra 2 file cạnh file nguồn:
  <tên>_loi.json  — words [bắt đầu, kết thúc, chữ, độ tin cậy, id đoạn], segments, speech (khoảng có tiếng thật)
  <tên>_loi.txt   — dạng dễ đọc: [mm:ss] câu nói  (đưa cho Claude đọc)

Mặc định dùng mô hình tiếng Việt ntgiaky/faster-PhoWhisper-small (tự tải lần đầu, vài trăm MB).
Ngôn ngữ khác: --model small --ngon-ngu en
Cần: pip install faster-whisper
"""
import argparse
import json
import sys
import time
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)
except Exception:
    pass

SR = 16000


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("nguon")
    ap.add_argument("--ra")
    ap.add_argument("--model", default="ntgiaky/faster-PhoWhisper-small")
    ap.add_argument("--ngon-ngu", default="vi")
    ap.add_argument("--luong", type=int, default=0, help="số luồng CPU (0 = tự chọn)")
    a = ap.parse_args()

    try:
        from faster_whisper import BatchedInferencePipeline, WhisperModel
        from faster_whisper.audio import decode_audio
        from faster_whisper.vad import VadOptions, get_speech_timestamps
    except ImportError:
        sys.exit("Chưa cài faster-whisper. Chạy: pip install faster-whisper")

    nguon = Path(a.nguon)
    out_json = Path(a.ra) if a.ra else nguon.with_name(nguon.stem + "_loi.json")
    out_txt = out_json.with_suffix(".txt")

    t0 = time.time()
    model = WhisperModel(a.model, device="cpu", compute_type="int8", cpu_threads=a.luong)
    pipe = BatchedInferencePipeline(model)
    audio = decode_audio(str(nguon), sampling_rate=SR)
    t_nap = time.time() - t0

    sp = get_speech_timestamps(audio, VadOptions(min_silence_duration_ms=100, speech_pad_ms=0, threshold=0.5))
    speech = [[round(x["start"] / SR, 3), round(x["end"] / SR, 3)] for x in sp]

    t1 = time.time()
    segs, _ = pipe.transcribe(audio, language=a.ngon_ngu, batch_size=8, beam_size=5, word_timestamps=True,
                              condition_on_previous_text=False, vad_filter=True,
                              vad_parameters=dict(min_silence_duration_ms=300, speech_pad_ms=300))
    words, segments = [], []
    for i, s in enumerate(segs):
        dur = max(0.01, s.end - s.start)
        n = len(s.words or [])
        nghi = (s.no_speech_prob > 0.6 and s.avg_logprob < -0.8) or n / dur > 10
        segments.append({"id": i, "start": round(s.start, 3), "end": round(s.end, 3), "text": s.text.strip(),
                         "nghi_bia": bool(nghi)})
        for w in s.words or []:
            t = w.word.strip()
            if t:
                words.append([round(w.start, 3), round(w.end, 3), t, round(w.probability, 3), i])

    out_json.write_text(json.dumps({"nguon": str(nguon), "dur": round(len(audio) / SR, 3),
                                    "ghi_chu": "words = [bắt đầu, kết thúc, chữ, độ tin cậy, id đoạn]; speech = khoảng có tiếng thật",
                                    "words": words, "segments": segments, "speech": speech},
                                   ensure_ascii=False, indent=0), encoding="utf-8")
    dong = []
    for s in segments:
        m, g = divmod(int(s["start"]), 60)
        dong.append(f"[{m:02d}:{g:02d}] {s['text']}" + ("  (nghi bịa)" if s["nghi_bia"] else ""))
    out_txt.write_text("\n".join(dong), encoding="utf-8")
    print(f"{nguon.name}: {len(audio) / SR:.0f}s âm thanh · nạp {t_nap:.1f}s · chép {time.time() - t1:.1f}s · {len(words)} chữ")
    print(f"→ {out_json}\n→ {out_txt}")


if __name__ == "__main__":
    main()
