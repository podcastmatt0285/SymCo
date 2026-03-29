#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# build-apk.sh — Build the Wadsworth Android APK with home-screen widget
#
# Requirements:
#   - Node.js 18+  (https://nodejs.org)
#   - Java JDK 17+ (https://adoptium.net)
#   - Android SDK  (set ANDROID_HOME env var, or install Android Studio)
#
# Usage:
#   chmod +x android/build-apk.sh
#   cd android
#   ./build-apk.sh
#
# Output: wadsworth-signed.apk in this directory
# ─────────────────────────────────────────────────────────────────────────────
set -e

DOMAIN="wadsworth.notifly.cc"
APP_NAME="Wadsworth"
PACKAGE="cc.notifly.wadsworth"           # ← change if yours differs
VERSION_CODE=2
VERSION_NAME="1.1"

WIDGET_DIR="$(cd "$(dirname "$0")/widget" && pwd)"

echo "=== Step 1: Install Bubblewrap CLI ==="
npm install -g @bubblewrap/cli 2>/dev/null || true
which bubblewrap || { echo "bubblewrap not found — install failed"; exit 1; }

echo "=== Step 2: Generate TWA project ==="
rm -rf twa-project && mkdir twa-project && cd twa-project

bubblewrap init \
  --manifest "https://${DOMAIN}/manifest.json" \
  --directory . \
  --packageId "${PACKAGE}" \
  --name "${APP_NAME}" \
  --appVersionCode "${VERSION_CODE}" \
  --appVersionName "${VERSION_NAME}"

echo "=== Step 3: Inject widget + notification-sound files ==="

# Java source directory
JAVA_DIR="app/src/main/java/$(echo "$PACKAGE" | tr '.' '/')"
mkdir -p "$JAVA_DIR"

# AppWidget provider
sed "s/PACKAGE_NAME/${PACKAGE}/g" "${WIDGET_DIR}/WadsworthWidget.java" \
    > "${JAVA_DIR}/WadsworthWidget.java"
echo "  Copied WadsworthWidget.java → ${JAVA_DIR}/"

# Custom Application subclass — pre-seeds notification channels with our
# sound at startup before Chrome/TWA can create them with the system default.
sed "s/PACKAGE_NAME/${PACKAGE}/g" "${WIDGET_DIR}/WadsworthApplication.java" \
    > "${JAVA_DIR}/WadsworthApplication.java"
echo "  Copied WadsworthApplication.java → ${JAVA_DIR}/"

# Token activity — receives widget auth token from web app via intent:// URL
# and stores it in SharedPreferences for the widget to read.
sed "s/PACKAGE_NAME/${PACKAGE}/g" "${WIDGET_DIR}/WadsworthTokenActivity.java" \
    > "${JAVA_DIR}/WadsworthTokenActivity.java"
echo "  Copied WadsworthTokenActivity.java → ${JAVA_DIR}/"

# LauncherActivity — overrides getLaunchingUrl() to append ?_wdid=sha256(ANDROID_ID)
# so the web app can silently link this device to the player session for widget auth.
# Must be copied AFTER bubblewrap init since init regenerates twa-project from scratch.
mkdir -p "${JAVA_DIR}/twa"
sed "s/PACKAGE_NAME/${PACKAGE}.twa/g" "${WIDGET_DIR}/LauncherActivity.java" \
    > "${JAVA_DIR}/twa/LauncherActivity.java"
echo "  Patched LauncherActivity.java → ${JAVA_DIR}/twa/"

# Resource directories (Bubblewrap doesn't create these)
mkdir -p app/src/main/res/layout
mkdir -p app/src/main/res/xml
mkdir -p app/src/main/res/drawable
mkdir -p app/src/main/res/raw

# Widget layout + metadata
cp "${WIDGET_DIR}/res/layout/widget_layout.xml"        app/src/main/res/layout/
cp "${WIDGET_DIR}/res/xml/wadsworth_widget_info.xml"   app/src/main/res/xml/
cp "${WIDGET_DIR}/res/drawable/widget_background.xml"  app/src/main/res/drawable/
echo "  Copied widget layout, xml, drawable resources"

