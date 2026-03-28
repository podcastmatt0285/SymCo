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
SIGNING_KEY="wadsworth-key.jks"
KEY_ALIAS="wadsworth"

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

# Custom TrustedWebActivityService — intercepts Chrome's channel creation to
# lock in our notification sound before Chrome can create the channel with a
# default sound (Android never overwrites an existing NotificationChannel).
sed "s/PACKAGE_NAME/${PACKAGE}/g" "${WIDGET_DIR}/WadsworthTwaService.java" \
    > "${JAVA_DIR}/WadsworthTwaService.java"
echo "  Copied WadsworthTwaService.java → ${JAVA_DIR}/"

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

# 1. Replace Bubblewrap's default TrustedWebActivityService with our subclass
#    so Chrome calls into WadsworthTwaService.onAreNotificationsEnabled() where
#    we pre-seed the notification channel with the custom sound.
if grep -q "WadsworthTwaService" "$MANIFEST"; then
    echo "  WadsworthTwaService already in AndroidManifest.xml — skipping"
else
    sed -i "s|com.google.androidbrowserhelper.trusted.TrustedWebActivityService|${PACKAGE}.WadsworthTwaService|g" "$MANIFEST"
    echo "  Patched TrustedWebActivityService → WadsworthTwaService"
fi

# 2. Inject AppWidget receiver
RECEIVER_BLOCK="        <receiver android:name=\"${PACKAGE}.WadsworthWidget\" android:exported=\"true\"><intent-filter><action android:name=\"android.appwidget.action.APPWIDGET_UPDATE\"/></intent-filter><meta-data android:name=\"android.appwidget.provider\" android:resource=\"@xml/wadsworth_widget_info\"/></receiver>"

if grep -q "WadsworthWidget" "$MANIFEST"; then
    echo "  WadsworthWidget already in AndroidManifest.xml — skipping"
else
    sed -i "s|</application>|${RECEIVER_BLOCK}\n    </application>|" "$MANIFEST"
    echo "  Injected WadsworthWidget receiver into AndroidManifest.xml"
fi

# ProGuard/R8 keep rules — prevent shrinking of our injected classes
PROGUARD_RULES="app/proguard-rules.pro"
if grep -q "WadsworthWidget" "$PROGUARD_RULES" 2>/dev/null; then
    echo "  ProGuard rules already present — skipping"
else
    cat >> "$PROGUARD_RULES" << 'EOF'

# Keep widget + notification-service classes (referenced by manifest, not by Java)
-keep class PACKAGE_PLACEHOLDER.WadsworthWidget { *; }
-keep class PACKAGE_PLACEHOLDER.WadsworthTwaService { *; }
EOF
    sed -i "s/PACKAGE_PLACEHOLDER/${PACKAGE}/g" "$PROGUARD_RULES"
    echo "  Added ProGuard keep rules"
fi

echo "=== Step 4: Generate signing key (skip if reusing) ==="
cd ..
if [ ! -f "${SIGNING_KEY}" ]; then
    keytool -genkey -v \
        -keystore "${SIGNING_KEY}" \
        -alias "${KEY_ALIAS}" \
        -keyalg RSA -keysize 2048 \
        -validity 10000 \
        -storepass wadsworth123 \
        -keypass wadsworth123 \
        -dname "CN=Wadsworth, OU=Game, O=Wadsworth, L=US, ST=US, C=US"
    echo "  Key generated: ${SIGNING_KEY}"
else
    echo "  Reusing existing ${SIGNING_KEY}"
fi
cd twa-project

echo "=== Step 5: Build and sign APK ==="
bubblewrap build \
    --keyPath "../${SIGNING_KEY}" \
    --keyAlias "${KEY_ALIAS}" \
    --keystorePassword "wadsworth123" \
    --keyPassword "wadsworth123"

cp app-release-signed.apk "../wadsworth-signed.apk"
cd ..

echo ""
echo "✅  Done!  APK is at: $(pwd)/wadsworth-signed.apk"
echo "    Install on device:  adb install wadsworth-signed.apk"
