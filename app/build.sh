#!/usr/bin/env bash
# Build the sketchpad wrapper app with plain javac + the Android build-tools (no Gradle, no Android Studio).
#   app/build.sh            build -> $OUT/sketchpad.apk
#   app/build.sh install    build, then adb install -r over USB
# Needs: JDK, Android build-tools 34 + platform android-34 (android.jar) in $ANDROID_SDK (default /mnt/sandbox/android-sdk).
# Build output goes to the sandbox partition; the signing key lives in ~/.config/sketchpad-app (600).
set -euo pipefail

SDK="${ANDROID_SDK:-/mnt/sandbox/android-sdk}"
BT="$SDK/build-tools/34.0.0"
JAR="$SDK/platforms/android-34/android.jar"
HERE="$(cd "$(dirname "$0")" && pwd)"
OUT="${SKETCHPAD_APP_BUILD:-/mnt/sandbox/sketchpad-app}"
KDIR="$HOME/.config/sketchpad-app"

[[ -x "$BT/aapt2" && -f "$JAR" ]] || { echo "Android SDK pieces not found in $SDK (need build-tools/34.0.0 and platforms/android-34/android.jar)" >&2; exit 1; }

if [[ ! -f "$KDIR/debug.jks" ]]; then
  mkdir -p "$KDIR"; chmod 700 "$KDIR"
  (umask 077; head -c 18 /dev/urandom | base64 | tr -d '=+/\n' >"$KDIR/ks.pass")
  keytool -genkeypair -keystore "$KDIR/debug.jks" -storepass "$(cat "$KDIR/ks.pass")" -keypass "$(cat "$KDIR/ks.pass")" \
    -alias sketchpad -keyalg RSA -keysize 2048 -validity 9125 -dname "CN=sketchpad local" >/dev/null 2>&1
  chmod 600 "$KDIR/debug.jks"
fi

rm -rf "$OUT"; mkdir -p "$OUT/gen" "$OUT/classes"
"$BT/aapt2" compile --dir "$HERE/res" -o "$OUT/res.zip"
"$BT/aapt2" link -o "$OUT/base.apk" -I "$JAR" --manifest "$HERE/AndroidManifest.xml" \
  --min-sdk-version 30 --target-sdk-version 34 --java "$OUT/gen" "$OUT/res.zip"
javac --release 8 -g:none -Xlint:-options -cp "$JAR" -d "$OUT/classes" $(find "$HERE/src" "$OUT/gen" -name '*.java')
"$BT/d8" --lib "$JAR" --min-api 30 --output "$OUT" $(find "$OUT/classes" -name '*.class')
(cd "$OUT" && zip -q base.apk classes.dex)
"$BT/zipalign" -f 4 "$OUT/base.apk" "$OUT/aligned.apk"
"$BT/apksigner" sign --ks "$KDIR/debug.jks" --ks-pass "file:$KDIR/ks.pass" --out "$OUT/sketchpad.apk" "$OUT/aligned.apk"
echo "built $OUT/sketchpad.apk ($(du -h "$OUT/sketchpad.apk" | cut -f1))"

if [[ "${1:-}" == "install" ]]; then adb install -r "$OUT/sketchpad.apk"; fi
