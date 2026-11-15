# Photoshop + Camera Raw automation — recipe library
_Built Nov 14–15 2026 (9956 revisited Nov 15 PM) on 9689 (hoodoo ridge), 9822 (fog hill / spire), 9861 (fog hoodoo + forest gap), 9785 (amphitheater, storm sky), 9792 (near-raw fog, gorge, branch frame) and 9956 (fog pano, hub + window fin, spine removed). Paste as session context._

**Session order (user rules): 1. WB check first, always, before any edit. 2. Composition / crop discussion. 3. One correction at a time, measured. Critiques must also say what works (composition, leading lines, DR retention, shadow detail, tonal balance).**

## 0. Session setup (unchanged)
- `cd ~/dev/adb-mcp/adb-proxy-socket && node proxy.js` → PS Beta (Developer Mode) → UXP Dev Tools: Load "Photoshop MCP Agent" → Plugins › Photoshop MCP Agent › Connect.
- claude_desktop_config uses repo-locked env: `uv run --directory …/adb-mcp/mcp mcp run ps-mcp.py` (and `ps-batch-play.py`). **Never `--with mcp`** (pulls SDK 2.x, no FastMCP).
- Work on a DUPLICATE document. Quit LrC, one doc open, PS memory ~60%.
- **Close every PS/Camera Raw dialog before Claude acts** — otherwise: `host is in a modal state`.
- Proxy log `No clients registered for application: photoshop` = proxy up, plugin not connected → UXP Dev Tools **Reload** plugin → panel **Connect**.
- User home path for saves: `get` application `preferencesFolder` (→ `/Users/tanhuynh/...`). The user saves edits as TIFF next to the source (e.g. `/Volumes/Photos2/root/2026/<date>/<name>-Edit.tif`); `get` document shows `path`/`saved`.
- Heavy re-render (152 MP pano) can time out the MCP call (`Could not connect… Timed Out`) while the command still succeeds → `get_documents`, then read the filter back before retrying.

## 1. Measurement loop (after every layer)
batchPlay: `duplicate` (merged) → `imageSize` 1350 px (2000 px for panos) → `convertToProfile` sRGB (colorimetric, BPC) → `convertMode` depth 8 → `get_document_image` → `close` no save.
- **Run `convertMode` as its own call** — in the 4-step batch it silently doesn't run (doc stays 16-bit → "Only 8 bit image data can be encoded as jpeg"). Reliable split: [duplicate, imageSize, convertToProfile] then [convertMode `_target` targetEnum, depth 8].
- Standalone `convertToProfile` on an already-sRGB doc → "parameters not currently valid" (harmless).
- Run the image fetch **after** the batch returns (parallel call races the 8-bit conversion).
- **Getting pixels to Claude for numbers** (Nov 15 PM): batchPlay `save` with a `_path` fails ("invalid file token used") and `save_document_image_as_png` returns "No raw image data". What works: `save_document_as(path, "PNG")` on the measure doc → `device_stage_files` (needs a connected folder, e.g. `~/dev/adb-mcp/measure`) → numpy. Saving before `convertMode` gives a **16-bit PNG** (good for shadow-level checks).
- **Full-res crop check**: duplicate merged → `crop` (`delete:true`, doc px = preview px × 8.57 for the 2.4:1 crop) → save PNG. The 2000 px preview hides Texture (8.5× downsample) and makes small dark subjects look empty — judge Texture and "is there data in the shadows" at 1:1.
- Close the measure doc by `_id`; if Photoshop closed docs on its own, `close` errors with "Cannot read properties of null" → check `get_documents` first.
- **Local contrast metric** (tree/rock detail): std of `L − gaussian(L, σ=2–3)` per region. Separates "darker" from "flatter": Exp burn cut it −25%, Dehaze raised it +10% at the same L*.
- Neutral-reference WB check: median a*/b* on fog/sky/grey cliff (target a*≈0; b* slightly negative is natural in overcast).
- **WB check by fog density** (9956): bin low-chroma, low-texture pixels by L* (88+, 82–88, 75–82, 68–75, 60–68). Densest fog neutral but thin fog warm *at the rock's hue* = red-rock scatter, not a cast → don't fix globally (a global fix turns dense fog/distance cyan). A true cast shifts all densities together. Distant gaps should read slightly cool (b* < 0).
- Composition metrics: detail energy per band/column, fog fraction per column, visual-weight map = detail × chroma × |L − median| (blurred). Highest weight not on the subject → crop or calm it. Mock crops with thirds grid from the preview (`mock.py`).
- Metrics per region: median L* (tone), p95–p5 (contrast), **Lab C\*** for color (HSV saturation hides chroma loss).
- Diff two renders (`|ΔL*|×15`) to *see* the effective mask — best way to verify any mask.

