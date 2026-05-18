package PACKAGE_NAME;

import android.app.PendingIntent;
import android.appwidget.AppWidgetManager;
import android.appwidget.AppWidgetProvider;
import android.content.ComponentName;
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

public class ForexWidget extends AppWidgetProvider {

    static final String BASE_URL       = "https://wadsworth.notifly.cc";
    static final String ACTION_REFRESH = "PACKAGE_NAME.FOREX_REFRESH";

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
        return ctx.getResources().getIdentifier("widget_forex_layout", "layout", ctx.getPackageName());
    }

    @Override
    public void onUpdate(Context ctx, AppWidgetManager mgr, int[] ids) {
        for (int id : ids) updateWidget(ctx, mgr, id);
    }

    @Override
    public void onReceive(Context ctx, Intent intent) {
        super.onReceive(ctx, intent);
        if (ACTION_REFRESH.equals(intent.getAction())) {
            AppWidgetManager mgr = AppWidgetManager.getInstance(ctx);
            int[] ids = mgr.getAppWidgetIds(new ComponentName(ctx, ForexWidget.class));
            for (int id : ids) updateWidget(ctx, mgr, id);
        }
    }

    static void updateWidget(Context ctx, AppWidgetManager mgr, int widgetId) {
        RemoteViews views = new RemoteViews(ctx.getPackageName(), layoutId(ctx));

        int piFlags = Build.VERSION.SDK_INT >= 23 ? PendingIntent.FLAG_IMMUTABLE : 0;

        // Tap header → open forex page
        Intent launch = new Intent(Intent.ACTION_VIEW, Uri.parse(BASE_URL + "/reserve-banks/forex"));
        launch.setPackage(ctx.getPackageName());
        launch.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK);
        views.setOnClickPendingIntent(id(ctx, "widget_forex_title"),
                PendingIntent.getActivity(ctx, 30, launch, piFlags));

        // Refresh button
        Intent refresh = new Intent(ACTION_REFRESH);
        refresh.setComponent(new ComponentName(ctx, ForexWidget.class));
        int rfFlags = Build.VERSION.SDK_INT >= 23
                ? PendingIntent.FLAG_IMMUTABLE | PendingIntent.FLAG_UPDATE_CURRENT
                : PendingIntent.FLAG_UPDATE_CURRENT;
        views.setOnClickPendingIntent(id(ctx, "widget_forex_refresh"),
                PendingIntent.getBroadcast(ctx, 31, refresh, rfFlags));

        // Loading state
        views.setTextViewText(id(ctx, "widget_forex_title"), "\uD83D\uDCB1 Forex Rates");
        for (int i = 1; i <= 8; i++)
            views.setTextViewText(id(ctx, "widget_forex_row" + i), "");
        views.setTextViewText(id(ctx, "widget_forex_subtitle"), "vs USD  \u2022  Loading\u2026");
        mgr.updateAppWidget(widgetId, views);

        final String deviceHash = getDeviceHash(ctx);

        new Thread(() -> {
            try {
                String dataUrl = BASE_URL + "/api/widget/forex";
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
                    views.setTextViewText(id(ctx, "widget_forex_subtitle"),
                            httpCode == 401 ? "Open app to log in" : "Server error " + httpCode);
                    mgr.updateAppWidget(widgetId, views);
                    return;
                }

                BufferedReader reader = new BufferedReader(
                        new InputStreamReader(conn.getInputStream(), "UTF-8"));
                StringBuilder sb = new StringBuilder();
                String line;
                while ((line = reader.readLine()) != null) sb.append(line);
                conn.disconnect();

                JSONObject data  = new JSONObject(sb.toString());
                JSONArray  pairs = data.optJSONArray("pairs");

                String[] rowIds = {
                    "widget_forex_row1", "widget_forex_row2", "widget_forex_row3",
                    "widget_forex_row4", "widget_forex_row5", "widget_forex_row6",
                    "widget_forex_row7", "widget_forex_row8"
                };

                int shown = 0;
                for (int i = 0; i < rowIds.length; i++) {
                    if (pairs != null && i < pairs.length()) {
                        JSONObject p   = pairs.getJSONObject(i);
                        String flag    = p.optString("flag", "");
                        String code    = p.optString("code", "");
                        String units   = p.optString("units_str", "");
                        double chPct   = p.optDouble("change_pct", 0);
                        String spark   = p.optString("sparkline", "");
                        String chStr   = chPct == 0 ? "" : (chPct > 0 ? "\u2191" : "\u2193")
                                       + String.format("%.2f%%", Math.abs(chPct));
                        // Skip USD row — it's always 1:1
                        if ("USD".equals(code)) {
                            views.setTextViewText(id(ctx, rowIds[i]), "");
                            continue;
                        }
                        String row = flag + " " + code + "  " + units
                                   + (chStr.isEmpty() ? "" : "  " + chStr)
                                   + (spark.isEmpty() ? "" : "  " + spark);
                        views.setTextViewText(id(ctx, rowIds[i]), row);
                        views.setTextColor(id(ctx, rowIds[i]),
                                chPct > 0 ? 0xFF22C55E : (chPct < 0 ? 0xFFEF4444 : 0xFF94A3B8));
                        shown++;
                    } else {
                        views.setTextViewText(id(ctx, rowIds[i]), "");
                    }
                }

                views.setTextViewText(id(ctx, "widget_forex_subtitle"),
                        "vs USD  \u2022  " + shown + " currencies");
                mgr.updateAppWidget(widgetId, views);

            } catch (Exception e) {
                String em = e.getClass().getSimpleName();
                if (e.getMessage() != null)
                    em += ": " + e.getMessage().substring(0, Math.min(40, e.getMessage().length()));
                views.setTextViewText(id(ctx, "widget_forex_subtitle"), em);
                mgr.updateAppWidget(widgetId, views);
            }
        }).start();
    }
}
