#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
SDK="${ANDROID_SDK_ROOT:-$HOME/Library/Android/sdk}"
TOOLS="${AAOS_BUILD_TOOLS:-$SDK/build-tools/35.0.0}"
ANDROID_JAR="${AAOS_ANDROID_JAR:-$SDK/platforms/android-32/android.jar}"
export JAVA_HOME="${AAOS_JAVA_HOME:-/opt/homebrew/opt/openjdk@25/libexec/openjdk.jdk/Contents/Home}"
KEYSTORE="${AAOS_DEBUG_KEYSTORE:-$HOME/.android/debug.keystore}"
BUILD="$ROOT/build"
[[ -f "$KEYSTORE" ]] || { echo 'Existing Android debug keystore required via AAOS_DEBUG_KEYSTORE' >&2; exit 1; }
mkdir -p "$BUILD/classes" "$BUILD/dex" "$BUILD/generated"
"$TOOLS/aapt2" link -I "$ANDROID_JAR" --manifest "$ROOT/AndroidManifest.xml" \
    --java "$BUILD/generated" -o "$BUILD/base.apk"
"$JAVA_HOME/bin/javac" --release 8 -classpath "$ANDROID_JAR" -d "$BUILD/classes" \
    "$ROOT/src/org/gminfo/audioprobe/MainActivity.java"
"$TOOLS/d8" --lib "$ANDROID_JAR" --min-api 26 --output "$BUILD/dex" \
    "$BUILD/classes/org/gminfo/audioprobe/"*.class
cp "$BUILD/base.apk" "$BUILD/unsigned.apk"
zip -q -j "$BUILD/unsigned.apk" "$BUILD/dex/classes.dex"
"$TOOLS/zipalign" -f 4 "$BUILD/unsigned.apk" "$BUILD/aligned.apk"
"$TOOLS/apksigner" sign --ks "$KEYSTORE" --ks-key-alias androiddebugkey \
    --ks-pass pass:android --key-pass pass:android \
    --out "$BUILD/aaos-audio-probe.apk" "$BUILD/aligned.apk"
"$TOOLS/apksigner" verify "$BUILD/aaos-audio-probe.apk"
echo "APK: $BUILD/aaos-audio-probe.apk"