# Reduce Gradle JVM heap — default 1.5 GB kills the daemon on low-RAM machines.
# Also disable the persistent daemon so each build starts clean.
cat >> gradle.properties << 'GPROPS'
org.gradle.jvmargs=-Xmx512m -Dfile.encoding=UTF-8
org.gradle.daemon=false
GPROPS
echo "  Set Gradle heap to 512m, daemon disabled"

# sdk.dir — Gradle needs this; bubblewrap installs the SDK here by default.
SDK_DIR="${ANDROID_HOME:-$HOME/.bubblewrap/android_sdk}"
echo "sdk.dir=${SDK_DIR}" > local.properties
echo "  Set sdk.dir=${SDK_DIR}"

# Gradle's Groovy DSL cannot compile on Java 22+. Point it at Java 17 if needed.
_JV=$(java -version 2>&1 | grep -oE '"[0-9]+' | grep -oE '[0-9]+' | head -1)
if [ "${_JV:-0}" -gt 21 ]; then
    _COMPAT=$(update-alternatives --list java 2>/dev/null \
              | grep -E 'java-(17|18|19|20|21)-' | head -1 | sed 's|/bin/java$||')
    [ -z "$_COMPAT" ] && _COMPAT=$(ls -d /usr/lib/jvm/java-17-openjdk* \
        /usr/lib/jvm/java-21-openjdk* 2>/dev/null | head -1)
    if [ -n "$_COMPAT" ]; then
        echo "org.gradle.java.home=${_COMPAT}" >> gradle.properties
        echo "  Java $_JV too new for Groovy DSL — using ${_COMPAT}"
    else
        echo "ERROR: need Java 17 or 21.  Run: sudo apt install openjdk-17-jdk"; exit 1
    fi
fi

# Notification sound — copy from the live static directory so it matches
# whatever sound the admin uploaded via the dashboard.
SOUND_SRC="$(cd "$(dirname "$0")/.." && pwd)/static/sounds/notification.mp3"
if [ -f "$SOUND_SRC" ]; then
    cp "$SOUND_SRC" app/src/main/res/raw/notification.mp3
    echo "  Copied notification.mp3 → res/raw/"
else
    echo "  WARNING: static/sounds/notification.mp3 not found — push sound will use system default"
fi

# Merge strings — append widget_description before </resources>
STRINGS_FILE="app/src/main/res/values/strings.xml"
if grep -q "widget_description" "$STRINGS_FILE" 2>/dev/null; then
    echo "  widget_description already in strings.xml — skipping"
else
    sed -i 's|</resources>|    <string name="widget_description">Live balance, alerts, and market tickers</string>\n</resources>|' "$STRINGS_FILE"
    echo "  Added widget_description to strings.xml"
fi

# AndroidManifest.xml patches
MANIFEST="app/src/main/AndroidManifest.xml"

# 1. Point <application> at our custom Application subclass so channels are
#    seeded with the custom notification sound on every app launch.
if grep -q "WadsworthApplication" "$MANIFEST"; then
    echo "  WadsworthApplication already in AndroidManifest.xml — skipping"
else
    sed -i "s|<application |<application android:name=\"${PACKAGE}.WadsworthApplication\" |" "$MANIFEST"
    echo "  Set android:name=WadsworthApplication on <application>"
fi

# 2. Inject AppWidget receiver
RECEIVER_BLOCK="        <receiver android:name=\"${PACKAGE}.WadsworthWidget\" android:exported=\"true\"><intent-filter><action android:name=\"android.appwidget.action.APPWIDGET_UPDATE\"/><action android:name=\"${PACKAGE}.WIDGET_REFRESH\"/></intent-filter><meta-data android:name=\"android.appwidget.provider\" android:resource=\"@xml/wadsworth_widget_info\"/></receiver>"

