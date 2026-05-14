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
# Output: wadsworth-signed.apk and wadsworth-signed.aab in this directory
# ─────────────────────────────────────────────────────────────────────────────
set -e

DOMAIN="wadsworth.notifly.cc"
APP_NAME="Wadsworth"
PACKAGE="cc.notifly.wadsworth"           # ← change if yours differs
VERSION_CODE=17
VERSION_NAME="1.17"

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
WIDGET_DIR="${SCRIPT_DIR}/widget"
KEY_PASS="wadsworth123"
KEYSTORE_ABS="${SCRIPT_DIR}/wadsworth-signing.jks"

echo "=== Step 0: Check system dependencies ==="
if ! which java &>/dev/null; then
    echo "  Java not found — installing openjdk-17-jdk..."
    sudo apt-get update -qq && sudo apt-get install -y openjdk-17-jdk
fi
java -version 2>&1 | head -1

if ! which npm &>/dev/null; then
    echo "  Node.js/npm not found — installing..."
    sudo apt-get update -qq && sudo apt-get install -y nodejs npm
fi
echo "  npm $(npm --version), node $(node --version)"

# Check git identity — must be set before the build so the post-build commit works
if [ -z "$(git config --global user.email 2>/dev/null)" ]; then
    echo ""
    echo "ERROR: git identity not configured. Run:"
    echo "  git config --global user.email \"you@example.com\""
    echo "  git config --global user.name  \"Your Name\""
    exit 1
fi

echo "=== Step 1: Install Bubblewrap CLI ==="
npm config set prefix "$HOME/.npm-global"
export PATH="$HOME/.npm-global/bin:$PATH"
export NO_UPDATE_NOTIFIER=1
if ! which bubblewrap &>/dev/null; then
    npm install -g @bubblewrap/cli --registry https://registry.npmmirror.com
    which bubblewrap || { echo "bubblewrap not found — install failed"; exit 1; }
fi
echo "  bubblewrap ready"

echo "=== Step 2: Create/reuse signing keystore ==="
# Must happen BEFORE bubblewrap init so we can pass it as flags and avoid
# interactive prompts. The file lives in android/ so it survives rm -rf twa-project.
if [ ! -f "${KEYSTORE_ABS}" ]; then
    keytool -genkey -v \
        -keystore "${KEYSTORE_ABS}" \
        -alias android \
        -keyalg RSA -keysize 2048 \
        -validity 10000 \
        -storepass "${KEY_PASS}" \
        -keypass  "${KEY_PASS}" \
        -dname "CN=Wadsworth, OU=Game, O=Wadsworth, L=US, ST=US, C=US"
    echo "  New keystore generated: ${KEYSTORE_ABS}"
else
    echo "  Reusing existing keystore: ${KEYSTORE_ABS}"
fi
FINGERPRINT=$(keytool -list -v -keystore "${KEYSTORE_ABS}" -alias android \
    -storepass "${KEY_PASS}" 2>/dev/null | grep "SHA256:" | awk '{print $2}')
echo "  SHA-256: ${FINGERPRINT}"
echo "  (must match assetlinks.json in app.py — update it if this is a new keystore)"

echo "=== Step 3: Generate TWA project (no prompts — write twa-manifest.json directly) ==="
rm -rf twa-project && mkdir twa-project && cd twa-project

