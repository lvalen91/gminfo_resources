# GMSystemUI App Gating

Static-RE findings on what gates (a) CardView clock/widget panel existence and (b) the CardView-hide/immersive decision in GMSystemUI/GMHomeScreen, and whether native Cinemo CarPlay's bounds can be changed without a calibration write.
Scope: code-level gates only; emulator calibration behavior lives in [emulator.md](emulator.md#matching-the-real-silverado-ui-calibration-driven) (it holds no hook text; the Xposed/LSPosed-style hook is only proposed, in this doc's [Verdict](#verdict-summary), and was never attempted), locked-radio verdicts in [security.md](security.md).

- **Device:** GM Info 3.7 (gminfo37)
- **Source:** static RE of decompiled `GMSystemUI.jadx` and `GMHomeScreen.jadx` (jadx names such as `f40185b`, `C3292z`, `p016g0/c.java` are tied to one jadx build; no firmware build ID was recorded in the source, so they are not reproducible against a stated build)
- **Research date:** 2026-09-27; edits through 2026-11-17
- **Evidence:** static decompile unless stated. One bench result (section 1) is labelled. The Cinemo APK was not decompiled.
- **Legend:** [C] = corrected finding (folded inline).

Result: both gates are hardcoded Java; neither has a non-calibration, non-root lever on a locked radio (see Verdict).

Related: [emulator.md](emulator.md), [security.md](security.md), [vehicle_config.md](vehicle_config.md) (CalSets.db / SCREEN_RESOLUTION)

## 1. CardView panel existence: calibration-gated

The CardView clock/widget panel's existence is gated by `CalibrationManager.getEnumeration("SCREEN_RESOLUTION")==4`, a hardcoded Java branch in `GMCarStatusBar.i3()` (line ~711-714) feeding `GMCarStatusBar.g1()` (line ~1238). `g1()` calls `com.gm.cardview.model.g.e()` to inflate and attach the panel as a WindowManager overlay (type 2024). No resource/prop/Settings fallback exists anywhere in this path.

`com.gm.cardview.model.g.d().e(...)` has no internal gate; it always builds and attaches when called. The only creation gate is the caller-site check.

**[C] Read-site count.** At least 4-5 read sites exist across both apps: `GMCarStatusBar.java:711`, `com/gm/statusbar/C0.java:307`, `com/gm/statusbar/q0.java:114`, `T/A.java:23` (GMHomeScreen), plus the `X.e.SIZE_2400_BY_960` enum path `HomeScreenActivity.java:415` (section 5). An earlier pass claimed "only these two call sites" for `SCREEN_RESOLUTION`/`SIZE_2400`/`1133`; that undercounted. The conclusion is unchanged: every site traces to the same `CalibrationManager`/`SCREEN_RESOLUTION` source, none is an independent resource/prop/Settings fallback.

**Fallback behavior (2026-11-17, source reinspection of `com/gm/common/GMCarStatusBar.java`).** `i3()` reads `getEnumeration("SCREEN_RESOLUTION", 3)` (fallback 3); `g1()` creates CardView only when the result is 4. Physical/VM display dimensions are not queried at this branch. An unavailable calibration returning fallback 3 is a concrete possible cause of a missing panel, not a proven explanation of every historical intermittent failure. No new independent Y181 binary comparison was done.

**Bench result [bench-observed].** Changing global SCREEN_RESOLUTION 4->2 was accepted but produced owner-observed display tearing. Restoring stock slot08 / 2400x960 restored normal output, with clean settled calibration statuses. Do not repeat the global resolution change as a proven panel-only control. CardView is distinct from HomeScreen `Porch_View_Enabled`, whose separate display-size gate was traced in the source (that trace is not reproduced in this doc; the 2026-11-17 Porch_View_Enabled=true trial and its display-size caveat are in the 2026-11-17 row of the [can_bench_experiments.md](can_bench_experiments.md) trial table). Current bench evidence: [CALSETSDB_HAND_EDITING_CHECKSUM_SHA256.md](../research/eeprom-calibration/CALSETSDB_HAND_EDITING_CHECKSUM_SHA256.md#screen_resolution-1280x768-can-trial--2026-11-17).

**Emulator consequences (pointer).** A 2400x960 VM can lack the panel when its effective calibration is not 4 (fallback 3 path above). A narrowly scoped inverse experiment (suppress CardView creation at the call site or its visibility controller on a rooted VM, keeping display geometry and calibration 4) is proposed, not performed; hiding the window does not show other apps reclaim the area; layout/insets and foreground-app behavior would need separate verification. No supported stock-radio shell/CAN toggle for this gate was established. Details: [emulator.md](emulator.md#matching-the-real-silverado-ui-calibration-driven).

## 2. SystemUI app-capability allow-list (`WhiteList.java`)

`com/gm/cardview/utils/d.java` in GMSystemUI (jadx-recovered name `WhiteList.java`) is a hardcoded `static{}` initializer populating 8 `static List` fields with activity class names and package names. Three are quoted:

```java
f40185b.add("com.gm.hmi.energy.ui.activity.CloseableFullScreenActivity")
f40185b.add("com.gm.teenmode.presentation.seatbelt.SeatBeltRestrictionModeActivity")
f40185b.add("com.gm.hmi.onstarui.ui.activities.PopUpActivity")
f40185b.add("com.gm.offroad.presentation.crabmode.CrabModeActivity")
f40186c.add("com.gm.offroad.presentation.main.MainActivity")
f40186c.add("com.gm.hmi.androidauto.ui.activities.AndroidAutoProjectionActivity")
f40187d.add("com.gm.hmi.radio")   // + "com.android.car.media", "com.gm.gmmedia",
                                   //   "com.gm.hmi.sxm", "com.gm.gmaudio.server"
```

The list is consumed by `com/gm/cardview/utils/b.java` (`CardViewComponentUtils`), which exposes these predicates:

| Method | Field checked | Meaning |
|---|---|---|
| `p()` | `f40184a` | is the top activity a dialog |
| `s()` | `f40185b` | is it eligible to hide CardView / go immersive |
| `t()` | `f40186c` | is it full-screen without hiding CardView; the method actually invoked live (`com/gm/cardview/model/p.java:171`, `com/gm/cardview/view/CardView.java:709`). `q()`/`w()`/`r()` are separate predicates that do NOT read `f40186c` |
| `i()` | hardcoded, not WhiteList | `"com.gm.hmi.androidauto".equals(pkg)`: the actual Android-Auto special case, independent of any WhiteList field |
| `F()` | `f40187d` | is it an audio-focus package |

## 3. CarPlay vs Android Auto asymmetry

Native Cinemo CarPlay's activity, `com.gm.hmi.applecarplay/.ui.activities.AppleCarPlayProjectionActivity` (component name confirmed from GMSystemUI `C3292z.java:34` and GMHomeScreen `p016g0/c.java:46`, `T/C0124q.java:65`), does **not** appear in any of the 8 `WhiteList` lists; grep found zero hits for `applecarplay`/`AppleCarPlayProjectionActivity` in `d.java`.

Android Auto (`com.gm.hmi.androidauto`) **is** granted a capability: present in `f40186c` (read by `t()`, not `q()`/`w()`/`r()` as an earlier pass mischaracterized) and separately special-cased by the hardcoded package check in `i()`. CarPlay is therefore treated as a fully generic 3P activity by this gate.

## 4. Immersive/CardView-hide gate

`com/gm/cardview/controller/x.java` (`VisibilityController.g()`, line ~170-174):

```java
if (this.f40100e.v() && com.gm.cardview.utils.b.s(componentName)) { /* hide CardView */ }
```

`b.s(ComponentName)` (`b.java:276-281`):

```java
return (d.f40185b.contains(componentName.getClassName())
        || "com.gm.drivemode".equals(componentName.getPackageName())) && !K();
```

The decision is keyed purely on class-name/package-name membership in the hardcoded `WhiteList`. It is orthogonal to Android's `SYSTEM_UI_FLAG_IMMERSIVE`/`WindowInsetsController` mechanism: an app requesting standard immersive mode via its own window flags has no effect on whether GMSystemUI's separate always-on-top CardView overlay hides. Grep shows no `addInsetsSource`/inset-type mapping calls anywhere in `SystemUIOverlayWindowManager.java` for the CardView column.

Consequence: a custom 3P app claiming immersive status to hide SystemUI works for that app, but native Cinemo CarPlay cannot be made to hide CardView by requesting immersive; GMSystemUI only checks hardcoded identity.

## 5. Bounds computation: falsified hypothesis [C]

`HomeScreenActivity.java:415` (a hardcoded `SCREEN_RESOLUTION==SIZE_2400_BY_960 && densityDpi==200` branch reserving `R.dimen.containerWidth`) was hypothesized to gate CarPlay's window bounds. Traced further, the View it resizes (`f4727D`) is a **decorative divider line** inside GMHomeScreen's launcher grid, not a container for CarPlay/3P content. Evidence: its subsequent `setSystemUiVisibility(FLAG_IS_DIVIDER_BAR)` call, and `containerWidth` having exactly one consumer in the decompiled tree.

CarPlay is launched as a plain foreground Activity via `context.startActivity(intent, ActivityOptions.makeBasic().toBundle())` (`com/gm/homescreen/app/p.java:373`); GMHomeScreen/GMSystemUI set no launch bounds, TaskView, or DisplayArea assignment for it.

Removing/hiding CardView (via the `b.s()` gate) is necessary but not independently sufficient for CarPlay to expand into the freed area. Whether Cinemo fills it is Cinemo's own layout logic inside the `com.gm.hmi.applecarplay` APK, which was not in the decompile set.

**Open item (needs Cinemo APK decompiled):** the dev-options DPI-change behavior (shrinking SystemUI via display density measurably changes CarPlay's rendered UI density/element count) suggests Cinemo reads live display metrics/safe-area rather than a fixed resolution. This is an inference from observed behavior, not proven from Cinemo code.

## Verdict (summary)

- Locked radio (AVB + enforcing SELinux + no root + no bootloader unlock): no non-cal, non-root lever was found for (a) hiding the CardView panel or (b) granting CarPlay the whitelisted/immersive capability. Absence is established for the decompiled path only (no RRO-targetable resource, system property, or Settings key).
- RRO install, `setprop`, `wm density` (beyond its cosmetic divider-width effect) and Settings writes each need `CHANGE_OVERLAY_PACKAGES`/system/root, which AVB, the locked bootloader and enforced SELinux deny.
- Full locked-radio reasoning: [security.md](security.md).
- Emulator (root): CardView lever is a `CalSets.db` `SCREEN_RESOLUTION` write ([emulator.md](emulator.md#matching-the-real-silverado-ui-calibration-driven)). Allow-list/immersive lever would be a root-required Xposed/LSPosed-style hook on `CardViewComponentUtils.s()` or runtime injection of CarPlay's class into `WhiteList`; queued, not attempted; no hook PoC exists in this or any other doc. emulator.md covers only the CalSets.db lever.

## History

- 2026-09: read-site recount (4-5 sites, not 2); `t()` vs `q()/w()/r()` correction; section 5 divider-line correction.
- 2026-11-17: fallback-3 finding, SCREEN_RESOLUTION 4->2 bench result, inverse-experiment proposal added; dead link to SCREEN_RESOLUTION_END_TO_END_WORKFLOW replaced by the CALSETSDB link.

## Open conflicts

None.
