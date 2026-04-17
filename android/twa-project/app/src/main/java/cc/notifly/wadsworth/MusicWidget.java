package cc.notifly.wadsworth;

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

import org.json.JSONObject;

import java.io.BufferedReader;
import java.io.InputStreamReader;
import java.net.HttpURLConnection;
import java.net.URL;

public class MusicWidget extends AppWidgetProvider {

    static final String BASE_URL       = "https://wadsworth.notifly.cc";
    static final String ACTION_REFRESH = "cc.notifly.wadsworth.MUSIC_REFRESH";

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
        return ctx.getResources().getIdentifier("widget_music_layout", "layout", ctx.getPackageName());
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
            int[] ids = mgr.getAppWidgetIds(new ComponentName(ctx, MusicWidget.class));
            for (int id : ids) updateWidget(ctx, mgr, id);
        }
    }

    static void updateWidget(Context ctx, AppWidgetManager mgr, int widgetId) {
        RemoteViews views = new RemoteViews(ctx.getPackageName(), layoutId(ctx));

        int piFlags = Build.VERSION.SDK_INT >= 23 ? PendingIntent.FLAG_IMMUTABLE : 0;

        // Tap anywhere → open the player
        Intent launch = new Intent(Intent.ACTION_VIEW,
                Uri.parse(BASE_URL + "/settings?tab=audio"));
        launch.setPackage(ctx.getPackageName());
        launch.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK);
        PendingIntent openPi = PendingIntent.getActivity(ctx, 40, launch, piFlags);
        views.setOnClickPendingIntent(id(ctx, "widget_music_play_btn"), openPi);
        views.setOnClickPendingIntent(id(ctx, "widget_music_station"), openPi);

        // Refresh button
        Intent refresh = new Intent(ACTION_REFRESH);
        refresh.setComponent(new ComponentName(ctx, MusicWidget.class));
        int rfFlags = Build.VERSION.SDK_INT >= 23
                ? PendingIntent.FLAG_IMMUTABLE | PendingIntent.FLAG_UPDATE_CURRENT
                : PendingIntent.FLAG_UPDATE_CURRENT;
        views.setOnClickPendingIntent(id(ctx, "widget_music_refresh"),
                PendingIntent.getBroadcast(ctx, 41, refresh, rfFlags));

        final String deviceHash = getDeviceHash(ctx);

        new Thread(() -> {
            try {
                String dataUrl = BASE_URL + "/api/widget/music";
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
                    views.setTextViewText(id(ctx, "widget_music_station"), "Open app to log in");
                    views.setTextViewText(id(ctx, "widget_music_slogan"), "");
                    views.setTextViewText(id(ctx, "widget_music_freq"), "");
                    views.setTextViewText(id(ctx, "widget_music_status"), "");
                    mgr.updateAppWidget(widgetId, views);
                    return;
                }

                BufferedReader reader = new BufferedReader(
                        new InputStreamReader(conn.getInputStream()));
                StringBuilder sb = new StringBuilder();
                String line;
                while ((line = reader.readLine()) != null) sb.append(line);
                conn.disconnect();

                JSONObject d = new JSONObject(sb.toString());
                views.setTextViewText(id(ctx, "widget_music_station"),
                        d.optString("station", "WCPR 104.1"));
                views.setTextViewText(id(ctx, "widget_music_slogan"),
                        d.optString("full_name", "Wadsworth Carter Public Radio"));
                views.setTextViewText(id(ctx, "widget_music_freq"),
                        d.optString("frequency", "104.1 FM"));
                views.setTextViewText(id(ctx, "widget_music_status"),
                        d.optString("status", "ON AIR"));
                views.setTextViewText(id(ctx, "widget_music_play_btn"), "\u25B6 Open Player");
                mgr.updateAppWidget(widgetId, views);

            } catch (Exception e) {
                views.setTextViewText(id(ctx, "widget_music_station"), "WCPR 104.1");
                views.setTextViewText(id(ctx, "widget_music_slogan"), "Wadsworth Carter Public Radio");
                views.setTextViewText(id(ctx, "widget_music_freq"), "104.1 FM");
                views.setTextViewText(id(ctx, "widget_music_status"), "ON AIR");
                views.setTextViewText(id(ctx, "widget_music_play_btn"), "\u25B6 Open Player");
                mgr.updateAppWidget(widgetId, views);
            }
        }).start();
    }
}