## 2. batchPlay gotchas
- Multi-command response echoes **only the first command**; a failure mid-batch **silently stops the rest**. Check `layers`/state after, or run risky steps alone.
- Curves: `make` adjustmentLayer (curves, mode luminosity) **then** `set` targetEnum with `curvesAdjustment` points. Points inside `make` are ignored.
- Curve inputs are ProPhoto gamma 1.8: in ≈ 255·Y^(1/1.8). 100→112 ≈ +5 L* near L*50.
- Luminosity-mode lifts cost ~5% chroma → pair with Vibrance +10 / **Saturation +5** on the same mask (Vibrance alone recovers little).
- **Never `select` the `mask` channel to paint it** — it can toggle Quick Mask (fill goes there; `convertMode` then fails). Exit with `clearEvent` on `quickMask`.
- `get_document_image` fails on 16-bit docs (use the measurement loop).

## 3. Photoshop mask recipes (all built as a selection, then `make` layer → selection becomes mask)
| Need | Recipe |
|---|---|
| Land vs fog/sky | `select_subject(SO)` — on landscapes it returns **all land/rock**, not "the subject". |
| Sky | `select_sky(SO)` (+ `inverse` for land). |
| Mask ∩ polygon | load mask as selection (`set selection to [mask, layer]`), then `intersectWith` `_target: selection`, `to: {polygon…}`, `feather`. (Reverse form `intersectWith` on the mask channel → "not available".) |
| Soft boundary at a stratum | `subtractFrom` selection a feathered `rectangle` (feather 100 px) at a row found by measuring brightness per row. |
| Gradient mask | clear selection, make layer, select channel `mask`, `gradientClassEvent` linear white→black. |
| Smart-filter mask from selection | with selection active: `delete` channel `filterMask`, then `make` `new: channel` `at: filterMask` `using: revealSelection`. Toggle via `set layer filterMaskEnable`. |
- Polygon from a preview: doc px = preview px × (doc width / 1350). Keep 20 px feather on true edges; check the edge with a zoomed diff crop (first try spilled ~40 px into the subject).
- Adobe cloud connector: hard prompt masks → seams. Prompt to Edit is generative → never for tonal work.

## 4. Camera Raw Filter, headless
**Apply** (selected SO layer → becomes an editable Smart Filter; only keys sent are changed, rest stay neutral):
```json
{"_obj":"Adobe Camera Raw Filter","$CrTx":15,"_options":{"dialogOptions":"dontDisplay"}}
```
Verified keys: `$CrTx` Texture, `$Dhze` Dehaze (−100…100), **`$Tint`** (relative on rendered SO; −8 moved fog a* ≈ −1.3, −20 neutralized a* +2.7; also nudges b* warmer and, oddly, L* +2 globally while non-zero). Probably (verify by pixel check before relying): `$Ex12 $Cr12 $Hi12 $Sh12 $Wh12 $Bk12 $Cl12 $Vibr`.
- An unrecognized key is still echoed back by `get` (no `$CrVe` added) → only a pixel check proves a key works.
- **WB belongs in the raw SO's own settings** (user double-clicks; not scriptable). Filter `$Tint` is a fallback. Fog/overcast "as shot" ~6300–6600 K is plausible; Daylight 5500 + magenta tint pushes fog violet.

**Apply with masks in one step** (verified 9785): the first apply accepts the full payload — `{"_obj":"Adobe Camera Raw Filter","$CrVe":"19.0","$PrVN":6,"$PrVe":251920384,"$LCs":"<XMP>","_options":{"dialogOptions":"dontDisplay"}}` → filter created with all corrections, no dialog. (Batched after a `select`, the response is empty — confirm with `get smartObject`.)

