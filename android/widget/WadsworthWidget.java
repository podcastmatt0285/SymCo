package PACKAGE_NAME;

import android.app.PendingIntent;
import android.appwidget.AppWidgetManager;
import android.appwidget.AppWidgetProvider;
import android.content.Context;
import android.content.Intent;
import android.net.Uri;
import android.os.Build;
import android.provider.Settings;
import android.widget.RemoteViews;
import java.security.MessageDigest;

import org.json.JSONArray;
import org.json.JSONObject;

import java.io.BufferedReader;
import java.io.InputStreamReader;
import java.net.HttpURLConnection;
import java.net.URL;

/**
 * Wadsworth home-screen widget.
 *
 * Shows the player's cash balance, most-recent alert, and a rolling
 * market ticker (indices → stocks → bonds → memecoins).
 *
 * Authentication piggy-backs on the TWA WebView cookie store: Chrome
 * shares cookies with the host app via CookieManager, so the session_token
 * cookie is available as long as the user is logged in inside the app.
 *
 * All resource IDs are resolved at runtime via getIdentifier() so this
 * file compiles regardless of the AGP namespace configuration.
 */
public class WadsworthWidget extends AppWidgetProvider {

    static final String BASE_URL    = "https://wadsworth.notifly.cc";
    static final String WIDGET_DATA = BASE_URL + "/api/widget/data";

    /** Compute SHA-256(ANDROID_ID + salt) — same value that LauncherActivity
     *  appends to the launch URL so the server can link device → player. */
    private static String getDeviceHash(Context ctx) {
        try {
            String androidId = Settings.Secure.getString(
                    ctx.getContentResolver(), Settings.Secure.ANDROID_ID);
            if (androidId == null || androidId.isEmpty()) return null;
            MessageDigest md = MessageDigest.getInstance("SHA-256");
            byte[] hash = md.digest((androidId + "wadsworth-device-v1").getBytes("UTF-8"));
            StringBuilder sb = new StringBuilder();
            for (byte b : hash) sb.append(String.format("%02x", b));
            return sb.toString();
        } catch (Exception e) {
            return null;
        }
    }

    // ── Lifecycle ─────────────────────────────────────────────────────────────

    @Override
    public void onUpdate(Context ctx, AppWidgetManager mgr, int[] widgetIds) {
        for (int id : widgetIds) {
            updateWidget(ctx, mgr, id);
        }
    }

    // ── Resource ID helpers ───────────────────────────────────────────────────

    private static int layoutId(Context ctx) {
        return ctx.getResources().getIdentifier("widget_layout", "layout", ctx.getPackageName());
    }

    private static int id(Context ctx, String name) {
        return ctx.getResources().getIdentifier(name, "id", ctx.getPackageName());
    }

    // ── Core update logic ─────────────────────────────────────────────────────

    static void updateWidget(Context ctx, AppWidgetManager mgr, int widgetId) {
        RemoteViews views = new RemoteViews(ctx.getPackageName(), layoutId(ctx));

        // Tap anywhere → open the app
        Intent launch = new Intent(Intent.ACTION_VIEW, Uri.parse(BASE_URL));
        launch.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK);
        int flags = Build.VERSION.SDK_INT >= 23 ? PendingIntent.FLAG_IMMUTABLE : 0;
        PendingIntent pi = PendingIntent.getActivity(ctx, 0, launch, flags);
        views.setOnClickPendingIntent(id(ctx, "widget_root"), pi);

        // Show loading state immediately, then update with real data
        views.setTextViewText(id(ctx, "widget_balance"),  "Loading…");
        views.setTextViewText(id(ctx, "widget_alert"),    "");
        views.setTextViewText(id(ctx, "widget_time"),     "");
        views.setTextViewText(id(ctx, "widget_tickers"),  "");
        mgr.updateAppWidget(widgetId, views);

        final String deviceHash = getDeviceHash(ctx);

        // Fetch data on a background thread
        new Thread(() -> {
            try {
                String dataUrl = WIDGET_DATA;
                if (deviceHash != null) {
                    dataUrl = WIDGET_DATA + "?device_id=" + Uri.encode(deviceHash);
                }

                URL url = new URL(dataUrl);
                HttpURLConnection conn = (HttpURLConnection) url.openConnection();
                conn.setRequestMethod("GET");
                conn.setConnectTimeout(8000);
                conn.setReadTimeout(8000);
                conn.setRequestProperty("Accept", "application/json");
                conn.connect();

                if (conn.getResponseCode() != 200) {
                    setError(ctx, views, "Open app to log in");
                    mgr.updateAppWidget(widgetId, views);
                    return;
                }

                BufferedReader reader =
                    new BufferedReader(new InputStreamReader(conn.getInputStream()));
                StringBuilder sb = new StringBuilder();
                String line;
                while ((line = reader.readLine()) != null) sb.append(line);
                conn.disconnect();

                JSONObject data = new JSONObject(sb.toString());

                // Balance
                views.setTextViewText(id(ctx, "widget_balance"),
                    data.optString("balance", "—"));

                // Last alert
                String alert = data.optString("last_alert", "");
                String time  = data.optString("last_alert_time", "");
                views.setTextViewText(id(ctx, "widget_alert"), alert);
                views.setTextViewText(id(ctx, "widget_time"),  time);

                // Tickers — build a compact single-line string
                JSONArray tickers = data.optJSONArray("tickers");
                if (tickers != null && tickers.length() > 0) {
                    StringBuilder ticker = new StringBuilder();
                    int max = Math.min(tickers.length(), 12);
                    for (int i = 0; i < max; i++) {
                        JSONObject t = tickers.getJSONObject(i);
                        String label  = t.optString("label", "");
                        String value  = t.optString("value", "");
                        String change = t.optString("change", "");
                        ticker.append(label).append(" ").append(value);
                        if (!change.isEmpty()) ticker.append(" ").append(change);
                        if (i < max - 1) ticker.append("  ·  ");
                    }
                    views.setTextViewText(id(ctx, "widget_tickers"), ticker.toString());
                }

                mgr.updateAppWidget(widgetId, views);

            } catch (Exception e) {
                setError(ctx, views, "Tap to refresh");
                mgr.updateAppWidget(widgetId, views);
            }
        }).start();
    }

    private static void setError(Context ctx, RemoteViews views, String msg) {
        views.setTextViewText(id(ctx, "widget_balance"), msg);
        views.setTextViewText(id(ctx, "widget_alert"),   "");
        views.setTextViewText(id(ctx, "widget_time"),    "");
        views.setTextViewText(id(ctx, "widget_tickers"), "");
    }
}