# Write twa-manifest.json with all values hardcoded. This bypasses `bubblewrap init`
# and its 20+ interactive prompts entirely. `bubblewrap update` reads this file and
# generates the full Android project structure from templates — no user input, no
# network calls, no SDK required for this step.
cat > twa-manifest.json << TWAMF
{
  "packageId": "${PACKAGE}.twa",
  "host": "${DOMAIN}",
  "name": "Wadsworth Economic Tycoon Simulator",
  "launcherName": "Wadsworth",
  "display": "fullscreen",
  "themeColor": "#020617",
  "themeColorDark": "#020617",
  "navigationColor": "#020617",
  "navigationColorDark": "#020617",
  "navigationDividerColor": "#020617",
  "navigationDividerColorDark": "#020617",
  "backgroundColor": "#020617",
  "enableNotifications": true,
  "startUrl": "/",
  "iconUrl": "https://${DOMAIN}/static/icons/icon-512.png",
  "maskableIconUrl": "https://${DOMAIN}/static/icons/android/launchericon-512x512.png",
  "monochromeIconUrl": "https://${DOMAIN}/static/icons/android/launchericon-512x512.png",
  "splashScreenFadeOutDuration": 300,
  "signingKey": {
    "path": "${KEYSTORE_ABS}",
    "alias": "android"
  },
  "appVersion": "${VERSION_NAME}",
  "appVersionName": "${VERSION_NAME}",
  "appVersionCode": ${VERSION_CODE},
  "shortcuts": [
    { "name": "Businesses", "shortName": "Biz",   "url": "https://${DOMAIN}/businesses", "chosenIconUrl": "https://${DOMAIN}/static/icons/icon-192.png" },
    { "name": "Market",     "shortName": "Market", "url": "https://${DOMAIN}/market",     "chosenIconUrl": "https://${DOMAIN}/static/icons/icon-192.png" },
    { "name": "Banks",      "shortName": "Banks",  "url": "https://${DOMAIN}/banks",      "chosenIconUrl": "https://${DOMAIN}/static/icons/icon-192.png" },
    { "name": "P2P",        "shortName": "P2P",    "url": "https://${DOMAIN}/p2p",        "chosenIconUrl": "https://${DOMAIN}/static/icons/icon-192.png" }
  ],
  "generatorApp": "bubblewrap-cli",
  "webManifestUrl": "https://${DOMAIN}/manifest.json",
  "fallbackType": "customtabs",
  "features": { "playBilling": { "enabled": false } },
  "alphaDependencies": { "enabled": false },
  "enableSiteSettingsShortcut": true,
  "isChromeOSOnly": false,
  "isMetaQuest": false,
  "fullScopeUrl": "https://${DOMAIN}/",
  "minSdkVersion": 21,
  "orientation": "any",
  "fingerprints": [],
  "additionalTrustedOrigins": [],
  "retainedBundles": [],
  "protocolHandlers": [],
  "fileHandlers": [],
  "launchHandlerClientMode": ["focus-existing", "auto"],
  "displayOverride": ["window-controls-overlay", "fullscreen"]
}
TWAMF
echo "  twa-manifest.json written"

# Generate the Android project from the manifest.
# bubblewrap update asks for a versionName then auto-increments versionCode
# regardless of what's in twa-manifest.json — so we pipe the answer and then
# patch app/build.gradle directly to set the version we actually want.
echo "${VERSION_NAME}" | NO_UPDATE_NOTIFIER=1 bubblewrap update
sed -i "s/versionCode [0-9]*/versionCode ${VERSION_CODE}/" app/build.gradle
sed -i "s/versionName \"[^\"]*\"/versionName \"${VERSION_NAME}\"/" app/build.gradle
echo "  Android project generated: versionCode=${VERSION_CODE}, versionName=${VERSION_NAME}"

echo "=== Step 3b: Inject widget + notification-sound files ==="

# Java source directory
JAVA_DIR="app/src/main/java/$(echo "$PACKAGE" | tr '.' '/')"
mkdir -p "$JAVA_DIR"

# AppWidget provider
sed "s/PACKAGE_NAME/${PACKAGE}/g" "${WIDGET_DIR}/WadsworthWidget.java" \
    > "${JAVA_DIR}/WadsworthWidget.java"
echo "  Copied WadsworthWidget.java → ${JAVA_DIR}/"

# WBC-50 index widget
sed "s/PACKAGE_NAME/${PACKAGE}/g" "${WIDGET_DIR}/WBCWidget.java" \
    > "${JAVA_DIR}/WBCWidget.java"
echo "  Copied WBCWidget.java → ${JAVA_DIR}/"

# Chat widgets — public classes required so Android can instantiate via reflection
sed "s/PACKAGE_NAME/${PACKAGE}/g" "${WIDGET_DIR}/ChatWidgetBase.java"   > "${JAVA_DIR}/ChatWidgetBase.java"
sed "s/PACKAGE_NAME/${PACKAGE}/g" "${WIDGET_DIR}/GlobalChatWidget.java" > "${JAVA_DIR}/GlobalChatWidget.java"
sed "s/PACKAGE_NAME/${PACKAGE}/g" "${WIDGET_DIR}/TradeChatWidget.java"  > "${JAVA_DIR}/TradeChatWidget.java"
echo "  Copied ChatWidgetBase, GlobalChatWidget, TradeChatWidget → ${JAVA_DIR}/"