if grep -q "WadsworthWidget" "$MANIFEST"; then
    echo "  WadsworthWidget already in AndroidManifest.xml — skipping"
else
    sed -i "s|</application>|${RECEIVER_BLOCK}\n    </application>|" "$MANIFEST"
    echo "  Injected WadsworthWidget receiver into AndroidManifest.xml"
fi

# 3. Inject token activity — handles wadsworth://widget-auth?token=... intents
#    fired by the web app JS to pass auth tokens into SharedPreferences.
TOKEN_ACTIVITY="        <activity android:name=\"${PACKAGE}.WadsworthTokenActivity\" android:exported=\"true\" android:theme=\"@android:style/Theme.NoDisplay\"><intent-filter><action android:name=\"android.intent.action.VIEW\"/><category android:name=\"android.intent.category.DEFAULT\"/><category android:name=\"android.intent.category.BROWSABLE\"/><data android:scheme=\"wadsworth\" android:host=\"widget-auth\"/></intent-filter></activity>"

if grep -q "WadsworthTokenActivity" "$MANIFEST"; then
    echo "  WadsworthTokenActivity already in AndroidManifest.xml — skipping"
else
    sed -i "s|</application>|${TOKEN_ACTIVITY}\n    </application>|" "$MANIFEST"
    echo "  Injected WadsworthTokenActivity into AndroidManifest.xml"
fi

# ProGuard/R8 keep rules — prevent shrinking of our injected classes
PROGUARD_RULES="app/proguard-rules.pro"
if grep -q "WadsworthWidget" "$PROGUARD_RULES" 2>/dev/null; then
    echo "  ProGuard rules already present — skipping"
else
    cat >> "$PROGUARD_RULES" << 'EOF'

# Keep widget + token classes (referenced by manifest, not by Java)
-keep class PACKAGE_PLACEHOLDER.WadsworthWidget { *; }
-keep class PACKAGE_PLACEHOLDER.WadsworthApplication { *; }
-keep class PACKAGE_PLACEHOLDER.WadsworthTokenActivity { *; }
EOF
    sed -i "s/PACKAGE_PLACEHOLDER/${PACKAGE}/g" "$PROGUARD_RULES"
    echo "  Added ProGuard keep rules"
fi

echo "=== Step 4: Create/reuse signing keystore (lives outside twa-project) ==="
# Stored in android/ so it survives 'rm -rf twa-project' on every rebuild.
cd ..
KEY_PASS="wadsworth123"
KEYSTORE_ABS="$(pwd)/wadsworth-signing.jks"
if [ ! -f "${KEYSTORE_ABS}" ]; then
    keytool -genkey -v \
        -keystore "${KEYSTORE_ABS}" \
        -alias android \
        -keyalg RSA -keysize 2048 \
        -validity 10000 \
        -storepass "${KEY_PASS}" \
        -keypass  "${KEY_PASS}" \
        -dname "CN=Wadsworth, OU=Game, O=Wadsworth, L=US, ST=US, C=US"
    echo "  Key generated: ${KEYSTORE_ABS}"
else
    echo "  Reusing existing ${KEYSTORE_ABS}"
fi
cd twa-project

echo "=== Step 5: Build and sign APK with Gradle ==="
# Pass signing credentials as project properties — no build.gradle modification needed.
# bubblewrap build always prompts interactively for passwords and ignores flags.
chmod +x gradlew
./gradlew assembleRelease \
    -Pandroid.injected.signing.store.file="${KEYSTORE_ABS}" \
    -Pandroid.injected.signing.store.password="${KEY_PASS}" \
    -Pandroid.injected.signing.key.alias=android \
    -Pandroid.injected.signing.key.password="${KEY_PASS}"

cp app/build/outputs/apk/release/app-release.apk "../wadsworth-signed.apk"
cd ..

echo ""
echo "✅  Done!  APK is at: $(pwd)/wadsworth-signed.apk"
echo "    Install on device:  adb install wadsworth-signed.apk"
