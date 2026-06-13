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

import org.json.JSONArray;
import org.json.JSONObject;

import java.io.BufferedReader;
import java.io.InputStreamReader;
import java.net.HttpURLConnection;
import java.net.URL;
import java.security.MessageDigest;

public class MemeCoinsWidget extends AppWidgetProvider {

    static final String BASE_URL        = "https://wadsworth.notifly.cc";
    static final String ACTION_REFRESH  = "PACKAGE_NAME.MEMECOINS_REFRESH";
    static final String ACTION_NEXT     = "PACKAGE_NAME.MEMECOINS_NEXT";
    static final String ACTION_PREV     = "PACKAGE_NAME.MEMECOINS_PREV";
    static final String ACTION_SORT     = "PACKAGE_NAME.MEMECOINS_SORT";
    static final String PREFS_NAME      = "memecoins_widget_prefs";
    static final String KEY_PAGE        = "page";
    static final String KEY_SORT        = "sort";
    static final int    PER_PAGE        = 5;

    // Sort cycle: market_cap → volume → change → holders → new → market_cap ...
    static final String[] SORTS = {"market_cap", "volume", "change", "holders", "new"};
    static final String[] SORT_LABELS = {"MCap", "Vol", "Chg%", "Holders", "New"};

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
        return ctx.getResources().getIdentifier("widget_memecoins_layout", "layout", ctx.getPackageName());
    }

    private static SharedPreferences prefs(Context ctx) {
        return ctx.getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE);
    }

    @Override
    public void onUpdate(Context ctx, AppWidgetManager mgr, int[] ids) {
        for (int wid : ids) updateWidget(ctx, mgr, wid);
    }

    @Override
    public void onReceive(Context ctx, Intent intent) {
        super.onReceive(ctx, intent);
        String action = intent.getAction();
        AppWidgetManager mgr = AppWidgetManager.getInstance(ctx);
        int[] ids = mgr.getAppWidgetIds(new ComponentName(ctx, MemeCoinsWidget.class));

        SharedPreferences sp = prefs(ctx);
        int page = sp.getInt(KEY_PAGE, 1);
        String sort = sp.getString(KEY_SORT, "market_cap");
        int totalPages = sp.getInt("total_pages", 1);

        if (ACTION_NEXT.equals(action)) {
            page = (page >= totalPages) ? 1 : page + 1;
            sp.edit().putInt(KEY_PAGE, page).apply();
        } else if (ACTION_PREV.equals(action)) {
            page = (page <= 1) ? totalPages : page - 1;
            sp.edit().putInt(KEY_PAGE, page).apply();
        } else if (ACTION_SORT.equals(action)) {
            // Cycle to next sort
            int idx = 0;
            for (int i = 0; i < SORTS.length; i++) {
                if (SORTS[i].equals(sort)) { idx = i; break; }
            }
            sort = SORTS[(idx + 1) % SORTS.length];
            sp.edit().putString(KEY_SORT, sort).putInt(KEY_PAGE, 1).apply();
        }

        if (ACTION_NEXT.equals(action) || ACTION_PREV.equals(action)
                || ACTION_SORT.equals(action) || ACTION_REFRESH.equals(action)) {
            for (int wid : ids) updateWidget(ctx, mgr, wid);
        }
    }

    static void updateWidget(Context ctx, AppWidgetManager mgr, int widgetId) {
        RemoteViews views = new RemoteViews(ctx.getPackageName(), layoutId(ctx));
        int piFlags = Build.VERSION.SDK_INT >= 23 ? PendingIntent.FLAG_IMMUTABLE : 0;
        int piUpdate = Build.VERSION.SDK_INT >= 23
                ? PendingIntent.FLAG_IMMUTABLE | PendingIntent.FLAG_UPDATE_CURRENT
                : PendingIntent.FLAG_UPDATE_CURRENT;

        SharedPreferences sp = prefs(ctx);
        int page = sp.getInt(KEY_PAGE, 1);
        String sort = sp.getString(KEY_SORT, "market_cap");

        // Tap title → open memecoins page
        Intent launch = new Intent(Intent.ACTION_VIEW, Uri.parse(BASE_URL + "/memecoins"));
        launch.setPackage(ctx.getPackageName());
        launch.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK);
        views.setOnClickPendingIntent(id(ctx, "widget_mc_title"),
                PendingIntent.getActivity(ctx, 50, launch, piFlags));

        // Refresh
        Intent refresh = new Intent(ACTION_REFRESH);
        refresh.setComponent(new ComponentName(ctx, MemeCoinsWidget.class));
        views.setOnClickPendingIntent(id(ctx, "widget_mc_refresh"),
                PendingIntent.getBroadcast(ctx, 51, refresh, piUpdate));

        // Previous page
        Intent prev = new Intent(ACTION_PREV);
        prev.setComponent(new ComponentName(ctx, MemeCoinsWidget.class));
        views.setOnClickPendingIntent(id(ctx, "widget_mc_prev"),
                PendingIntent.getBroadcast(ctx, 52, prev, piUpdate));

        // Next page
        Intent next = new Intent(ACTION_NEXT);
        next.setComponent(new ComponentName(ctx, MemeCoinsWidget.class));
        views.setOnClickPendingIntent(id(ctx, "widget_mc_next"),
                PendingIntent.getBroadcast(ctx, 53, next, piUpdate));

        // Sort cycle
        Intent sortIntent = new Intent(ACTION_SORT);
        sortIntent.setComponent(new ComponentName(ctx, MemeCoinsWidget.class));
        views.setOnClickPendingIntent(id(ctx, "widget_mc_sort"),
                PendingIntent.getBroadcast(ctx, 54, sortIntent, piUpdate));

        // Show sort label
        String sortLabel = "MCap";
        for (int i = 0; i < SORTS.length; i++) {
            if (SORTS[i].equals(sort)) { sortLabel = SORT_LABELS[i]; break; }
        }
        views.setTextViewText(id(ctx, "widget_mc_sort"), "🔄 " + sortLabel);

        // Loading state
        views.setTextViewText(id(ctx, "widget_mc_title"), "📈 Meme Coins");
        views.setTextViewText(id(ctx, "widget_mc_pager"), "p." + page + " • Loading…");
        for (int i = 1; i <= PER_PAGE; i++) {
            views.setTextViewText(id(ctx, "widget_mc_row" + i + "_name"), "");
            views.setTextViewText(id(ctx, "widget_mc_row" + i + "_price"), "");
            views.setTextViewText(id(ctx, "widget_mc_row" + i + "_chg"), "");
            views.setTextViewText(id(ctx, "widget_mc_row" + i + "_extra"), "");
        }
        mgr.updateAppWidget(widgetId, views);

        final String deviceHash = getDeviceHash(ctx);
        final int finalPage = page;
        final String finalSort = sort;

        new Thread(() -> {
            HttpURLConnection conn = null;
            BufferedReader reader = null;
            try {
                String dataUrl = BASE_URL + "/api/widget/memecoins"
                        + "?page=" + finalPage
                        + "&per_page=" + PER_PAGE
                        + "&sort=" + Uri.encode(finalSort);
                if (deviceHash != null) dataUrl += "&device_id=" + Uri.encode(deviceHash);

                URL url = new URL(dataUrl);
                conn = (HttpURLConnection) url.openConnection();
                conn.setRequestMethod("GET");
                conn.setConnectTimeout(12000);
                conn.setReadTimeout(12000);
                conn.setRequestProperty("Accept", "application/json");
                conn.setRequestProperty("User-Agent",
                        "Mozilla/5.0 (Linux; Android " + Build.VERSION.RELEASE + ") Wadsworth/1.0");
                conn.setRequestProperty("Connection", "close");

                int httpCode = conn.getResponseCode();
                if (httpCode != 200) {
                    String msg = httpCode == 401 ? "Open app to log in" : "Error " + httpCode;
                    views.setTextViewText(id(ctx, "widget_mc_pager"), msg);
                    mgr.updateAppWidget(widgetId, views);
                    return;
                }

                reader = new BufferedReader(
                        new InputStreamReader(conn.getInputStream(), "UTF-8"));
                StringBuilder sb = new StringBuilder();
                String line;
                while ((line = reader.readLine()) != null) sb.append(line);

                JSONObject data = new JSONObject(sb.toString());
                JSONArray coins = data.optJSONArray("coins");
                int total = data.optInt("total", 0);
                int totalPages = data.optInt("total_pages", 1);
                int curPage = data.optInt("page", finalPage);

                // Persist total_pages for prev/next bounds
                prefs(ctx).edit().putInt("total_pages", totalPages).apply();

                views.setTextViewText(id(ctx, "widget_mc_pager"),
                        "p." + curPage + "/" + totalPages + "  •  " + total + " coins");

                int shown = coins == null ? 0 : coins.length();
                for (int i = 1; i <= PER_PAGE; i++) {
                    if (coins != null && i - 1 < shown) {
                        JSONObject c = coins.getJSONObject(i - 1);
                        String sym   = c.optString("symbol", "?");
                        String name  = c.optString("name", "");
                        String nat   = c.optString("native_symbol", "");
                        String price = c.optString("price", "0");
                        String chg   = c.optString("change_24h", "0%");
                        boolean up   = c.optBoolean("up", true);
                        String mcap  = c.optString("market_cap_native", "0");
                        String holders = String.valueOf(c.optInt("holders", 0));
                        boolean mining = c.optBoolean("mining_enabled", false);
                        String miningPct = c.optString("mining_minted_pct", "0");

                        String nameStr  = sym + " — " + name;
                        String priceStr = price + " " + nat;
                        String extraStr = "MC:" + mcap + " • H:" + holders
                                + (mining ? " • ⛏" + miningPct + "%" : "");

                        views.setTextViewText(id(ctx, "widget_mc_row" + i + "_name"), nameStr);
                        views.setTextViewText(id(ctx, "widget_mc_row" + i + "_price"), priceStr);
                        views.setTextViewText(id(ctx, "widget_mc_row" + i + "_chg"), chg);
                        views.setTextViewText(id(ctx, "widget_mc_row" + i + "_extra"), extraStr);

                        int chgColor = up ? 0xFF22C55E : 0xFFEF4444;
                        views.setTextColor(id(ctx, "widget_mc_row" + i + "_chg"), chgColor);

                        // Tap row → open that coin's page
                        Intent coinLaunch = new Intent(Intent.ACTION_VIEW,
                                Uri.parse(BASE_URL + "/memecoins?symbol=" + Uri.encode(sym)));
                        coinLaunch.setPackage(ctx.getPackageName());
                        coinLaunch.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK);
                        // Use unique request codes per row to avoid collisions
                        views.setOnClickPendingIntent(id(ctx, "widget_mc_row" + i + "_root"),
                                PendingIntent.getActivity(ctx, 60 + i, coinLaunch,
                                        Build.VERSION.SDK_INT >= 23
                                        ? PendingIntent.FLAG_IMMUTABLE | PendingIntent.FLAG_UPDATE_CURRENT
                                        : PendingIntent.FLAG_UPDATE_CURRENT));
                    } else {
                        views.setTextViewText(id(ctx, "widget_mc_row" + i + "_name"), "");
                        views.setTextViewText(id(ctx, "widget_mc_row" + i + "_price"), "");
                        views.setTextViewText(id(ctx, "widget_mc_row" + i + "_chg"), "");
                        views.setTextViewText(id(ctx, "widget_mc_row" + i + "_extra"), "");
                    }
                }

                mgr.updateAppWidget(widgetId, views);

            } catch (Exception e) {
                String em = e.getClass().getSimpleName();
                if (e.getMessage() != null)
                    em += ": " + e.getMessage().substring(0, Math.min(40, e.getMessage().length()));
                views.setTextViewText(id(ctx, "widget_mc_pager"), em);
                mgr.updateAppWidget(widgetId, views);
            } finally {
                try { if (reader != null) reader.close(); } catch (Exception ignored) {}
                try { if (conn != null) conn.disconnect(); } catch (Exception ignored) {}
            }
        }).start();
    }
}