# Bond yields and Forex rate widgets
sed "s/PACKAGE_NAME/${PACKAGE}/g" "${WIDGET_DIR}/BondsWidget.java" > "${JAVA_DIR}/BondsWidget.java"
sed "s/PACKAGE_NAME/${PACKAGE}/g" "${WIDGET_DIR}/ForexWidget.java" > "${JAVA_DIR}/ForexWidget.java"
echo "  Copied BondsWidget, ForexWidget → ${JAVA_DIR}/"

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
cp "${WIDGET_DIR}/res/layout/widget_layout.xml"           app/src/main/res/layout/
cp "${WIDGET_DIR}/res/layout/widget_chat_layout.xml"      app/src/main/res/layout/
cp "${WIDGET_DIR}/res/layout/widget_wbc_layout.xml"       app/src/main/res/layout/
cp "${WIDGET_DIR}/res/layout/widget_bonds_layout.xml"     app/src/main/res/layout/
cp "${WIDGET_DIR}/res/layout/widget_forex_layout.xml"     app/src/main/res/layout/
cp "${WIDGET_DIR}/res/xml/wadsworth_widget_info.xml"      app/src/main/res/xml/
cp "${WIDGET_DIR}/res/xml/global_chat_widget_info.xml"    app/src/main/res/xml/
cp "${WIDGET_DIR}/res/xml/trade_chat_widget_info.xml"     app/src/main/res/xml/
cp "${WIDGET_DIR}/res/xml/wbc_widget_info.xml"            app/src/main/res/xml/
cp "${WIDGET_DIR}/res/xml/bonds_widget_info.xml"          app/src/main/res/xml/
cp "${WIDGET_DIR}/res/xml/forex_widget_info.xml"          app/src/main/res/xml/
cp "${WIDGET_DIR}/res/drawable/widget_background.xml"     app/src/main/res/drawable/
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

# Accept all Android SDK licenses by writing known hash files directly.
# This is the standard headless/CI approach — sdkmanager --licenses is interactive.
mkdir -p "${SDK_DIR}/licenses"
printf '\n8933bad161af4178b1185d1a37fbf41ea5269c55\nd56f5187479451eabf01fb78af6dfcb131a6481e\n24333f8a63b6825ea9c5514f83c2829b004d1fee' \
    > "${SDK_DIR}/licenses/android-sdk-license"
printf '\n84831b9409646a918e30573bab4c9c91346d8abd' \
    > "${SDK_DIR}/licenses/android-sdk-preview-license"
printf '\n33b6a2b64607f11b759f320ef9dff4ae5c47d97a' \
    > "${SDK_DIR}/licenses/google-gdk-license"
printf '\n859f317696f67ef3d7f30a50a5560e7834b43903' \
    > "${SDK_DIR}/licenses/android-sdk-arm-dbt-license"
echo "  Android SDK licenses written"

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
SOUND_SRC="${SCRIPT_DIR}/../static/sounds/notification.mp3"
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

# 0. Ensure INTERNET permission — Bubblewrap normally includes this, but the widget's
#    direct HttpURLConnection calls throw SecurityException if it's absent.
if grep -q "android.permission.INTERNET" "$MANIFEST"; then
    echo "  INTERNET permission already in AndroidManifest.xml — skipping"
else
    sed -i 's|<application |<uses-permission android:name="android.permission.INTERNET" />\n    <application |' "$MANIFEST"
    echo "  Added INTERNET permission to AndroidManifest.xml"
fi

# 1. Point <application> at our custom Application subclass so channels are
#    seeded with the custom notification sound on every app launch.
#    Bubblewrap generates android:name="Application" — replace it rather than
#    prepending a second android:name (duplicate attributes break XML parsing).
if grep -q "WadsworthApplication" "$MANIFEST"; then
    echo "  WadsworthApplication already in AndroidManifest.xml — skipping"
elif grep -q 'android:name="Application"' "$MANIFEST"; then
    sed -i "s|android:name=\"Application\"|android:name=\"${PACKAGE}.WadsworthApplication\"|" "$MANIFEST"
    echo "  Set android:name=WadsworthApplication on <application>"
else
    sed -i "s|<application |<application android:name=\"${PACKAGE}.WadsworthApplication\" |" "$MANIFEST"
    echo "  Set android:name=WadsworthApplication on <application>"
fi

