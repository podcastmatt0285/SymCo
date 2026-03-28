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

echo "=== Step 3: Inject widget files ==="

# Java source
JAVA_DIR="app/src/main/java/$(echo "$PACKAGE" | tr '.' '/')"
mkdir -p "$JAVA_DIR"
sed "s/PACKAGE_NAME/${PACKAGE}/g" "${WIDGET_DIR}/WadsworthWidget.java" \
    > "${JAVA_DIR}/WadsworthWidget.java"
echo "  Copied WadsworthWidget.java → ${JAVA_DIR}/"

# Resource files
cp "${WIDGET_DIR}/res/layout/widget_layout.xml"        app/src/main/res/layout/
cp "${WIDGET_DIR}/res/xml/wadsworth_widget_info.xml"   app/src/main/res/xml/
cp "${WIDGET_DIR}/res/drawable/widget_background.xml"  app/src/main/res/drawable/
echo "  Copied layout, xml, drawable resources"

# Merge strings — append widget_description before </resources>
STRINGS_FILE="app/src/main/res/values/strings.xml"
if grep -q "widget_description" "$STRINGS_FILE" 2>/dev/null; then
    echo "  widget_description already in strings.xml — skipping"
else
    sed -i 's|</resources>|    <string name="widget_description">Live balance, alerts, and market tickers</string>\n</resources>|' "$STRINGS_FILE"
    echo "  Added widget_description to strings.xml"
fi

# Inject receiver into AndroidManifest.xml before </application>
MANIFEST="app/src/main/AndroidManifest.xml"
RECEIVER_BLOCK="        <receiver android:name=\"${PACKAGE}.WadsworthWidget\" android:exported=\"true\"><intent-filter><action android:name=\"android.appwidget.action.APPWIDGET_UPDATE\"/></intent-filter><meta-data android:name=\"android.appwidget.provider\" android:resource=\"@xml/wadsworth_widget_info\"/></receiver>"

if grep -q "WadsworthWidget" "$MANIFEST"; then
    echo "  WadsworthWidget already in AndroidManifest.xml — skipping"
else
    sed -i "s|</application>|${RECEIVER_BLOCK}\n    </application>|" "$MANIFEST"
    echo "  Injected WadsworthWidget receiver into AndroidManifest.xml"
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

cp app/build/outputs/apk/release/app-release.apk "../wadsworth-signed.apk"
cd ..

echo ""
echo "✅  Done!  APK is at: $(pwd)/wadsworth-signed.apk"
echo "    Install on device:  adb install wadsworth-signed.apk"
