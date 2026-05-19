package PACKAGE_NAME;

import android.app.PendingIntent;
import android.appwidget.AppWidgetManager;
import android.appwidget.AppWidgetProvider;
import android.content.ComponentName;
import android.content.Context;
import android.content.Intent;
import android.content.SharedPreferences;
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

public class P2PWidget extends AppWidgetProvider {

    static final String BASE_URL       = "https://wadsworth.notifly.cc";
    static final String ACTION_PREV    = "PACKAGE_NAME.P2P_PREV";
    static final String ACTION_NEXT    = "PACKAGE_NAME.P2P_NEXT";
    static final String ACTION_REFRESH = "PACKAGE_NAME.P2P_REFRESH";
    static final String PREFS_NAME     = "PACKAGE_NAME.p2p_widget";
    static final String KEY_INDEX      = "p2p_index";

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
        } catch (Exception e) { return null; }
    }

    private static int id(Context ctx, String name) {
        return ctx.getResources().getIdentifier(name, "id", ctx.getPackageName());
    }

    private static int layoutId(Context ctx) {
        return ctx.getResources().getIdentifier("widget_p2p_layout", "layout", ctx.getPackageName());
    }

    @Override
    public void onUpdate(Context ctx, AppWidgetManager mgr, int[] ids) {
        for (int id : ids) updateWidget(ctx, mgr, id);
    }

    @Override
    public void onReceive(Context ctx, Intent intent) {
        super.onReceive(ctx, intent);
        String action = intent.getAction();
        if (ACTION_PREV.equals(action) || ACTION_NEXT.equals(action)
                || ACTION_REFRESH.equals(action)) {
            SharedPreferences prefs = ctx.getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE);
            if (ACTION_PREV.equals(action)) {
                int cur = prefs.getInt(KEY_INDEX, 0);
                prefs.edit().putInt(KEY_INDEX, Math.max(0, cur - 1)).apply();
            } else if (ACTION_NEXT.equals(action)) {
                int cur = prefs.getInt(KEY_INDEX, 0);
                prefs.edit().putInt(KEY_INDEX, cur + 1).apply();
            }
            AppWidgetManager mgr = AppWidgetManager.getInstance(ctx);
            int[] ids2 = mgr.getAppWidgetIds(new ComponentName(ctx, P2PWidget.class));
            for (int wid : ids2) updateWidget(ctx, mgr, wid);
        }
    }

    static void updateWidget(Context ctx, AppWidgetManager mgr, int widgetId) {
        RemoteViews views = new RemoteViews(ctx.getPackageName(), layoutId(ctx));

        int piFlags = Build.VERSION.SDK_INT >= 23 ? PendingIntent.FLAG_IMMUTABLE : 0;
        int muFlags = Build.VERSION.SDK_INT >= 23
                ? PendingIntent.FLAG_IMMUTABLE | PendingIntent.FLAG_UPDATE_CURRENT
                : PendingIntent.FLAG_UPDATE_CURRENT;

        // Tap card body → open contacts page
        Intent launch = new Intent(Intent.ACTION_VIEW, Uri.parse(BASE_URL + "/contacts"));
        launch.setPackage(ctx.getPackageName());
        launch.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK);
        views.setOnClickPendingIntent(id(ctx, "widget_p2p_name"),
                PendingIntent.getActivity(ctx, 40, launch, piFlags));
        views.setOnClickPendingIntent(id(ctx, "widget_p2p_avatar"),
                PendingIntent.getActivity(ctx, 41, launch, piFlags));

        // Prev button
        Intent prevI = new Intent(ACTION_PREV);
        prevI.setComponent(new ComponentName(ctx, P2PWidget.class));
        views.setOnClickPendingIntent(id(ctx, "widget_p2p_prev"),
                PendingIntent.getBroadcast(ctx, 42, prevI, muFlags));

        // Next button
        Intent nextI = new Intent(ACTION_NEXT);
        nextI.setComponent(new ComponentName(ctx, P2PWidget.class));
        views.setOnClickPendingIntent(id(ctx, "widget_p2p_next"),
                PendingIntent.getBroadcast(ctx, 43, nextI, muFlags));

        views.setTextViewText(id(ctx, "widget_p2p_name"), "Loading…");
        views.setTextViewText(id(ctx, "widget_p2p_page"), "");
        views.setTextViewText(id(ctx, "widget_p2p_avatar"), "?");
        views.setTextViewText(id(ctx, "widget_p2p_level"), "");
        views.setTextViewText(id(ctx, "widget_p2p_networth"), "");
        views.setTextViewText(id(ctx, "widget_p2p_cash"), "");
        views.setTextViewText(id(ctx, "widget_p2p_biz"), "");
        views.setTextViewText(id(ctx, "widget_p2p_contracts"), "");
        mgr.updateAppWidget(widgetId, views);

        final String deviceHash = getDeviceHash(ctx);
        final SharedPreferences prefs = ctx.getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE);
        final int requestedIndex = prefs.getInt(KEY_INDEX, 0);

        new Thread(() -> {
            try {
                String dataUrl = BASE_URL + "/api/widget/p2p-contacts";
                if (deviceHash != null)
                    dataUrl += "?device_id=" + Uri.encode(deviceHash);

                URL url = new URL(dataUrl);
                HttpURLConnection conn = (HttpURLConnection) url.openConnection();
                conn.setRequestMethod("GET");
                conn.setConnectTimeout(10000);
                conn.setReadTimeout(10000);
                conn.setRequestProperty("Accept", "application/json");
                conn.setRequestProperty("User-Agent",
                        "Mozilla/5.0 (Linux; Android 10) Wadsworth/1.0");
                conn.connect();

                int httpCode = conn.getResponseCode();
                if (httpCode != 200) {
                    views.setTextViewText(id(ctx, "widget_p2p_name"),
                            httpCode == 401 ? "Open app to log in" : "Server error " + httpCode);
                    views.setTextViewText(id(ctx, "widget_p2p_page"), "");
                    mgr.updateAppWidget(widgetId, views);
                    return;
                }

                BufferedReader reader = new BufferedReader(
                        new InputStreamReader(conn.getInputStream(), "UTF-8"));
                StringBuilder sb = new StringBuilder();
                String line;
                while ((line = reader.readLine()) != null) sb.append(line);
                conn.disconnect();

                JSONObject data     = new JSONObject(sb.toString());
                JSONArray  contacts = data.optJSONArray("contacts");
                int        total    = contacts != null ? contacts.length() : 0;

                if (total == 0) {
                    views.setTextViewText(id(ctx, "widget_p2p_name"), "No contacts yet");
                    views.setTextViewText(id(ctx, "widget_p2p_page"), "0 / 0");
                    views.setTextViewText(id(ctx, "widget_p2p_avatar"), "?");
                    mgr.updateAppWidget(widgetId, views);
                    return;
                }

                // Clamp index (may be out of range after contacts are removed)
                int idx = Math.min(requestedIndex, total - 1);
                if (idx != requestedIndex)
                    prefs.edit().putInt(KEY_INDEX, idx).apply();

                JSONObject c = contacts.getJSONObject(idx);
                String name      = c.optString("name", "Unknown");
                String initials  = name.length() > 0 ? String.valueOf(name.charAt(0)).toUpperCase() : "?";
                String level     = c.optString("level_label", "");
                String netWorth  = c.optString("net_worth", "");
                String cash      = c.optString("cash", "");
                String biz       = c.optString("biz_summary", "");
                String contracts = c.optString("contracts", "");

                views.setTextViewText(id(ctx, "widget_p2p_avatar"), initials);
                views.setTextViewText(id(ctx, "widget_p2p_name"), name);
                views.setTextViewText(id(ctx, "widget_p2p_page"), (idx + 1) + " / " + total);
                views.setTextViewText(id(ctx, "widget_p2p_level"), level);
                views.setTextViewText(id(ctx, "widget_p2p_networth"),
                        netWorth.isEmpty() ? "" : "💰 Net worth: " + netWorth);
                views.setTextViewText(id(ctx, "widget_p2p_cash"),
                        cash.isEmpty() ? "" : "💵 Cash:      " + cash);
                views.setTextViewText(id(ctx, "widget_p2p_biz"),
                        biz.isEmpty() ? "" : "🏭 " + biz);
                views.setTextViewText(id(ctx, "widget_p2p_contracts"),
                        contracts.isEmpty() ? "" : "📄 " + contracts);

                mgr.updateAppWidget(widgetId, views);

            } catch (Exception e) {
                String em = e.getClass().getSimpleName();
                if (e.getMessage() != null)
                    em += ": " + e.getMessage().substring(0, Math.min(40, e.getMessage().length()));
                views.setTextViewText(id(ctx, "widget_p2p_name"), em);
                views.setTextViewText(id(ctx, "widget_p2p_page"), "");
                mgr.updateAppWidget(widgetId, views);
            }
        }).start();
    }
}