# 2. Inject AppWidget receiver
RECEIVER_BLOCK="        <receiver android:name=\"${PACKAGE}.WadsworthWidget\" android:label=\"Balance + Alerts\" android:exported=\"true\"><intent-filter><action android:name=\"android.appwidget.action.APPWIDGET_UPDATE\"/><action android:name=\"${PACKAGE}.WIDGET_REFRESH\"/></intent-filter><meta-data android:name=\"android.appwidget.provider\" android:resource=\"@xml/wadsworth_widget_info\"/></receiver>"

if grep -q "WadsworthWidget" "$MANIFEST"; then
    echo "  WadsworthWidget already in AndroidManifest.xml — skipping"
else
    sed -i "s|</application>|${RECEIVER_BLOCK}\n    </application>|" "$MANIFEST"
    echo "  Injected WadsworthWidget receiver into AndroidManifest.xml"
fi

# 3. Inject token activity
TOKEN_ACTIVITY="        <activity android:name=\"${PACKAGE}.WadsworthTokenActivity\" android:exported=\"true\" android:theme=\"@android:style/Theme.NoDisplay\"><intent-filter><action android:name=\"android.intent.action.VIEW\"/><category android:name=\"android.intent.category.DEFAULT\"/><category android:name=\"android.intent.category.BROWSABLE\"/><data android:scheme=\"wadsworth\" android:host=\"widget-auth\"/></intent-filter></activity>"

if grep -q "WadsworthTokenActivity" "$MANIFEST"; then
    echo "  WadsworthTokenActivity already in AndroidManifest.xml — skipping"
else
    sed -i "s|</application>|${TOKEN_ACTIVITY}\n    </application>|" "$MANIFEST"
    echo "  Injected WadsworthTokenActivity into AndroidManifest.xml"
fi

# 4. Inject WBCWidget receiver
WBC_BLOCK="        <receiver android:name=\"${PACKAGE}.WBCWidget\" android:label=\"WBC-50 Index\" android:exported=\"true\"><intent-filter><action android:name=\"android.appwidget.action.APPWIDGET_UPDATE\"/><action android:name=\"${PACKAGE}.WBC_REFRESH\"/></intent-filter><meta-data android:name=\"android.appwidget.provider\" android:resource=\"@xml/wbc_widget_info\"/></receiver>"

if grep -q "WBCWidget" "$MANIFEST"; then
    echo "  WBCWidget already in AndroidManifest.xml — skipping"
else
    sed -i "s|</application>|${WBC_BLOCK}\n    </application>|" "$MANIFEST"
    echo "  Injected WBCWidget receiver into AndroidManifest.xml"
fi

# 6. Inject GlobalChatWidget receiver
GLOBAL_CHAT_BLOCK="        <receiver android:name=\"${PACKAGE}.GlobalChatWidget\" android:label=\"Global Chat\" android:exported=\"true\"><intent-filter><action android:name=\"android.appwidget.action.APPWIDGET_UPDATE\"/><action android:name=\"${PACKAGE}.GLOBAL_CHAT_REFRESH\"/></intent-filter><meta-data android:name=\"android.appwidget.provider\" android:resource=\"@xml/global_chat_widget_info\"/></receiver>"

if grep -q "GlobalChatWidget" "$MANIFEST"; then
    echo "  GlobalChatWidget already in AndroidManifest.xml — skipping"
else
    sed -i "s|</application>|${GLOBAL_CHAT_BLOCK}\n    </application>|" "$MANIFEST"
    echo "  Injected GlobalChatWidget receiver into AndroidManifest.xml"
fi

# 5. Inject TradeChatWidget receiver
TRADE_CHAT_BLOCK="        <receiver android:name=\"${PACKAGE}.TradeChatWidget\" android:label=\"Trade Chat\" android:exported=\"true\"><intent-filter><action android:name=\"android.appwidget.action.APPWIDGET_UPDATE\"/><action android:name=\"${PACKAGE}.TRADE_CHAT_REFRESH\"/></intent-filter><meta-data android:name=\"android.appwidget.provider\" android:resource=\"@xml/trade_chat_widget_info\"/></receiver>"

if grep -q "TradeChatWidget" "$MANIFEST"; then
    echo "  TradeChatWidget already in AndroidManifest.xml — skipping"
else
    sed -i "s|</application>|${TRADE_CHAT_BLOCK}\n    </application>|" "$MANIFEST"
    echo "  Injected TradeChatWidget receiver into AndroidManifest.xml"
fi

