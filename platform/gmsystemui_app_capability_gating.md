# GMSystemUI App-Capability + Immersive Gating

**Device:** GM Info 3.7 (gminfo37)
**Source:** static RE of decompiled `GMSystemUI.jadx` and `GMHomeScreen.jadx`
**Research Date:** 2026-09-27

---

Prompted by investigating whether the CardView clock/widget panel and/or native Cinemo CarPlay's
screen bounds can be influenced without a calibration write. Two related, previously undocumented
code-level gates were located; neither has a non-calibration, non-root lever on a locked radio (see
Verdict).

## 1. CardView panel existence — calibration-gated (already known, restated for context)

The CardView clock/widget panel's very existence is gated by
`CalibrationManager.getEnumeration("SCREEN_RESOLUTION")==4` — a hardcoded Java branch in
`GMCarStatusBar.i3()` (line ~711-714) feeding `GMCarStatusBar.g1()` (line ~1238), which calls
`com.gm.cardview.model.g.e()` to inflate+attach the panel as a WindowManager overlay (type 2024). No
resource/prop/Settings fallback exists anywhere in this path — confirmed by grepping the whole
decompiled tree for `SCREEN_RESOLUTION`/`SIZE_2400`/`1133`, finding only these two call sites.
`com.gm.cardview.model.g.e()` itself has no internal gate — it always builds+attaches when called; the
only gate is the caller-site check. See `research/SCREEN_RESOLUTION_END_TO_END_WORKFLOW.md` for the
calibration-write procedure that changes this value.

## 2. NEW — the SystemUI app-capability allow-list (`WhiteList.java`)

`com/gm/cardview/utils/d.java` in GMSystemUI (jadx-recovered name `WhiteList.java`) is a hardcoded Java
`static{}` initializer populating 8 separate `static List` fields with activity class names and
package names. Quoted as given:

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

This list is consumed by `com/gm/cardview/utils/b.java` (`CardViewComponentUtils`), which exposes
predicates:

| Method | Field checked | Meaning |
|---|---|---|
| `p()` | `f40184a` | is the top activity a dialog |
| `s()` | `f40185b` | is it eligible to hide CardView / go immersive |
| `q()` / `w()` / `r()` | `f40186c` | is it full-screen without hiding CardView (special-cases Android Auto's package `com.gm.hmi.androidauto`) |
| `F()` | `f40187d` | is it an audio-focus package |

## 3. Where CarPlay sits — the asymmetry

Native Cinemo CarPlay's activity, `com.gm.hmi.applecarplay/.ui.activities.AppleCarPlayProjectionActivity`
(confirmed as its component name from GMSystemUI's `C3292z.java:34` and GMHomeScreen's
`p016g0/c.java:46`, `T/C0124q.java:65`), does **not** appear in any of the 8 `WhiteList` lists — grep
confirmed zero hits for `applecarplay`/`AppleCarPlayProjectionActivity` in `d.java`. By contrast Android
Auto (`com.gm.hmi.androidauto`) **is** granted a capability (present in `f40186c`, special-cased in
`q()`/`i()`). This asymmetry — Android Auto whitelisted, CarPlay not — means CarPlay is treated as a
fully generic 3P activity by this gate.

## 4. The immersive/CardView-hide gate — mechanism, and why it's orthogonal to Android's own immersive flags

`com/gm/cardview/controller/x.java` (`VisibilityController.g()`, line ~170-174):

```java
if (this.f40100e.v() && com.gm.cardview.utils.b.s(componentName)) { /* hide CardView */ }
```

`b.s(ComponentName)` (`b.java:276-281`):

```java
return (d.f40185b.contains(componentName.getClassName())
        || "com.gm.drivemode".equals(componentName.getPackageName())) && !K();
```

**Critical point:** this decision is keyed purely on class-name/package-name membership in the
hardcoded `WhiteList` — it is completely orthogonal to Android's standard
`SYSTEM_UI_FLAG_IMMERSIVE`/`WindowInsetsController` mechanism. An app requesting standard Android
immersive mode via its own window flags has no effect on whether GMSystemUI's separate always-on-top
CardView overlay window hides itself — that decision is made unilaterally by GMSystemUI checking the
foreground activity's identity against this list (confirmed by grep showing no
`addInsetsSource`/inset-type mapping calls anywhere in `SystemUIOverlayWindowManager.java` for the
CardView column). This is the concrete, code-level reason a workaround project (a custom 3P app
claiming immersive status to hide SystemUI, achieving true fullscreen for itself) works for a 3P app but
cannot be replicated by getting native Cinemo CarPlay itself to "ask nicely" for immersive —
GMSystemUI's gate doesn't listen to that request at all, only to hardcoded identity.

