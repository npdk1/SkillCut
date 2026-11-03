# Script and voiceover

## Contents
1. Writing the script
2. script.json
3. Choosing the voice
4. Generating the voiceover
5. Stitching, length and checks
6. Vietnamese videos
7. Short vertical videos (9:16)

## 1. Writing the script

**Length.** Aim for about 150 spoken words per finished minute (a natural TTS read is 130-140 wpm; stitching can speed it up gently, up to 1.15x). So 1 min = 150 words, 3 min = 450, 5 min = 750, 8 min = 1,200, 10 min = 1,500. Tell the viewer the word count and estimated length when you present the script.

**Research first.** For a true story or explainer, search the web and keep the sources. Every number, date and name in the script should trace to a source; if sources disagree, say "around" or pick the most reliable one and note it. Give the viewer the source list with the script (it also goes in their video description).

**Structure that holds attention:**
- Hook, first 10-15 seconds: lead with the most surprising true fact, stated plainly, then promise the story. Speak the video's main search phrase (the topic name people would type into YouTube) inside the first 15 seconds, naturally. YouTube reads the transcript, so spoken keywords early help the video get found.
- Context: just enough background to follow (who, where, why it mattered).
- 3-6 escalating beats, each ending on a turn ("Then...", "But...", "So...").
- Payoff: the outcome or the twist.
- Close: one line that lands the point, then a short call to action (one sentence).

**Write for the ear and for pictures:**
- Short sentences (mostly under 20 words). One idea per sentence, because each sentence usually becomes one shot.
- Concrete, drawable nouns and actions. "Soldiers loaded two machine guns onto a truck" is a picture; "the situation escalated" is not.
- Spell things the way they should be said: "World War One" not "WWI", "Doctor" not "Dr.", avoid symbols and abbreviations the voice might read oddly. Digits are fine for numbers and years ("1932", "20,000").
- No stage directions, headings or brackets in the text the voice reads.
- Humour and pauses come from rhythm: a very short sentence after a long one ("And the emus won.") lands as a beat.

**Scenes.** Split the script into 6-12 scenes at natural paragraph breaks (one beat each). Every scene must stay under 1,900 characters, because Higgsfield's voice model takes at most 2,048 characters per request. Scene breaks also become slightly longer pauses in the read.

**Approval.** Show the full script (scene by scene), word count, estimated length and sources. Wait for approval or edits before generating audio: changing words after the voiceover exists costs a regeneration.

## 2. script.json

Save the approved script as `work/<slug>/script.json`:
```json
{"title": "The Great Emu War", "keyword": "Great Emu War",
 "scenes": [{"n": 1, "text": "In 1932, Australia sent soldiers with machine guns to fight a war against 20,000 emus. And the emus won. This is the true story of the Great Emu War."},
            {"n": 2, "text": "After World War One, ..."}]}
```
The scene texts must be exactly what the voice reads. Everything downstream (timing, shot list, word indexes) is keyed to these words.

## 3. Choosing the voice

Call `list_voices` (size 50, page with `next_cursor` if needed). Pick three that suit narration for this topic (for example a warm documentary voice, an energetic storyteller, a calm explainer) and show each with its name and `preview_url` so the viewer can listen. If they have their own cloned voice it shows up as `voice_type: "element"`. If they say "you pick", choose the clearest warm narrator and say which.

## 4. Generating the voiceover

Model `seed_audio` with the chosen `voice_type` + `voice_id`. One request per scene, sent together with `generate_audio_batch` (up to 12 per call):
```json
{"index": 1, "params": {"model": "seed_audio", "prompt": "<scene 1 text>", "voice_type": "preset",
  "voice_id": "<id>", "format": "wav", "sample_rate": 48000}}
```
- `speech_rate` (0 = normal, positive = faster, about +10 is noticeably brisker) is the clean way to change pace. Use it if the viewer wants a faster read or the first scene runs well over the target pace.
- Wait with `jobs_wait` (groups of up to 12), then write a list file `work/<slug>/vo/urls.txt` with lines `scene01 <url>` and download:
  ```bash
  python3 scripts/prep_images.py download --list work/<slug>/vo/urls.txt --dir work/<slug>/vo
  ```
  (the download command works for any file type and names each file by its real format, e.g. `scene01.wav` or `scene01.mp3`; use the names it prints in the stitch command).
- If a submission times out, don't resubmit blindly: check the returned job ids first.

## 5. Stitching, length and checks

