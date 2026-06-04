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
<<<<<<< Updated upstream
<<<<<<< Updated upstream
VERSION_CODE=26
VERSION_NAME="2.04"
=======
VERSION_CODE=30
VERSION_NAME="3.00"
>>>>>>> Stashed changes
=======
VERSION_CODE=30
VERSION_NAME="3.00"
>>>>>>> Stashed changes

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

# Preflight: the directly-distributed APK is signed with THIS keystore, so its
# fingerprint MUST be listed in the assetlinks.json the server serves or the TWA
# fails Digital Asset Links verification (browser URL bar, broken push delegation
# and login-cred sharing). Catch a mismatch here instead of discovering it on the
# device. (Play-delivered installs additionally need Google's app-signing key,
# which we can't read locally — that one is verified in the Play Console.)
ASSETLINKS_SRC="${SCRIPT_DIR}/../app.py"
if [ -f "${ASSETLINKS_SRC}" ]; then
    if grep -q "${FINGERPRINT}" "${ASSETLINKS_SRC}"; then
        echo "  ✓ Keystore fingerprint found in app.py assetlinks — TWA will verify for sideloaded APK."
    else
        echo ""
        echo "  ⚠️  WARNING: this keystore's SHA-256 is NOT in app.py's assetlinks.json."
        echo "      The directly-installed APK will fail TWA verification (URL bar shows,"
        echo "      push delegation/login-creds break). Add this line to the"
        echo "      sha256_cert_fingerprints array in app.py and redeploy the server:"
        echo "          \"${FINGERPRINT}\","
        echo ""
    fi
else
    echo "  (could not locate app.py to verify assetlinks — skipping preflight check)"
fi

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
  "features": { "playBilling": { "enabled": true } },
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

# Pre-configure bubblewrap so it never asks JDK/SDK prompts.
# Both paths must be non-empty in ~/.bubblewrap/config.json before running bubblewrap.
_JDK_PATH="${JAVA_HOME:-}"
[ -z "$_JDK_PATH" ] && _JDK_PATH=$(update-alternatives --list java 2>/dev/null | grep -E 'java-(17|21)' | head -1 | sed 's|/bin/java||')
[ -z "$_JDK_PATH" ] && _JDK_PATH=$(ls -d /usr/lib/jvm/java-21-openjdk* /usr/lib/jvm/java-17-openjdk* 2>/dev/null | head -1)
_SDK_PATH="${ANDROID_HOME:-$HOME/.bubblewrap/android_sdk}"
# Write config so bubblewrap skips both interactive setup prompts entirely.
mkdir -p "$HOME/.bubblewrap"
printf '{"jdkPath":"%s","androidSdkPath":"%s"}\n' "$_JDK_PATH" "$_SDK_PATH" > "$HOME/.bubblewrap/config.json"
echo "  bubblewrap config: jdk=${_JDK_PATH}, sdk=${_SDK_PATH}"

# Install Android SDK command-line tools if the SDK is not yet set up.
if [ ! -d "${_SDK_PATH}/platform-tools" ]; then
    echo "=== Installing Android SDK ==="
    mkdir -p "${_SDK_PATH}/cmdline-tools"
    _CMDTOOLS_ZIP="/tmp/cmdline-tools-latest.zip"
    if [ ! -f "$_CMDTOOLS_ZIP" ]; then
        curl -fsSL "https://dl.google.com/android/repository/commandlinetools-linux-11076708_latest.zip" \
             -o "$_CMDTOOLS_ZIP"
    fi
    unzip -q "$_CMDTOOLS_ZIP" -d "${_SDK_PATH}/cmdline-tools"
    # sdkmanager requires the directory to be named "latest"
    mv "${_SDK_PATH}/cmdline-tools/cmdline-tools" "${_SDK_PATH}/cmdline-tools/latest" 2>/dev/null || true
    export ANDROID_HOME="${_SDK_PATH}"
    export PATH="${_SDK_PATH}/cmdline-tools/latest/bin:${_SDK_PATH}/platform-tools:$PATH"
    # Accept licenses and install required components
    yes | sdkmanager --licenses > /dev/null 2>&1 || true
    sdkmanager "platform-tools" "build-tools;34.0.0" "platforms;android-34"
    echo "  Android SDK installed at ${_SDK_PATH}"
fi
export ANDROID_HOME="${_SDK_PATH}"
export PATH="${_SDK_PATH}/cmdline-tools/latest/bin:${_SDK_PATH}/platform-tools:$PATH"