## 5. Bounds computation — a falsified hypothesis, corrected

`HomeScreenActivity.java:415` (a hardcoded `SCREEN_RESOLUTION==SIZE_2400_BY_960 && densityDpi==200`
branch reserving `R.dimen.containerWidth`) was initially hypothesized to gate CarPlay's own window
bounds. Traced further: the View it resizes (`f4727D`) is confirmed, by its subsequent
`setSystemUiVisibility(FLAG_IS_DIVIDER_BAR)` call and by `containerWidth` having exactly one consumer
in the whole decompiled tree, to be a **decorative divider line** inside GMHomeScreen's own launcher
grid — **not** a container that hosts or constrains CarPlay/3P content. CarPlay is launched as a plain
foreground Activity via `context.startActivity(intent, ActivityOptions.makeBasic().toBundle())`
(`com/gm/homescreen/app/p.java:373`) — no launch bounds, no TaskView, no DisplayArea assignment is set
by GMHomeScreen/GMSystemUI for CarPlay's window at all.

So removing/hiding CardView (via the `b.s()` gate above) is a necessary but **not** independently
sufficient condition for CarPlay to visually expand into the freed screen area — whether Cinemo's own
internal rendering would actually fill that space is Cinemo's own internal layout logic, inside the
`com.gm.hmi.applecarplay` APK, which was **not** part of this decompile set.

**Open item — needs the Cinemo APK decompiled to confirm/refute:** the dev-options DPI-change behavior
already observed (shrinking SystemUI via display density measurably changes CarPlay's own rendered UI
density/element-count) is suggestive that Cinemo reads live display metrics/safe-area rather than
assuming a fixed resolution — but this is an inference from observed behavior, not yet proven from
Cinemo's own decompiled code.

## Verdict — locked radio vs. emulator (same underlying pattern as the CalSet-write lock)

On a stock **locked** radio (AVB + enforcing SELinux + no root + no bootloader unlock), there is **no**
non-cal, non-root lever for either (a) removing/hiding the CardView panel, or (b) granting native
Cinemo CarPlay the whitelisted/immersive capability. Both gates are hardcoded Java code (a calibration
value branch for CardView's existence; a hardcoded class-name list for the hide/immersive decision)
with no resource (RRO-targetable), system-property, or Settings-key fallback found anywhere in the
decompiled path. Every lever that could otherwise reach this code (installing/enabling a Runtime
Resource Overlay, `setprop`, `wm density` beyond its cosmetic divider-width effect, a Settings write)
independently requires `CHANGE_OVERLAY_PACKAGES`/system/root privilege that AVB + the locked bootloader
+ enforced SELinux deny.

On the **emulator** specifically (root available): the working lever for the CardView case is a direct
`CalSets.db` `SCREEN_RESOLUTION` write (already used this session — see
[`emulator.md`](emulator.md#matching-the-real-silverado-ui-calibration-driven)). For the
allow-list/immersive case, a root-required in-memory method hook (e.g. Xposed/LSPosed-style, hooking
`CardViewComponentUtils.s()` or injecting CarPlay's class into the `WhiteList` at runtime) would be the
emulator-side proof-of-concept — **queued, not yet attempted this session.**