# 7. Inject BondsWidget receiver
BONDS_BLOCK="        <receiver android:name=\"${PACKAGE}.BondsWidget\" android:label=\"Bond Yields\" android:exported=\"true\"><intent-filter><action android:name=\"android.appwidget.action.APPWIDGET_UPDATE\"/><action android:name=\"${PACKAGE}.BONDS_REFRESH\"/></intent-filter><meta-data android:name=\"android.appwidget.provider\" android:resource=\"@xml/bonds_widget_info\"/></receiver>"

if grep -q "BondsWidget" "$MANIFEST"; then
    echo "  BondsWidget already in AndroidManifest.xml — skipping"
else
    sed -i "s|</application>|${BONDS_BLOCK}\n    </application>|" "$MANIFEST"
    echo "  Injected BondsWidget receiver into AndroidManifest.xml"
fi

# 8. Inject ForexWidget receiver
FOREX_BLOCK="        <receiver android:name=\"${PACKAGE}.ForexWidget\" android:label=\"Forex Rates\" android:exported=\"true\"><intent-filter><action android:name=\"android.appwidget.action.APPWIDGET_UPDATE\"/><action android:name=\"${PACKAGE}.FOREX_REFRESH\"/></intent-filter><meta-data android:name=\"android.appwidget.provider\" android:resource=\"@xml/forex_widget_info\"/></receiver>"

if grep -q "ForexWidget" "$MANIFEST"; then
    echo "  ForexWidget already in AndroidManifest.xml — skipping"
else
    sed -i "s|</application>|${FOREX_BLOCK}\n    </application>|" "$MANIFEST"
    echo "  Injected ForexWidget receiver into AndroidManifest.xml"
fi

# ProGuard/R8 keep rules
PROGUARD_RULES="app/proguard-rules.pro"
if grep -q "WadsworthWidget" "$PROGUARD_RULES" 2>/dev/null; then
    echo "  ProGuard rules already present — skipping"
else
    cat >> "$PROGUARD_RULES" << 'EOF'

# Keep widget + token classes (referenced by manifest, not by Java)
-keep class PACKAGE_PLACEHOLDER.WadsworthWidget { *; }
-keep class PACKAGE_PLACEHOLDER.WadsworthApplication { *; }
-keep class PACKAGE_PLACEHOLDER.WadsworthTokenActivity { *; }
-keep class PACKAGE_PLACEHOLDER.WBCWidget { *; }
-keep class PACKAGE_PLACEHOLDER.ChatWidgetBase { *; }
-keep class PACKAGE_PLACEHOLDER.GlobalChatWidget { *; }
-keep class PACKAGE_PLACEHOLDER.TradeChatWidget { *; }
-keep class PACKAGE_PLACEHOLDER.BondsWidget { *; }
-keep class PACKAGE_PLACEHOLDER.ForexWidget { *; }
EOF
    sed -i "s/PACKAGE_PLACEHOLDER/${PACKAGE}/g" "$PROGUARD_RULES"
    echo "  Added ProGuard keep rules"
fi

echo "=== Step 4: Build and sign APK and AAB with Gradle ==="
# Pass signing credentials as project properties — no build.gradle modification needed.
# bubblewrap build always prompts interactively for passwords and ignores flags.
chmod +x gradlew

# Run both assembleRelease (APK) and bundleRelease (AAB)
./gradlew assembleRelease bundleRelease \
    -Pandroid.injected.signing.store.file="${KEYSTORE_ABS}" \
    -Pandroid.injected.signing.store.password="${KEY_PASS}" \
    -Pandroid.injected.signing.key.alias=android \
    -Pandroid.injected.signing.key.password="${KEY_PASS}"

# Copy the generated APK
cp app/build/outputs/apk/release/app-release.apk "../wadsworth-signed.apk"

# Copy the generated AAB
cp app/build/outputs/bundle/release/app-release.aab "../wadsworth-signed.aab"
cd ..

echo ""
echo "✅  Done!  APK is at: $(pwd)/wadsworth-signed.apk"
echo "✅  Done!  AAB is at: $(pwd)/wadsworth-signed.aab"
echo "    Install APK on device:  adb install wadsworth-signed.apk"
echo "    Upload AAB to Google Play Console: wadsworth-signed.aab"
echo ""
echo "=== Signing certificate SHA-256 (for assetlinks.json) ==="
keytool -list -v -keystore "${KEYSTORE_ABS}" -alias android \
    -storepass "${KEY_PASS}" 2>/dev/null | grep "SHA256:"
echo ""
echo "    Verify live:  curl https://${DOMAIN}/.well-known/assetlinks.json"