# Generate the Android project from the manifest.
# bubblewrap update asks for the new versionName — pipe it as the only required input.
printf "%s\n" "${VERSION_NAME}" | NO_UPDATE_NOTIFIER=1 JAVA_HOME="${_JDK_PATH}" bubblewrap update
sed -i "s/versionCode [0-9]*/versionCode ${VERSION_CODE}/" app/build.gradle
sed -i "s/versionName \"[^\"]*\"/versionName \"${VERSION_NAME}\"/" app/build.gradle
# jcenter was shut down for new uploads in 2021 and is deprecated; use mavenCentral instead.
sed -i "s/jcenter()/mavenCentral()/g" build.gradle
echo "  Android project generated: versionCode=${VERSION_CODE}, versionName=${VERSION_NAME}"

# AGP 8+ deprecates package= in the manifest; namespace must be in build.gradle instead.
# Remove package= attribute from the generated manifest.
sed -i 's/ package="[^"]*"//' app/src/main/AndroidManifest.xml
# Ensure namespace is declared in build.gradle (bubblewrap may not add it).
if ! grep -q "namespace" app/build.gradle; then
    sed -i "s/applicationId \"${PACKAGE}.twa\"/namespace \"${PACKAGE}.twa\"\n        applicationId \"${PACKAGE}.twa\"/" app/build.gradle
fi
echo "  Removed package= from manifest; ensured namespace in build.gradle"

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
sed "s/PACKAGE_NAME/${PACKAGE}/g" "${WIDGET_DIR}/P2PWidget.java"   > "${JAVA_DIR}/P2PWidget.java"
echo "  Copied P2PWidget.java → ${JAVA_DIR}/"

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
cp "${WIDGET_DIR}/res/xml/p2p_widget_info.xml"            app/src/main/res/xml/
cp "${WIDGET_DIR}/res/layout/widget_p2p_layout.xml"       app/src/main/res/layout/
cp "${WIDGET_DIR}/res/drawable/"*.xml                     app/src/main/res/drawable/
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

# 0. Ensure INTERNET permission — always remove then re-insert so the tag is
#    guaranteed to exist as a direct child of <manifest> regardless of what
#    bubblewrap generates.  Inserting before </manifest> is reliable even when
#    <application ...> spans multiple lines (which breaks the old sed pattern).
sed -i '/<uses-permission android:name="android\.permission\.INTERNET"/d' "$MANIFEST"
sed -i 's|</manifest>|    <uses-permission android:name="android.permission.INTERNET"/>\n</manifest>|' "$MANIFEST"
echo "  Ensured INTERNET permission in AndroidManifest.xml"

# 0b. Maximize Play Store device reach. By default Android implicitly treats
#     android.hardware.touchscreen as required="true", so the Play Store hides
#     the listing from every device that reports no real touchscreen — Android TV,
#     many Chromebooks, desktop-mode / foldable devices, and budget tablets that
#     report "faketouch". Declaring these features required="false" keeps the app
#     installable on all of them. Remove-then-reinsert so it stays idempotent.
sed -i '/<uses-feature android:name="android\.hardware\.touchscreen"/d'      "$MANIFEST"
sed -i '/<uses-feature android:name="android\.hardware\.faketouch"/d'        "$MANIFEST"
sed -i '/<uses-feature android:name="android\.hardware\.screen\.portrait"/d' "$MANIFEST"
sed -i '/<uses-feature android:name="android\.hardware\.screen\.landscape"/d' "$MANIFEST"
sed -i '/<uses-feature android:name="android\.software\.leanback"/d'         "$MANIFEST"
sed -i 's|</manifest>|    <uses-feature android:name="android.hardware.touchscreen" android:required="false"/>\n    <uses-feature android:name="android.hardware.faketouch" android:required="false"/>\n    <uses-feature android:name="android.hardware.screen.portrait" android:required="false"/>\n    <uses-feature android:name="android.hardware.screen.landscape" android:required="false"/>\n    <uses-feature android:name="android.software.leanback" android:required="false"/>\n</manifest>|' "$MANIFEST"
echo "  Injected uses-feature required=false (touchscreen/faketouch/screen/leanback) for max device reach"

