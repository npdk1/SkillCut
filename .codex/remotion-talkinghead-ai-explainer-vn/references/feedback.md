---
name: feedback
when: MANDATORY after every verify round that has at least one FAIL (or a failed manual tick), before the rewrite. Also load it when a round 3 rewrite still fails (blockers.md).
---

# feedback.md - per-round feedback report + blockers.md (v4.4)

Loop: build -> `verify_rules.py` (references/verified.md) -> **write `feedback_round<N>.md` (this file)** -> rewrite ONLY what the report names -> verify again.
**Max 3 rewrite rounds** (= verify rounds 1-4). Deliver ONLY when a round has every V-rule PASS (auto) and the manual ticks are done. Still failing after rewrite 3 => no delivery: write `blockers.md` and report it.
Never change a threshold, `verify_rules.py`, `text_occlusion.py`, or a report to make a rule pass. Fix the cause (video, placement, phrase, code) - or, if the rule is a proven false positive of a heuristic, say so in `blockers.md`.

## Where files live
```
out/verify/verify_report_round<N>.json|.md     output of verify_rules.py (--out out/verify/verify_report_round<N>)
out/verify/feedback_round<N>.md                this template, one per FAILED round (V20 checks it exists)
out/verify/manual_round<N>.json                ticks for V05/V09/V13/V17/V18
out/blockers.md                                only when round 3 rewrite still fails
```
Final bundle (V19): copy the all-pass report as `<out>_verify_report.json|.md`, the feedback files as `<out>_feedback_round<N>.md`, and keep `<out>_verify/`.

## feedback_round<N>.md template (copy, fill every cell, no empty cells)
```markdown
# Feedback round <N> - <file>.mp4 (verify_rules.py: pass <a>, fail <b>, warn <c>, manual <d>)
Verify command: `<exact command incl. --out>`
Date: <YYYY-MM-DD HH:MM, Asia/Bangkok (UTC+7)>

| # | rule ID | timestamp (OUTPUT s) / beat id / file:line | measured value | required | fix (what exactly I change) |
|---|---|---|---|---|---|
| 1 | V07 | 14.2 s, tbs1 line 2 glyph "N" | 49 % visible | >= 70 % | other phrase / move line 2 lower / pick a segment with more headroom |
| 2 | V14 | 4.0-6.9 s and 40.1-43.0 s | 2 framed-focus | <= max(1, floor(30/30)) = 1 | drop the lower-scored framed-focus (beats.json) |

Manual items (V05 V09 V13 V17 V18): <ticked / not ticked + one line why>
Root cause (1-3 lines): <why it happened - data limit, code bug, wrong phrase...>
Rewrite plan: <which stages re-run: masks / beats / captions / render only> ; stages NOT touched: <list>
Rounds left: <3 - N rewrites>
```
Rules for filling it:
1. **Every failure gets a row**: rule ID, a timestamp in output seconds (or `whole file` / `file:line` for static checks), the measured number copied from the report JSON, the threshold, and a concrete fix. "Improve" is not a fix.
2. One row per failing item, not per rule (V06 failing on 2 beats = 2 rows).
3. A fix must target the cause: failing V07 -> change phrase/position/line split, never `--max-glyph`; failing V05 -> remove the box, never the check.
4. After the rewrite re-run the SAME verify command with the next round number. Previous round files stay.

## blockers.md template (only after rewrite round 3 still fails)
```markdown
# BLOCKERS - <file>.mp4 - NOT delivered
Date: <YYYY-MM-DD HH:MM Asia/Bangkok>   Rounds run: 4 (1 build + 3 rewrites)   Last report: out/verify/verify_report_round4.json

| rule ID | timestamp / beat | measured (round 1 -> 2 -> 3 -> 4) | threshold | what was tried each round | why it still fails | what is needed (decision / asset / tool change) |
|---|---|---|---|---|---|---|

Rules that PASS in the last round: <list>
Best candidate file (NOT approved for delivery): <path>
Recommendation: <ship with these named known gaps | re-record / different segment | change tool X (owner: ...)>
```
The orchestrator reports `blockers.md` to the requester instead of uploading. Delivery of a file with an open FAIL is forbidden.
