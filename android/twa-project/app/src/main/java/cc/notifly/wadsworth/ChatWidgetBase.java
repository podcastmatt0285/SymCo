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

import org.json.JSONArray;
import org.json.JSONObject;

import java.io.BufferedReader;
import java.io.InputStreamReader;
import java.net.HttpURLConnection;
import java.net.URL;

/** Shared logic for the Global Chat and Trade Chat home-screen widgets. */
public abstract class ChatWidgetBase extends AppWidgetProvider {

    static final String BASE_URL = "https://wadsworth.notifly.cc";

    public abstract String getRoomId();
    public abstract String getActionRefresh();
    public abstract String getRoomLabel();

    static String getDeviceHash(Context ctx) {
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

    static int viewId(Context ctx, String name) {
        return ctx.getResources().getIdentifier(name, "id", ctx.getPackageName());
    }

    static int layoutId(Context ctx) {
        return ctx.getResources().getIdentifier("widget_chat_layout", "layout", ctx.getPackageName());
    }

    @Override
    public void onUpdate(Context ctx, AppWidgetManager mgr, int[] widgetIds) {
        for (int id : widgetIds) updateWidget(ctx, mgr, id, this);
    }

    @Override
    public void onReceive(Context ctx, Intent intent) {
        super.onReceive(ctx, intent);
        if (getActionRefresh().equals(intent.getAction())) {
            AppWidgetManager mgr = AppWidgetManager.getInstance(ctx);
            int[] ids = mgr.getAppWidgetIds(new ComponentName(ctx, getClass()));
            for (int id : ids) updateWidget(ctx, mgr, id, this);
        }
    }

    static void updateWidget(Context ctx, AppWidgetManager mgr, int widgetId, ChatWidgetBase w) {
        RemoteViews views = new RemoteViews(ctx.getPackageName(), layoutId(ctx));

        views.setTextViewText(viewId(ctx, "widget_chat_title"), w.getRoomLabel());

        // Tap title → open chat page in the app
        int piFlags = Build.VERSION.SDK_INT >= 23 ? PendingIntent.FLAG_IMMUTABLE : 0;
        Intent launch = new Intent(Intent.ACTION_VIEW, Uri.parse(BASE_URL + "/chat"));
        launch.setPackage(ctx.getPackageName());
        launch.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK);
        views.setOnClickPendingIntent(viewId(ctx, "widget_chat_title"),
                PendingIntent.getActivity(ctx, (w.getRoomId() + "_open").hashCode(), launch, piFlags));

        // Refresh button → broadcast to this provider
        Intent refresh = new Intent(w.getActionRefresh());
        refresh.setComponent(new ComponentName(ctx, w.getClass()));
        int rfFlags = Build.VERSION.SDK_INT >= 23
                ? PendingIntent.FLAG_IMMUTABLE | PendingIntent.FLAG_UPDATE_CURRENT
                : PendingIntent.FLAG_UPDATE_CURRENT;
        views.setOnClickPendingIntent(viewId(ctx, "widget_chat_refresh"),
                PendingIntent.getBroadcast(ctx, (w.getRoomId() + "_refresh").hashCode(), refresh, rfFlags));

        // Clear message rows
        for (int i = 1; i <= 25; i++)
            views.setTextViewText(viewId(ctx, "widget_chat_msg" + i), "");
        mgr.updateAppWidget(widgetId, views);

        final String deviceHash = getDeviceHash(ctx);
        final String room = w.getRoomId();

        new Thread(() -> {
            try {
                String dataUrl = BASE_URL + "/api/widget/chat?room=" + room;
                if (deviceHash != null)
                    dataUrl += "&device_id=" + Uri.encode(deviceHash);

                URL url = new URL(dataUrl);
                HttpURLConnection conn = (HttpURLConnection) url.openConnection();
                conn.setRequestMethod("GET");
                conn.setConnectTimeout(8000);
                conn.setReadTimeout(8000);
                conn.setRequestProperty("Accept", "application/json");
                conn.connect();

                if (conn.getResponseCode() != 200) {
                    views.setTextViewText(viewId(ctx, "widget_chat_msg1"), "Open app to log in");
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
                JSONArray msgs = data.optJSONArray("messages");

                for (int i = 1; i <= 25; i++) {
                    if (msgs != null && (i - 1) < msgs.length()) {
                        JSONObject m = msgs.getJSONObject(i - 1);
                        String sender = m.optString("sender", "");
                        String text   = m.optString("text", "");
                        if (sender.length() > 12)
                            sender = sender.substring(0, 11) + "\u2026";
                        views.setTextViewText(viewId(ctx, "widget_chat_msg" + i),
                                sender + ": " + text);
                    } else {
                        views.setTextViewText(viewId(ctx, "widget_chat_msg" + i), "");
                    }
                }
                mgr.updateAppWidget(widgetId, views);

            } catch (Exception e) {
                views.setTextViewText(viewId(ctx, "widget_chat_msg1"), "Tap \u21bb to refresh");
                mgr.updateAppWidget(widgetId, views);
            }
        }).start();
    }
}
