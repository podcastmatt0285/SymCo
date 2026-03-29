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

public class WadsworthWidget extends AppWidgetProvider {

    static final String BASE_URL    = "https://wadsworth.notifly.cc";
    static final String WIDGET_DATA = BASE_URL + "/api/widget/data";
    static final String ACTION_REFRESH = "PACKAGE_NAME.WIDGET_REFRESH";

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

    @Override
    public void onUpdate(Context ctx, AppWidgetManager mgr, int[] widgetIds) {
        for (int id : widgetIds) updateWidget(ctx, mgr, id);
    }

    /** Refresh button tap triggers this broadcast. */
    @Override
    public void onReceive(Context ctx, Intent intent) {
        super.onReceive(ctx, intent);
        if (ACTION_REFRESH.equals(intent.getAction())) {
            AppWidgetManager mgr = AppWidgetManager.getInstance(ctx);
            int[] ids = mgr.getAppWidgetIds(new ComponentName(ctx, WadsworthWidget.class));
            for (int id : ids) updateWidget(ctx, mgr, id);
        }
    }

    private static int layoutId(Context ctx) {
        return ctx.getResources().getIdentifier("widget_layout", "layout", ctx.getPackageName());
    }

    private static int id(Context ctx, String name) {
        return ctx.getResources().getIdentifier(name, "id", ctx.getPackageName());
    }

    static void updateWidget(Context ctx, AppWidgetManager mgr, int widgetId) {
        RemoteViews views = new RemoteViews(ctx.getPackageName(), layoutId(ctx));

        // Tap body → open the app
        Intent launch = new Intent(Intent.ACTION_VIEW, Uri.parse(BASE_URL));
        launch.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK);
        int piFlags = Build.VERSION.SDK_INT >= 23 ? PendingIntent.FLAG_IMMUTABLE : 0;
        PendingIntent openApp = PendingIntent.getActivity(ctx, 0, launch, piFlags);
        views.setOnClickPendingIntent(id(ctx, "widget_root"), openApp);

        // Refresh button → broadcast back to this provider
        Intent refresh = new Intent(ACTION_REFRESH);
        refresh.setComponent(new ComponentName(ctx, WadsworthWidget.class));
        int refreshFlags = Build.VERSION.SDK_INT >= 23
                ? PendingIntent.FLAG_IMMUTABLE | PendingIntent.FLAG_UPDATE_CURRENT
                : PendingIntent.FLAG_UPDATE_CURRENT;
        PendingIntent refreshPi = PendingIntent.getBroadcast(ctx, 1, refresh, refreshFlags);
        views.setOnClickPendingIntent(id(ctx, "widget_refresh"), refreshPi);

        // Loading state
        views.setTextViewText(id(ctx, "widget_balance"), "Loading\u2026");
        views.setTextViewText(id(ctx, "widget_notif1"),  "");
        views.setTextViewText(id(ctx, "widget_notif2"),  "");
        views.setTextViewText(id(ctx, "widget_notif3"),  "");
        views.setTextViewText(id(ctx, "widget_tickers"), "");
        mgr.updateAppWidget(widgetId, views);

        final String deviceHash = getDeviceHash(ctx);

        new Thread(() -> {
            try {
                String dataUrl = WIDGET_DATA;
                if (deviceHash != null)
                    dataUrl = WIDGET_DATA + "?device_id=" + Uri.encode(deviceHash);

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

                BufferedReader reader = new BufferedReader(
                        new InputStreamReader(conn.getInputStream()));
                StringBuilder sb = new StringBuilder();
                String line;
                while ((line = reader.readLine()) != null) sb.append(line);
                conn.disconnect();

                JSONObject data = new JSONObject(sb.toString());

                views.setTextViewText(id(ctx, "widget_balance"),
                        data.optString("balance", "\u2014"));

                // Notifications — show 3 most recent
                JSONArray notifs = data.optJSONArray("notifications");
                String[] notifIds = {"widget_notif1", "widget_notif2", "widget_notif3"};
                for (int i = 0; i < notifIds.length; i++) {
                    if (notifs != null && i < notifs.length()) {
                        JSONObject n = notifs.getJSONObject(i);
                        String text   = n.optString("text", "");
                        String amount = n.optString("amount", "");
                        String time   = n.optString("time", "");
                        String line2  = text + (amount.isEmpty() ? "" : "  " + amount)
                                      + (time.isEmpty() ? "" : "  " + time);
                        views.setTextViewText(id(ctx, notifIds[i]), line2);
                    } else {
                        views.setTextViewText(id(ctx, notifIds[i]), "");
                    }
                }

                // Market tickers — compact single line
                JSONArray tickers = data.optJSONArray("tickers");
                if (tickers != null && tickers.length() > 0) {
                    StringBuilder ticker = new StringBuilder();
                    int max = Math.min(tickers.length(), 12);
                    for (int i = 0; i < max; i++) {
                        JSONObject t = tickers.getJSONObject(i);
                        ticker.append(t.optString("label", ""))
                              .append(" ").append(t.optString("value", ""));
                        String change = t.optString("change", "");
                        if (!change.isEmpty()) ticker.append(" ").append(change);
                        if (i < max - 1) ticker.append("  \u00b7  ");
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
        views.setTextViewText(id(ctx, "widget_notif1"),  "");
        views.setTextViewText(id(ctx, "widget_notif2"),  "");
        views.setTextViewText(id(ctx, "widget_notif3"),  "");
        views.setTextViewText(id(ctx, "widget_tickers"), "");
    }
}
