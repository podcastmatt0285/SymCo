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

public class WBCWidget extends AppWidgetProvider {

    static final String BASE_URL       = "https://wadsworth.notifly.cc";
    static final String ACTION_REFRESH = "PACKAGE_NAME.WBC_REFRESH";

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
        return ctx.getResources().getIdentifier("widget_wbc_layout", "layout", ctx.getPackageName());
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
            int[] ids = mgr.getAppWidgetIds(new ComponentName(ctx, WBCWidget.class));
            for (int id : ids) updateWidget(ctx, mgr, id);
        }
    }

    static void updateWidget(Context ctx, AppWidgetManager mgr, int widgetId) {
        RemoteViews views = new RemoteViews(ctx.getPackageName(), layoutId(ctx));

        // Tap value → open markets page
        int piFlags = Build.VERSION.SDK_INT >= 23 ? PendingIntent.FLAG_IMMUTABLE : 0;
        Intent launch = new Intent(Intent.ACTION_VIEW, Uri.parse(BASE_URL + "/market"));
        launch.setPackage(ctx.getPackageName());
        launch.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK);
        views.setOnClickPendingIntent(id(ctx, "widget_wbc_value"),
                PendingIntent.getActivity(ctx, 10, launch, piFlags));

        // Refresh button → broadcast
        Intent refresh = new Intent(ACTION_REFRESH);
        refresh.setComponent(new ComponentName(ctx, WBCWidget.class));
        int rfFlags = Build.VERSION.SDK_INT >= 23
                ? PendingIntent.FLAG_IMMUTABLE | PendingIntent.FLAG_UPDATE_CURRENT
                : PendingIntent.FLAG_UPDATE_CURRENT;
        views.setOnClickPendingIntent(id(ctx, "widget_wbc_refresh"),
                PendingIntent.getBroadcast(ctx, 11, refresh, rfFlags));

        views.setTextViewText(id(ctx, "widget_wbc_value"), "Loading\u2026");
        views.setTextViewText(id(ctx, "widget_wbc_change"), "");
        views.setTextViewText(id(ctx, "widget_wbc_sparkline"), "");
        for (int i = 1; i <= 5; i++)
            views.setTextViewText(id(ctx, "widget_wbc_co" + i), "");
        mgr.updateAppWidget(widgetId, views);

        final String deviceHash = getDeviceHash(ctx);

        new Thread(() -> {
            try {
                String dataUrl = BASE_URL + "/api/widget/wbc50";
                if (deviceHash != null)
                    dataUrl += "?device_id=" + Uri.encode(deviceHash);

                URL url = new URL(dataUrl);
                HttpURLConnection conn = (HttpURLConnection) url.openConnection();
                conn.setRequestMethod("GET");
                conn.setConnectTimeout(8000);
                conn.setReadTimeout(8000);
                conn.setRequestProperty("Accept", "application/json");
                conn.connect();

                if (conn.getResponseCode() != 200) {
                    views.setTextViewText(id(ctx, "widget_wbc_value"), "Open app to log in");
                    mgr.updateAppWidget(widgetId, views);
                    return;
                }

                BufferedReader reader = new BufferedReader(
                        new InputStreamReader(conn.getInputStream()));
                StringBuilder sb = new StringBuilder();
                String line;
                while ((line = reader.readLine()) != null) sb.append(line);
                conn.disconnect();

                JSONObject data = new JSONObject(sb.toString());

                views.setTextViewText(id(ctx, "widget_wbc_value"),
                        data.optString("value", "\u2014"));

                String changePct = data.optString("change_pct", "");
                boolean up = data.optBoolean("up", true);
                views.setTextViewText(id(ctx, "widget_wbc_change"), changePct);
                views.setTextColor(id(ctx, "widget_wbc_change"),
                        up ? 0xFF22C55E : 0xFFEF4444);  // green or red

                views.setTextViewText(id(ctx, "widget_wbc_sparkline"),
                        data.optString("sparkline", ""));

                JSONArray top5 = data.optJSONArray("top5");
                for (int i = 1; i <= 5; i++) {
                    if (top5 != null && (i - 1) < top5.length()) {
                        JSONObject co = top5.getJSONObject(i - 1);
                        String name  = co.optString("name", "");
                        String price = co.optString("price", "");
                        if (name.length() > 20) name = name.substring(0, 19) + "\u2026";
                        views.setTextViewText(id(ctx, "widget_wbc_co" + i), name + "  " + price);
                    } else {
                        views.setTextViewText(id(ctx, "widget_wbc_co" + i), "");
                    }
                }

                mgr.updateAppWidget(widgetId, views);

            } catch (Exception e) {
                views.setTextViewText(id(ctx, "widget_wbc_value"), "Tap \u21bb to refresh");
                mgr.updateAppWidget(widgetId, views);
            }
        }).start();
    }
}