# 0c. Android TV support. For the app to appear in the *TV* Play Store and get a
#     home-screen tile, Google Play requires (a) a LEANBACK_LAUNCHER activity and
#     (b) an android:banner on <application>. The bubblewrap template ships
#     neither. Add the leanback category to the launcher activity's MAIN filter,
#     and point android:banner at the @drawable/tv_banner copied in from widget/.
if grep -q "LEANBACK_LAUNCHER" "$MANIFEST"; then
    echo "  LEANBACK_LAUNCHER already in AndroidManifest.xml — skipping"
else
    sed -i 's|<category android:name="android.intent.category.LAUNCHER" />|<category android:name="android.intent.category.LAUNCHER" />\n                <category android:name="android.intent.category.LEANBACK_LAUNCHER" />|' "$MANIFEST"
    echo "  Added LEANBACK_LAUNCHER category to launcher activity (Android TV)"
fi
if grep -q 'android:banner=' "$MANIFEST"; then
    echo "  android:banner already in AndroidManifest.xml — skipping"
else
    sed -i 's|<application|<application\n        android:banner="@drawable/tv_banner"|' "$MANIFEST"
    echo "  Added android:banner=@drawable/tv_banner to <application> (Android TV)"
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

# 9. Inject P2PWidget receiver
P2P_BLOCK="        <receiver android:name=\"${PACKAGE}.P2PWidget\" android:label=\"P2P Contacts\" android:exported=\"true\"><intent-filter><action android:name=\"android.appwidget.action.APPWIDGET_UPDATE\"/><action android:name=\"${PACKAGE}.P2P_PREV\"/><action android:name=\"${PACKAGE}.P2P_NEXT\"/><action android:name=\"${PACKAGE}.P2P_REFRESH\"/></intent-filter><meta-data android:name=\"android.appwidget.provider\" android:resource=\"@xml/p2p_widget_info\"/></receiver>"

if grep -q "P2PWidget" "$MANIFEST"; then
    echo "  P2PWidget already in AndroidManifest.xml — skipping"
else
    sed -i "s|</application>|${P2P_BLOCK}\n    </application>|" "$MANIFEST"
    echo "  Injected P2PWidget receiver into AndroidManifest.xml"
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
-keep class PACKAGE_PLACEHOLDER.P2PWidget { *; }
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

echo ""
echo "=== Step 5: Post-build verification — confirm native features are bundled ==="
# Inspect the merged manifest + packaged APK so a silently-dropped receiver,
# permission, or asset fails the build loudly instead of shipping broken.
MERGED=$(find app/build/intermediates -name AndroidManifest.xml -path "*merged*release*" 2>/dev/null | head -1)
VERIFY_FAIL=0
check() {
    if grep -q "$1" "$MERGED" 2>/dev/null; then
        echo "  ✓ $2"
    else
        echo "  ✗ MISSING: $2"; VERIFY_FAIL=1
    fi
}
if [ -n "$MERGED" ] && [ -f "$MERGED" ]; then
    check "LEANBACK_LAUNCHER"               "Android TV launcher (LEANBACK_LAUNCHER)"
    check "android:banner"                  "Android TV home-screen banner"
    check "android.hardware.touchscreen"    "touchscreen uses-feature (broad device reach)"
    check "POST_NOTIFICATIONS"              "Push-notification permission"
    check "DelegationService"               "Notification delegation service (Android push)"
    check "android.permission.INTERNET"     "INTERNET permission"
    for w in WadsworthWidget WBCWidget GlobalChatWidget TradeChatWidget BondsWidget ForexWidget P2PWidget; do
        check "$w"                          "Home-screen widget: $w"
    done
    check "WadsworthTokenActivity"          "Widget auth token activity"
    check "WadsworthApplication"            "Custom Application (seeds notification-sound channels)"
else
    echo "  ✗ Could not locate merged manifest to verify — check the build output."; VERIFY_FAIL=1
fi
# Notification sound must be packaged in the APK for Android push to use it.
if unzip -l "../wadsworth-signed.apk" 2>/dev/null | grep -q "res/raw/notification"; then
    echo "  ✓ Notification sound bundled (res/raw/notification.*)"
else
    echo "  ✗ MISSING: notification sound (res/raw/notification.*) in APK"; VERIFY_FAIL=1
fi
if [ "$VERIFY_FAIL" -ne 0 ]; then
    echo ""
    echo "  ⚠️  One or more expected components are missing from the build above."
    echo "      The APK/AAB were still produced — inspect before publishing."
else
    echo "  All native components present and accounted for."
fi

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
