# Troubleshooting

**CapCut shows an empty timeline after installing.** CapCut was running while the files were written, or it was opened before the write finished, and it saved its own copy over ours. Ask them to quit CapCut, check the project's `draft_info.json` (or `draft_content.json`) size and md5 against `build_report.json`, reinstall, then open CapCut.

**"Media missing" / red clips in CapCut.** A file moved or the path is wrong. Compare `build/device_paths.txt` with the real files (route B: check each with `device_bash`). Common causes: the viewer moved or renamed the media folder after importing, the Downloads folder was cleaned, a path_map prefix was wrong (missing trailing slash, mount path used instead of the real path). Fix the plan or move the files back, rebuild, reinstall. In CapCut they can also relink a missing file by clicking it.

**Encrypted project.** The timeline file doesn't start with `{`. Some CapCut builds (notably the Chinese edition, JianYing 6 and later) encrypt projects, and they can't be edited from outside. Tell the viewer plainly. Options: use the international CapCut desktop app, or take the delivered media and preview MP4 and assemble manually using the shot table.

**The project can't be found by name.** CapCut only saves the name after the project is created and closed. Ask them to check the exact name (case and spaces matter), open the project once, rename it, quit, and try again. If they moved CapCut's projects folder, CapCut shows the location in its settings (Projects / Draft location).

**Captions look a little different in CapCut than in the preview.** The preview measures with the bundled Metropolis font plus a 7% safety margin, so real captions are slightly narrower and always fit. For pixel-exact measuring on Mac, stage `/Applications/CapCut.app/Contents/Resources/Font/SystemFont/en.ttf` and pass `--capcut-font`.

**Captions use a different font on Windows.** On Windows the builder leaves the font path empty so CapCut uses its default font. If CapCut picks something else, ask the viewer to add any text to the project's timeline once (then quit): the builder copies the font path CapCut writes for that text. Or pass `--font-path-in-draft "C:/Users/<name>/AppData/Local/CapCut/Apps/<version>/Resources/Font/SystemFont/en.ttf"`.

**Sound effects too loud or too quiet.** Change `level` for that cue (hit > accent > soft > bed > low, about 3 dB apart) or give a number in dB relative to the voice. The builder already caps every effect's peak at -4 dBFS.

**Music too loud under the voice.** Lower `target_lufs` (for example -32). Too quiet: -28.

**A cue lands early or late.** Check the word in `words.txt`. With pause-based timing (no whisper) a few words inside long sentences can be off by up to about 0.3 s; sentence starts and cuts are exact. Use a nearby cut (`cN`), shift with an offset (`w120+0.2`), or install faster-whisper (`check_env.py --whisper`) and re-run `align_vo.py`.

**Whisper reports many unheard words in one place.** The voice probably garbled a line. Regenerate that scene (spell the word phonetically), then re-run stitch, align, plan_shots, normalize and the build, since every time after it moves.

**The image model keeps putting text in images.** Repeat "no text, no letters" and replace the object that invites text ("a blank sign", "an envelope without writing", "a newspaper with unreadable grey lines").

**Every shot shows the whole cast.** The full sheet was attached. Attach only the per-character references for the characters in that shot and write "ONLY <names>" in the prompt.

**Higgsfield downloads fail.** The network setting for code execution blocks the result domain. See setup.md section 5.

**`device_commit_files` refuses a write (mtime changed).** CapCut (or the viewer) changed the project after you copied it. Ask them to quit CapCut, copy the project again, rebuild and install.

**Windows: the installer window closes immediately or is blocked.** Double-click `install_windows.bat` again from the unzipped folder (not from inside the zip); if SmartScreen appears choose More info > Run anyway. If PowerShell is blocked by company policy, they can copy `draft/<file>` over the same file in the project folder (and the `.bak` and `template-2.tmp` copies) by hand while CapCut is closed.

**Mac: "cannot be opened because it is from an unidentified developer".** Right-click `install_mac.command` > Open > Open. Or open Terminal, type `bash ` (with a space), drag the file in and press Enter.

**Vietnamese captions show in a different font or with broken tone marks.** CapCut didn't find the font file at the path in the draft. Check that `BeVietnamPro-Bold.ttf` is at the plan's `font.device` path (default `CapCut Automation/_fonts/`), fix the path or copy the file there, rebuild and reinstall with CapCut closed. Quick manual fix in CapCut: select all captions on the text track and pick any font with Vietnamese support; sizes may then need a small adjustment.

**Vertical captions are bigger or smaller in CapCut than in the preview.** The em-to-pixel factor was measured on 16:9. Set `text_scale` in the plan (current value x CapCut size / preview size), rebuild, reinstall, and reuse that value for this viewer's later vertical videos.

**CapCut opens a vertical project as 16:9.** The canvas is written as `canvas_config` 1080x1920 with ratio "9:16". If CapCut still shows another ratio, ask the viewer to set the project ratio to 9:16 once in CapCut (Ratio menu above the preview), quit, then copy the project again and rebuild: the builder keeps their CapCut's own settings.

**The Vietnamese voice mispronounces an English name or a number.** Write it the way it should sound in that scene's text (keep the real spelling in the caption), regenerate just that scene with the same model, voice and settings, then re-run stitch, align, plan_shots, normalize and the build.

**align_vo matches few words in a Vietnamese video.** Make sure `script.json` has `"lang": "vi"` (or pass `--lang vi`) so whisper runs the multilingual model with Vietnamese; the English model can't transcribe Vietnamese and falls back to pause-based timing.