**Read**: `get` `smartObject` on the layer → `filterFX[i].filter` (with a Remove present the response is ~11 MB → saved to a file; parse with `ast.literal_eval`):
- `$LCs` = standard Camera Raw XMP string (`crs:MaskGroupBasedCorrections`) — fully readable/editable.
- `$BigT` = binary AI-mask bitmaps (can't be sent back through JSON; leave it out).
- `$CrVe` "19.0", `$PrVN` 6, `$PrVe` 251920384 — send back unchanged.
- **Filter-level sliders the user sets in the dialog appear as their own keys** — e.g. Glow: `$GLWA` amount, `$GLWR` range, `$GLWS` spread, `$GLWW` warmth, `$GLST` style, `$GLWD` direction, `$GLSF` directional softness. **A scripted `set` must resend every key** (keys not sent are reset) → always read the live filter first and edit it; never regenerate blindly.
- **`$Rtch`** = Remove tool XMP (`crs:RemoveAreas`), see §5. Send back unchanged.

**Edit in place**:
```json
{"_obj":"set","_target":[{"_ref":"filterFX","_index":1},{"_ref":"layer","_id":ID}],
 "filterFX":{"_obj":"filterFX","filter":{"_obj":"Adobe Camera Raw Filter",
   "$CrVe":"19.0","$PrVN":6,"$PrVe":251920384,"$LCs":"<edited XMP>"}},
 "_options":{"dialogOptions":"dontDisplay"}}
```
Existing AI masks keep working when `$BigT` is omitted (Camera Raw keeps the cached bitmap). **Same for Generative Remove patches** (verified 9956: set with `$Rtch` but without `$BigT` → patch area median ΔL* 0.00). Still: save before the first scripted write after a Remove, so `revert` is available.
- Dialog re-save normalizes my XMP (radials `Flipped="true"`, range masks `MaskValue="0"`) — harmless, keep what it wrote.
- Raw SO can be a pano **DNG** (`smartObject.fileReference` `_52_9956-Pano.dng`) → raw WB/Glow editable by double-click; its LrC settings (incl. Glow) stack with filter Glow.
- Raw Smart Object's own Camera Raw settings (double-click SO) are **not readable** — only a content ID. Do mask work in a Camera Raw *Filter* on a layer.
- Duplicated SO layers are linked instances: a raw-level edit shows in all of them.
- ⚠️ Local Dehaze strength varies with render path, same settings: headless apply −11 L*; after the dialog was opened/OK'd −5.5 L*; after nesting into a Smart Object (full re-render) −11 L* again. Dehaze is neighborhood-based, so a cached/proxy render can differ. **Judge final strength on a full re-render** (nest, or flatten a copy), not on the live smart-filter preview.

## 5. Camera Raw mask XMP — schema (as observed, Camera Raw 19.0)
Correction (`rdf:li` → `rdf:Description`): `crs:What="Correction"`, `CorrectionAmount="1"`, `CorrectionActive`, `CorrectionName`, `CorrectionSyncID` (32 hex), local sliders on **−1…+1** (`LocalDehaze="0.40"` = +40; also `LocalExposure2012`, `LocalContrast2012`, `LocalHighlights2012`, `LocalShadows2012`, `LocalWhites2012`, `LocalBlacks2012`, `LocalClarity2012`, `LocalTexture`, `LocalTemperature`, `LocalTint`, `LocalSaturation`, …), then `crs:CorrectionMasks` seq.

Mask components (combined in order):
- **Blend**: `MaskBlendMode="0"` add · `"1"` subtract · **Intersect = `"1"` + `MaskInverted="true"`** (what the UI writes).
- **Linear gradient** `Mask/Gradient`: `ZeroX/ZeroY` (value 0) → `FullX/FullY` (value 1, stays 1 beyond). Normalized coords, origin top-left; **perpendicular computed in pixel space** (correct for aspect — see `acr_band.py`).
- **AI** `Mask/Image`: `MaskSubCategoryID` landscape class — **Mountains 50002, Vegetation 50005**; `ReferencePoint`, digests, `FullMaskSize`; bitmap in `$BigT`. **Cannot be created headless** (sent without bitmap → silently ignored).
- **Color Range** `Mask/RangeMask` → `crs:CorrectionRangeMask`: `Version="4" Type="1"` (color), `ColorAmount` 0–1, `SampleType="0"`, `PointModels` = `"x y c1 c2 c3 0"` (sample position normalized + sampled color). **✅ Writable headless** (cloned a user sample into new corrections). ColorAmount 0.49 caught tan rock only; 0.8 also caught pink/red rock while fog/forest stayed out.
- **Color Range, multiple samples**: shift-click adds `PointModels` entries; last field is the sample index (`… 0`, `… 1`).
- **Luminance Range** `Mask/RangeMask` → `crs:CorrectionRangeMask` as a self-closing element (not nested Description): `Version="4" Type="2"`, `LumRange="f_lo lo hi f_hi"` (0–1; e.g. `0.088 0.338 0.538 0.788`), `LuminanceDepthSampleInfo="0 <sampled lum> <…>"`. **✅ Creatable headless from scratch** (9792: written with no dialog sample, worked first time). Scale ≈ L*/100 of the image the filter sees: dark trees at L* ~13 were caught by `LumRange="0 0.02 0.22 0.36"` while rock at 27–30 and bright river/rocks stayed out. Use for near-neutral areas (forest in fog) where Color Range would also catch fog, and as "∩ dark tones only" to dodge trees without lifting adjacent rock.
- **Radial** `Mask/CircularGradient`: `Top/Left/Bottom/Right` (normalized bounding box, may exceed 0–1), `Angle`, `Midpoint` 50, `Roundness` 0, `Feather` 0–100, `Flipped` false (=inside), `Version="2"`. Intersect = blend 1 + inverted, as with linear.
- **Object mask** (Select Object, brushed) `Mask/Image` with **no `MaskSubCategoryID`**, plus nested `crs:Gesture` → `Mask/Paint` with `Dabs` (`r` radius, `h` hardness, `d x y` points). **Sending it back without `Gesture` and without `$BigT` still works** (bitmap cached by `MaskDigest`). Can't be created headless.
- **Dark subjects need ~1.5–2× the midtone exposure** (9956 hub, L* ~20): Exp 0.07 → +0.7 L*; 0.12 → lit faces +4.5…+5.9; 0.17 → another +2. Pair with **Luminance Range `0.05 0.12 0.60 0.80`** to skip the crevices → lifts faces only, crevices ΔL 0, local contrast +14…21%.
- UI slider ≈ 4 × stored `LocalExposure2012` (0.12 ≈ +0.48 EV) — *probably*, verify in dialog.
- **Local exposure calibration**: `LocalExposure2012` is applied in linear light before the profile tone curve — 0.3 lifted midtone rock +14 L*; **~0.09–0.10 ≈ +5 L*** (≈ PS Curves Lum 100→112). Burn needs a slightly larger magnitude than the lift on the same mask (−0.13 vs +0.09) to net out like the PS pair. Iterate: set → render → measure.
- ⚠️ **In flat fog light, keep rock Exposure lifts ≤ ~+0.06–0.10.** +0.20 (+7…+11 L*) on 9861 made every hoodoo chalky/white ("zombies"). Separate the subject by working on the *surroundings* instead (dehaze/burn the background), and lift chroma with Sat +0.05.
- **Fog glow** (9956): Radial on a dull grey fog mass ∩ Luminance Range `0.40 0.50 0.85 0.95`, Exp +0.10 → fog +5…+6 L*, rock 0. Pinkish fog: Sat alone (−0.30) removes yellow but leaves magenta → use **LocalTint −0.15** (a* −1) + Sat −0.15.
- **Local Dehaze on hazy foreground needs ≥ +0.25** to show (0.10 → detail +11%; 0.25 + Clarity 0.15 → +23%, −3 L*). Stop before real drifting fog disappears.
- **Dehaze vs Exposure burn on hazy areas**: Exp −0.20 darkened the forest −7.5 L* but local contrast −25% → "dark blob". Dehaze +0.60 + Clarity +0.15 gave the same −7.5 L* with contrast +10%. Dehaze +0.35 was too weak on this render path (−3.5 L*, no contrast gain).
- **Depth rule**: don't dehaze the far background — haze increasing with distance *is* the depth cue. For background detail use Clarity/Texture ≤ +0.12 with Dehaze ≤ +0.08, faded toward the fog side; check the background stays well above mid-ground L*.
- **Gradient coords are in the uncropped SO frame** — Camera Raw renders the full SO; a non-destructive crop only hides pixels. Convert preview coords from the uncropped render.
- ⚠️ **Near-raw / underexposed land (9792): start low and step up.** Land at L* 12 with sky at 88 (bimodal). Exp +0.35 / Shadows +0.30 overshot to 39 L* ("sunlit", wrong for overcast); **Exp +0.25 / Shadows +0.20 / Blacks +0.10 / Sat +0.10 → 30 L*** (shaded hoodoos, gorge kept darkest at 13). Sky: Highlights −0.30/Exp −0.15/Dehaze +0.15 overshot to 65 (= fog band, fog layer lost); **Hl −0.25 / Exp −0.05 / Dehaze +0.10 → 76** (sky stays above fog). Rule: keep the order sky > fog > land and the darkest mid-ground darkest.
- **Remove (captured 9956)** → filter key **`$Rtch`**: `crs:RemoveAreas` seq; each item `SpotType="heal_patchmatch"`, `fill_method="firefly"` (Generative), `pm_target_top/left/bottom/right` (px, uncropped SO), `pm_search_*`, `pm_patch` / `pm_patch_mask` / `pm_patch_variations` digests (bitmaps in `$BigT`), `crs:Masks` → `Mask/Paint` (`Radius` normalized, `Flow`, `CenterWeight`, `Dabs` "d x y"). Image-specific: can't be authored headless (needs the Firefly patch). Full example: `crf-9956-final.json`.
- **Texture/Clarity on rock emerging from fog** (9956 PM): fade gradient (spare the already-crisp subject) ∩ Luminance Range on rock tones (`0.05 0.12 0.48 0.60` — measure first: rock L* 9–54 vs fog 55–93). Texture +0.25 / Clarity +0.15 → detail +20…39%, fog untouched. +0.15/+0.10 was invisible at preview scale. Side effect: raises visual weight of busy foreground → may need a calm afterwards.
- **Crevice "unplug"**: Radial ∩ darks-only range `0 0 0.08 0.16`, Shadows +0.20 / Blacks +0.10 → p1 2→3.6, mids/lit faces ΔL 0.0, local contrast −10%. Stop there.
- ❌ **Don't try to lift trees in fogged crevices** (9956): data is there at full res, but trees share L* and hue (~45°, red-rock scatter) with shaded rock faces. Wider range (to 0.22) + Exp +0.25 turned shaded rock orange (+9 L*) and noisy; Tint −0.12 didn't make them green. Only hand-painting would separate them — not worth it.
- **Edge balance on a fog edge**: burning bright fog hits ~2× harder than rock for the same exposure. Right-edge gradient Exp −0.12 (+Dehaze) gave −10 L* and an edge darker than the interior (grey band). **Exp −0.06, no Dehaze, long ramp (last ~22% of width)** → edge flat with interior (66→61). Target: edge ≈ interior, not darker.
- **Secondary anchor at a frame edge** (window fin): Radial ∩ rock-tone range (`0.05 0.12 0.50 0.62`, keeps surrounding fog out) with Clarity/Texture +0.20, Dehaze +0.15 → detail +15%, weight 0.11→0.14. +0.12/+0.08 was too timid (+8%).
- **Foreground calm**: bottom ∩ fade-in-right gradients, Exp −0.06, Sat −0.08 → −1.4 L*, C* −1.6, weight 0.34→0.31.
- Not yet observed: Brush (standalone), Depth.

## 6. Who does what
| Task | Headless (Claude) | Needs one click in dialog |
|---|---|---|
| Global CRF sliders | ✅ | |
| Read any mask/correction | ✅ | |
| Edit values / gradients around existing masks | ✅ | |
| New linear gradients, bands | ✅ | |
| Color Range | ✅ (clone a sample; ColorAmount tunable) | first sample on a new image |
| Luminance Range | ✅ (create from scratch; verified 9792) | |
| Object removal (branch, distraction) | ❌ scripted Content-Aware Fill failed on fog + textured rim (9792). ✅ read/preserve `$Rtch`; scripted edits afterwards safe | ✅ Camera Raw **Remove** tool, painted by the user (Generative: clean over fog 9792 and over hoodoo-column texture 9956) |
| Radial gradient | ✅ (schema known) | |
| White balance | check first (§1, by fog density); `$Tint` / LocalTint in filter (fallback) | ✅ raw SO WB (user, double-click) |
| Filter Glow, other dialog-only sliders | ✅ preserve (`$GLW*` keys) | ✅ set by user |
| Crop | ✅ `crop` with `delete:false` (non-destructive) | |
| Select Landscape/Subject/Sky/Objects/People, Depth | | ✅ (then Claude edits around it) |
- Select Landscape → Vegetation isn't always offered (9861: unavailable) → fallback: **Luminance Range ∩ Radial − Object mask** on the subject.

## 7. Recipe: dehaze a ridge line in fog (9822)
1. Find the crest per column: blur L, strongest downward darkening (skip columns crossed by rock). 9822: (0.41,0.42)→(1.0,0.56).
2. `python3 acr_band.py` → band endpoints (top −0.07, full +0.02…+0.10, bottom +0.20 frame heights).
3. Correction "Crest band": gradA blend 0; gradB blend 1 + inverted; `LocalDehaze` 0.40.
4. Exclude rock: in dialog **Intersect → Select Landscape → Vegetation** (+ optional Subtract → Color Range on the rock). Fallback: inverted `select_subject` as the smart-filter mask (equal result here).
5. Measure: 9822 crest 53.1→47.6 L*, spire/mesa/front block unchanged, fog/sky unchanged. TASTE: 0.60 for a stronger ridge.

## 8. Layer recipes that worked
| Recipe | Values | Mask | Result |
|---|---|---|---|
| Rock lift | Curves Lum 100→112 (192,255 pinned) | sky inverted / select_subject | +4.7 L* on rock |
| Restore chroma after lift | Vibrance +10, Sat +5 | same | C* back to baseline |
| Bottom burn (9689) | Curves Lum 100→84, 220→215 | gradient bottom→62% | bottom under ridge |
| Red stratum burn (9822) | Curves Lum 100→86 | rock ∩ block-aware polygon − feathered rect above stratum | band −4.8 L*, C* +1 |

## 9. Critique rules
Web default: top 2–3 visible issues, label FIX vs TASTE, ignore the mat, deep darks + rich color, don't flatten subject color. Print = strict. Build one layer at a time, measure after each.
- **WB first**, before any local work (user's call on 9861) — it resets every color judgment.
- **Composition pass** at the end: detail energy per third/band (mean |L − blur|) finds dead space (9861 top 30% = 0.21 vs 1.7 mid). Mock crops locally with PIL + thirds grid before touching PS. Check which mass carries the most area × warmth × detail — if it isn't the subject, calm it (small burn/desat by gradient).
- Before "fixing" a color patch at an edge, ask/check what it is (9861 corner = real red cliff, not vignetting); edge cleanup is still fine if it pulls the eye out.

## 7e. Recipe: fog pano, focal hub + edge distraction (9956)
Problem: 2.55:1 pano; clear hoodoo hub left swallowed by fog right; hub (most detail) was the *darkest* area (L* 19); dull grey fog mass (58); bright rim rubble + pale spine at bottom = highest visual weight. All headless except Remove:
1. WB check → fine (dense fog neutral; warm thin fog = rock scatter). Left alone.
2. Crop 2.4:1 (drop rim rubble + dead right strip; spine lands on right-third line).
3. Fog glow — Radial ∩ LumRange fog tones; Exp +0.10, Sat −0.15, Tint −0.15 → 58→64, a* 5→3.7.
4. Hub light — Radial ∩ LumRange "lit faces"; Exp +0.17, Sat +0.05 → faces +6.5…+8, crevices 0, contrast +21%.
5. Foreground haze — bottom ∩ fade-right gradients; Dehaze +0.25, Clarity +0.15.
6. User: filter Glow 28/62/53 (top fog +4); Generative Remove of the spine (user judged it out of place; edge distraction, short "leading line" not worth keeping).
7. (PM, revisited) Fog rock edges · Crevice lift · Right edge · Window fin · BR calm — see §5 bullets; tree lift abandoned.
- What worked compositionally: Z-flow (fog in top-right → hub → ridge from window fin; spine pointed back to hub before removal), 4–5 fog-separated depth planes, cool distant gap. DR: no channel at 255, crevices detailed (darkest 10% had 3× midtone local contrast). Full recipe: `crf-9956-final.json`.

## 7d. Recipe: near-raw, underexposed land under bright fog (9792)
Problem: land median 11 L*, sky 86 (exposed for the sky); hoodoos colorless (C* 11), gorge crushed. All headless, 4 corrections:
1. Land — below-fog-line gradient − Radial on the branch tip (keeps the silhouette black); Exp +0.25, Shadows +0.20, Blacks +0.10, Sat +0.10.
2. Sky texture — above-fog gradient; Exp −0.05, Highlights −0.25, Dehaze +0.10.
3. Gorge dodge — 3 Radials along the gorge (∪) ∩ headless Luminance Range on dark tones; Exp +0.18, Shadows +0.15 → light through the mist on the trees, rock untouched.
4. Field presence — Clarity +0.12, Texture +0.10 on the hoodoo field, faded before the gorge.
- Composition: kept the branch frame (don't crop the top — the branch must enter from its corner); 4:3 trimmed the low-interest left third. Mock crops on a roughly brightened preview before tonal work.
- Removing the lower branch: scripted Content-Aware Fill (stamp → polygon → fill → mask) failed twice → user used the Camera Raw Remove tool. Full recipe: `crf-9792-final.json`.

## 7c. Recipe: focal light on a uniform scene under a storm sky (9785)
Problem: whole hoodoo field equally busy (detail ~7) and equally bright (31–33 L*); bottom third most saturated; cloud break above centre with no matching light below. Everything headless (radials + gradients), 5 corrections:
1. Light pool — feathered Radial (feather 100) on the field under the break; Exp +0.09, Sat +0.03 → centre +4…+6 L*, whites 45 (not chalky).
2. Frame burn — (bottom ∪ left ∪ right gradients) ∩ below-horizon gradient; Exp −0.08, Sat −0.05 → bottom −4, corners −5; centre now ~8 L* above bottom.
3. Mesa detail — band ∩ fade-to-fog; Clarity/Texture +0.10 (detail +9%, tone unchanged).
4. Sky top — top gradient (0→30%) − Radial on the break; Exp −0.12, Dehaze +0.08 → top 60→49 L*.
5. Cloud glow — Radial on the break; Exp +0.08, Highlights −0.15, Dehaze −0.05 → core 85→89; ~0.3% hits L*97 (fine for web; +0.06 for print).
- Mask patterns: "∪ then ∩" = add several gradients (blend 0), then one intersect (blend 1 + inverted) applies to the union. Radial subtract = blend 1, inverted false.
- Light order to aim for: dark top → glowing break → lit field centre → darker frame. Full recipe: `crf-9785-final.json`.

## 7b. Recipe: subject vs hazy mid-ground (9861)
Problem: hero hoodoo 7–10 L* darker than the foggy forest behind it.
1. Rock lift — Color Range on hoodoo (2 samples), Exp +0.06, Sat +0.05 (not more — see §5 warning).
2. Forest dehaze — Luminance Range on forest ∩ Radial around forest − Object mask (hoodoo); Dehaze +0.60, Clarity +0.15.
3. Result: hoodoo waist 36 vs forest 30, mid 30 vs 26; base 23 vs 26.5 but separated by chroma (21 vs 2). Fog/sky unchanged.
4. Then: BG wall detail (Clarity/Texture, fade toward fog), calm the competing block (Exp −0.06, Sat −0.05), ledge burn (−0.05), 16:9 crop of empty top. Full recipe: `crf-9861-final.json`.

## 10. 9822 state at end of session
One layer: **"_52_9822 (edit)"** — the raw SO itself (outer wrapper removed with `placedLayerConvertToLayers`; render pixel-identical) with **one Camera Raw Filter** (Texture 15 + 3 corrections): Crest band (Crest top ∩ Vegetation − Color Range, Dehaze +40) · Rock lift (Color Range 0.8, Exp +0.09) · Red band burn (Color Range 0.8 ∩ below-stratum ∩ left-of-block gradients, Exp −0.13, Sat +0.10). All PS adjustment layers replaced; matches them within ~1 L* (right hoodoos −2.2). Full recipe: `crf-9822-final.json`. Unsaved.
- PS → Camera Raw mapping: Curves-Luminosity lift/burn → LocalExposure2012; PS polygon → intersected linear gradients; PS select_subject rock mask → Color Range on rock.
- To edit later: double-click the layer to open the inner document, adjust, save/close.
- To nest a stack: select all layers (`select` top, then `addToSelectionContinuous` bottom), then `newPlacedLayer`.

## 14. 9956 state at end of session (saved by user, revised Nov 15 PM)
`/Volumes/Photos2/root/2026/2026-11-01/_52_9956-Pano-Edit.tif`: raw pano DNG SO (LrC globals, WB Auto 5650/0, raw Glow 41) + one Camera Raw Filter, **8 corrections**: Fog glow · Hub light · Foreground haze · Fog rock edges · Crevice lift · Right edge · Window fin · BR calm; filter Glow (28/62/53/0), Remove (spine, Generative). Crop 2.4:1 non-destructive (x 0–17139, y 0–7141 of 19700×7732). Full command: `crf-9956-final.json`.

## 16. 0028 (Queen's Garden / overcast hoodoo bowl, R5 II CR3, 8192×5464) — saved (`…/2026-11-01/_52_0028-Edit.tif`, full command `crf-0028-final.json`)
- **WB: true global cool/magenta cast** (unlike 9956's fog scatter): every neutral shifted together — white limestone a* +2.6…+6.4 / b* −14…−20, red rock hue −30° (b* negative), trees hue −102° (blue). Fixed in the raw SO by WB eyedropper on the white limestone tower (avoid the sky-lit white dune) → tower +1.9/+3.8 (cream), rock hue 56° C* 22→30, trees 176° (blue-green, normal under overcast). Residual a* +5 on the dune = optional Tint −2…−3.
- **Remove done inside the raw SO** (user, Generative, bottom-left sage brush): clean fill with matching striation; also removed two small shrubs under the brush. ⚠️ Raw-SO Camera Raw settings are **not readable** (`smartObject` → only `documentID` xmp.did changes; `smartObjectMore` → transforms/IDs) → no XMP for the recipe, but later scripted *filter* writes don't need to carry `$Rtch`. **User rule (Nov 15): always do Remove in a Camera Raw *Filter* (on the layer), never in the raw SO dialog, so the `$Rtch` XMP can be read and added to the recipe.** WB stays in the raw SO.
- Crash note: Photoshop crashed after the dialog; auto-recovery restored the unsaved duplicate **with** raw edits (new doc id, layer renamed `_52_00281`). Re-read ids after any restart; restart the proxy + plugin Connect.

- **Hero separation (no fog, overcast):** Spire lift (radial, Exp +0.12, Clarity/Texture +0.18) + Spire surround (Exp −0.08, Sat −0.05, radial minus spire) → spire ≈10 L* above the wash (was 1.6). A brush Texture/Contrast +0.10 on top adds only ~1% detail once the radial is doing the work — the surround darkening matters more than more texture.
- **Keep competing hoodoos out of hero masks.** User's first hero brush also painted 3 left columns → removed; detail on those dropped back slightly, which is the point.
- **Dark trees, no fog = rescuable** (contrast with 9956): Tree pools = several small radials (different spots, not one gradient) ∩ LumRange 0/0.08/0.42/0.52, Exp +0.24, Shadows +0.31, Sat +0.10, Temp +0.06. Uniform gradient looked fake; dappled spots read as light. Hoodoos ΔL* 0.
- **Then deepen the green ravine selectively** (user): small radials ∩ Color Range on the pine green, Exp −0.025…−0.075 → band sits back, rock untouched. Lift-then-deepen is fine: pools give the dapple, deepen sets the band's overall weight.
- **Foreground vignette** (user): linear gradient y 0.73→1.16, Exp −0.275 (≈−0.17 at the edge) stacked on FG calm → bottom slope L* 56→48, no band. **Every bottom burn needs the "minus spire" subtraction** or it darkens the hero's base (−1.3 L* before fix).
- **Calibration Blue primary Sat +7 / Hue −9** (user, raw SO) instead of global Saturation: rock and greens +1.5–2 C* evenly, rock stays peach not orange.
- **Crop:** left trim 541 px (1.40:1) put the spire on the left third and removed competing white fins; the 3:2 bottom-trim variant cut the FG hoodoo — avoid.
- Paint (brush) dabs and Color Range masks are pure XMP → survive scripted writes (no `$BigT` needed).

## 17. 0013 (overcast canyon, V-gap with fog, big foreground pine, R5 II CR3) — saved (`…/2026-11-01/_52_0013-Edit.tif`, `crf-0013-final.json`)
- **WB: cyan (green) cast, not just blue** — cloud a* −3…−8 at every density, trees hue −148°. Needs **Tint** (+7) as well as Temp (5300). Clouds then a* 0, b* −3…−12 = natural overcast; fog b* −9 left as aerial blue. Don't eyedropper on partly clipped cloud.
- **Crop 16:9 from 3:2** (rows 614–5222 kept: top −614, bottom −242): sky top quarter had 1.5% of visual weight; keep a thin cloud band so the fog has a source. V gap lands on upper third.
- **Sky structure:** top gradient (full at crop edge → zero above mesas) ∩ LumRange bright 0.58/0.72; Highlights −30, Exposure −0.40 (dialog), Dehaze +15, Texture +10 → L 89→77, cloud detail ×1.5–1.8, mesas untouched. Side effect: darker cloud reads cooler (b* −12) — user kept it (moody).
- **Hero darker than its surroundings** (shaded cluster vs sunlit slopes 35 vs 46): lift only +0.40 dialog; separation comes from Clarity/Texture +15 (+29% detail) + surround −0.32. Lifting more would merge it into the slope.
- **Tree pools** reused from 0028 (spot radials ∩ LumRange 0/0.08/0.42/0.52); user settled at Exposure +0.65 dialog. **Skip far forest near fog** — a spot under the far mesa went grey/hazy (+9 L*) and flattened depth; removed.
- **Distant ravines:** radials on far walls ∩ LumRange shadows 0/0/0.30/0.42, Exposure −0.15 dialog + Blacks −10 → −2…−3 L* in gullies. Hazy far mesas have ~no real shadows → little effect; that haze *is* the depth cue. Don't push far darks toward FG darks (FG ~12 vs far ~24).
- **Big FG pine (user):** Object masks (Mask/Image + Gesture) ∩ Color Range on needles; Clarity +10, Texture +25, Temp +6. Clean edge vs busy rock; keep Clarity ≤ +15 to avoid a bright rim against the slope.
- **Units confirmed:** local Exposure dialog = **4 × stored** (user set +0.65 → 0.1625); Shadows/Blacks/Texture/Clarity/Dehaze/Sat dialog = stored × 100. Quote dialog values to the user.

## 15. Tooling
- `acr.py`: builds `$LCs` XMP — `grad()`, `radial()`, `lum()` (Luminance Range), `corr()`, `set_cmd2(corrs, extra=GLOW)`; coords given in crop-preview px, converted to uncropped-SO normalized (`SX/SY` constants per image). For edits after dialog work, edit the live `$LCs` string instead and resend all keys.
- `wb.py` (white-ref / rock / tree a*·b*·hue table from 16-bit renders). `m.py` (load → L*, C*, detail; region table) and `diff.py` (region ΔL/detail/C* table + `|ΔL|×15` mask image) — current versions in `~/dev/adb-mcp/recipes/`. `diff.py` region ΔL table + `|ΔL|×15` mask image; `wb.py` fog-density WB check; `mock.py` crop mocks with thirds grid.

## 13. 9792 state at end of session (saved by user)
Raw SO `_52_9792` (WB 6200/0) + one Camera Raw Filter: Land · Sky texture · Gorge dodge · Field presence, **plus the user's manual Remove stroke on the lower branch** (not in the JSON). Crop 4:3 non-destructive (columns 907–8192). Full command: `crf-9792-final.json`.

## 12. 9785 state at end of session (saved by user)
One layer: raw SO `_52_9785` + one Camera Raw Filter, 5 corrections: Light pool · Frame burn · Mesa detail · Sky top · Cloud glow. No crop. Full command: `crf-9785-final.json`.

## 11. 9861 state at end of session (saved by user)
One layer: raw SO `_52_9861` (WB 6300 / −12 + user globals) + **one Camera Raw Filter, 6 corrections**: Rock lift · Forest dehaze · BG wall detail · Right block calm · Ledge burn · Corner fix. Crop 16:9 non-destructive (rows 728–5336 of 8192×5464). Full command + crop: `crf-9861-final.json`.
- Editing an existing filter: rewrite the whole `$LCs` (all corrections) in one `set` on `filterFX` index 1; omit `$BigT`. New corrections need fresh 32-hex `CorrectionSyncID` / `MaskSyncID`.