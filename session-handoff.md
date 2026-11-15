# Session handoff — Photoshop + Camera Raw automation (Nov 15 2026, after 9956 revisit)
Paste this into the new session together with **ps-acr-recipes.md** (full reference), **acr.py** (XMP builder), **acr_band.py**, **m.py** / **diff.py** (measurement). `crf-*.json` are worked examples — attach one only if the new image is similar (fog pano → `crf-9956-final.json`).

## Setup (unchanged)
- Chain: chat ⇄ remote-devices ⇄ MCP servers (Claude Desktop) ⇄ node proxy :3001 ⇄ UXP plugin ⇄ Photoshop.
- Each session: `cd ~/dev/adb-mcp/adb-proxy-socket && node proxy.js` → Photoshop → UXP Dev Tools: Load/**Reload** "Photoshop MCP Agent" → Plugins › Photoshop MCP Agent › **Connect**. (`No clients registered for application: photoshop` = plugin not connected.)
- Connect `~/dev/adb-mcp` as a folder in the Claude app (measure PNGs go to `measure/`). Open a DUPLICATE of the image. Quit LrC. **Close every dialog before Claude acts** (else "host is in a modal state").

## Workflow (user rules in bold)
1. Claude: `get_documents` / `get_layers`, read doc info (size, raw SO type, existing raw settings), baseline render.
2. **WB check first, before any edit** — fog/sky by density bins; distinguish rock-scatter warmth from a cast. Fix in the raw SO (user double-click) or filter Tint as fallback.
3. Composition discussion: metrics (detail/weight map) + crop mocks with thirds grid; non-destructive `crop` (`delete:false`).
4. **Feedback includes what works** (composition, leading lines, DR retention, shadow detail, tonal balance) plus top FIX/TASTE items. Ignore the mat; don't chase small clipping numbers unless it's for print.
5. One correction at a time in **one Camera Raw Filter**: render → measure → adjust. Start low; dark subjects need ~1.5–2× the exposure; hazy areas need Dehaze ≥ +0.25.
6. **Before every scripted write: read the live filter and resend ALL keys** (user's Glow `$GLW*`, `$Rtch` Remove, …). `$BigT` can be omitted — AI masks and Generative Remove patches survive (verified 9956).
7. Removals: user paints Camera Raw **Remove** (Generative) **in a Camera Raw Filter on the layer — never in the raw SO dialog** (raw-SO settings aren't readable, so no recipe). Save before the first scripted write after a Remove (revert = safety net).
8. After the user saves: Claude writes `crf-<id>-final.json` and updates the recipe library.
9. **Cleanup after each image** (once the recipe is written): delete the render PNGs in `~/dev/adb-mcp/measure/` (scratch, ~10 MB each; keep the folder). Commit the recipe repo locally; the user pushes.

## Done so far
| Image | What made it work | Status |
|---|---|---|
| 9822 fog hill | Crest dehaze band, rock lift, red band burn | saved |
| 9861 fog hoodoo | WB → raw; forest Dehaze + Clarity; small rock lift (+0.06); 16:9 crop | saved |
| 9785 storm amphitheater | Light pool, frame burn, mesa detail, sky top, cloud glow | saved |
| 9792 near-raw fog/gorge | Land lift, sky texture, gorge dodge (Radials ∩ Luminance Range), 4:3 crop, manual Remove | saved |
| **9956 fog pano** | WB OK (rock scatter, not cast); 2.4:1 crop; Fog glow (LumRange ∩ Radial, Exp +0.10, Tint −0.15); Hub light (LumRange skips crevices, Exp +0.17); Foreground haze (Dehaze +0.25); user Glow 28; Generative Remove of foreground spine | saved (`…/2026-11-01/_52_9956-Pano-Edit.tif`) |
| **9956 revisit (PM)** | Fog rock edges (Texture/Clarity ∩ rock-tone range, +20…39% detail); Crevice lift (darks only, gentle); Right edge Exp −0.06 (fog edge flat with interior); Window fin Clarity/Texture +0.20, Dehaze +0.15; BR calm. Tree lift in crevices abandoned (not maskable under fog) | saved, 8 corrections |
| **0028 hoodoo bowl** | WB cast fixed in raw SO (eyedropper on white tower); spire lift + surround darken; tree pools (spot radials ∩ LumRange); user pine deepen (∩ Color Range), FG vignette minus spire, Blue primary Sat +7; left-trim crop 1.40:1 | saved (`…/2026-11-01/_52_0028-Edit.tif`) |
| **0013 fog-gap canyon** | WB cyan cast → 5300/+7 (Tint matters); 16:9 sky trim; sky gradient ∩ bright; hero crispness > lift; tree pools (skip far forest); distant ravines ∩ shadows; user object-mask pine | saved (`…/2026-11-01/_52_0013-Edit.tif`) |

## Learned this session
- Remove schema = filter key `$Rtch` (`crs:RemoveAreas`, `heal_patchmatch`, `fill_method="firefly"`, Mask/Paint dabs); pixels in `$BigT`.
- Scripted writes after Remove are safe if `$Rtch` + all slider keys are resent.
- Filter-level dialog sliders (Glow) come back as `$GLWA/$GLWR/$GLWS/$GLWW/$GLST/$GLWD/$GLSF`.
- Pinkish fog: Saturation alone removes yellow, not magenta → LocalTint −0.15.
- Heavy pano re-renders can time out the MCP call while still succeeding → check state, don't blindly retry.

## Learned (PM)
- Pixels to Claude: `save_document_as(..., "PNG")` + `device_stage_files`; batchPlay `save` with a path fails (file token). 16-bit PNG if saved before `convertMode`.
- Judge Texture and shadow data on a full-res crop, not the 2000 px preview.
- Bright fog burns ~2× harder than rock: edge burns Exp ≤ −0.06; aim for edge ≈ interior.
- Trees in fogged crevices = same tone/hue as shaded rock → don't attempt with range masks.
- Big sets time out ~50% while succeeding → render to verify.

## Learned (0028)
- Without fog, dark trees lift cleanly with spot radials ∩ Luminance Range; vary the spots.
- Bottom burns/vignettes must subtract the hero radial.
- Raw-SO edits (WB, Calibration) aren't readable → user reports values; record as manual.

## Learned (0013)
- Local Exposure: dialog = 4 × stored (confirmed). Quote dialog values.
- Object masks (Mask/Image) live in `$BigT`; omit it on scripted writes, rebuild from the live `$LCs`.
- Long `get smartObject` results with `$BigT` get truncated in chat → extract `$LCs` from the saved tool-result file.

## Open items
- Still not observed: Brush (standalone), Depth masks.