```bash
python3 scripts/stitch_vo.py --script work/<slug>/script.json \
  --clips work/<slug>/vo/scene01.wav work/<slug>/vo/scene02.wav ... \
  --out work/<slug>/vo/voiceover.wav --target-seconds <minutes x 60>
```
It trims each clip, joins them with half-second scene pauses, nudges the speed (0.87x-1.15x) to hit the target length, levels to -16 LUFS and writes `scenes.json` next to the output. If the natural read is too far from the target it keeps the natural speed and tells you; then trim or extend the script, or regenerate with `speech_rate`. Long voiceovers (over 28 MB) also get an `.m4a` copy: deliver and reference that one.

Then time the words (next step in SKILL.md):
```bash
python3 scripts/align_vo.py --scenes work/<slug>/vo/scenes.json --out work/<slug>/timing/words.json --names "proper nouns, comma separated"
```
With whisper available it prints how many script words it heard and lists the ones it didn't. A cluster of unheard words usually means the voice mispronounced, slurred or skipped something there. Tell the viewer the timestamp so they can listen, and offer to regenerate that one scene (spell the tricky word phonetically). Isolated unheard numbers or names are normally fine (whisper writes them differently).

It also notes any pause longer than 1.5 s inside a sentence (TTS voices sometimes add a dramatic pause). Either keep it and plan a beat there in the edit, or regenerate that scene.

Send the voiceover to the viewer (SendUserFile) so they can listen while you carry on. Regenerating one scene later is cheap; just re-run stitch, align and the shot timing afterwards because every timestamp moves.

## 6. Vietnamese videos

**Rate.** Count tiếng (each space-separated word is one syllable): aim for about 200 tiếng per finished minute as a starting point (30 s = 100, 60 s = 200, 3 min = 600). TTS voices differ, so generate scene 1 first, read the rate that `stitch_vo.py` prints, and adjust the rest of the script before generating it.

**Writing for the ear in Vietnamese:**
- Always full diacritics (tiếng Việt có dấu). The script text is what the voice reads AND what the captions and word timing match, so no unaccented words anywhere.
- Numbers: years and counts as digits are fine ("năm 2026", "20.000 người": Vietnamese uses a dot for thousands), but write "hai phẩy năm" if a decimal must be read a certain way, and "phần trăm" rather than relying on "%".
- Spell out abbreviations: "Thành phố Hồ Chí Minh" not "TP.HCM", "khoảng" not "~".
- English product and tech names (CapCut, iPhone, gimbal) are fine, but voices often mispronounce them. Listen to the test scene; if a name comes out wrong, write it the way it sounds only in the spoken text and keep the real name in captions.
- Keep sentences short and spoken ("mình", "bạn" read naturally); avoid long written-style clauses.

**Voice model.** `seed_audio` voices are mostly English and Chinese, so don't assume they read Vietnamese well. Options on Higgsfield (check `models_explore` for the current list and `get_cost` for prices):
- `qwen_audio_tts` with `"language": "vi"`: preset voices or the viewer's own cloned voice (`voice_type: "element"`), plus an `instruction` (max 128 characters) for tone, e.g. "giọng kể chuyện ấm áp, nhịp vừa phải". Its `speech_rate` is a multiplier (1 = normal, 1.1 = a little faster).
- `elevenlabs_v4_turbo`: one voice, `dialogue: [{"text": "<scene text>", "voice_type": "...", "voice_id": "..."}]`.
- If the viewer has cloned their own voice on Higgsfield (`create_voice`), offer it first: a Vietnamese channel usually wants its own voice.
Generate ONE scene with two candidate voices first, send both, and let the viewer pick before generating the rest. Then generate the other scenes with exactly the same model, voice and settings, so the read sounds continuous.

**Timing.** `script.json` carries `"lang": "vi"`; stitch_vo copies it into scenes.json and align_vo then uses the multilingual whisper model with `language="vi"` (run `check_env.py --whisper --lang vi` once) and counts one syllable per word in the pause-based fallback. Word matching ignores tone marks and accents, so whisper writing a name slightly differently still matches the script. A cluster of unheard words still means a misread: listen there.

## 7. Short vertical videos (9:16)

- Length: 30-90 s. One topic, one promise. Vietnamese 60 s is about 200 tiếng, English about 150 words.
- Hook in the first 2 seconds: the most surprising fact or a direct question to the viewer, said in the first sentence, no greeting or channel intro.
- 2-4 scenes, each one beat; the last line is a short payoff, then at most one short call to action.
- Keep every sentence short (under about 12 words / 15 tiếng): the shot changes every 1.5-3 s.
- `--target-seconds` in stitch_vo matters more here: trim the script rather than speeding the read past 1.1x.
