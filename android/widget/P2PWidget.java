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

    /** Clear all data rows to blank before fetch or on error. */
    private static void clearRows(Context ctx, RemoteViews views) {
        views.setTextViewText(id(ctx, "widget_p2p_founding"),    "");
        views.setTextViewText(id(ctx, "widget_p2p_networth"),    "");
        views.setTextViewText(id(ctx, "widget_p2p_worth_detail"),"");
        views.setTextViewText(id(ctx, "widget_p2p_cash"),        "");
        views.setTextViewText(id(ctx, "widget_p2p_cash_other"),  "");
        views.setTextViewText(id(ctx, "widget_p2p_debt"),        "");
        views.setTextViewText(id(ctx, "widget_p2p_biz"),         "");
        views.setTextViewText(id(ctx, "widget_p2p_execs"),       "");
        views.setTextViewText(id(ctx, "widget_p2p_city"),        "");
        views.setTextViewText(id(ctx, "widget_p2p_stocks"),      "");
        views.setTextViewText(id(ctx, "widget_p2p_divs"),        "");
        views.setTextViewText(id(ctx, "widget_p2p_orders"),      "");
        views.setTextViewText(id(ctx, "widget_p2p_bankrupt"),    "");
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

        // Prev / Next buttons
        Intent prevI = new Intent(ACTION_PREV);
        prevI.setComponent(new ComponentName(ctx, P2PWidget.class));
        views.setOnClickPendingIntent(id(ctx, "widget_p2p_prev"),
                PendingIntent.getBroadcast(ctx, 42, prevI, muFlags));

        Intent nextI = new Intent(ACTION_NEXT);
        nextI.setComponent(new ComponentName(ctx, P2PWidget.class));
        views.setOnClickPendingIntent(id(ctx, "widget_p2p_next"),
                PendingIntent.getBroadcast(ctx, 43, nextI, muFlags));

        // Loading state
        views.setTextViewText(id(ctx, "widget_p2p_name"), "Loading…");
        views.setTextViewText(id(ctx, "widget_p2p_level"), "");
        views.setTextViewText(id(ctx, "widget_p2p_avatar"), "?");
        views.setTextViewText(id(ctx, "widget_p2p_page"), "");
        clearRows(ctx, views);
        mgr.updateAppWidget(widgetId, views);

        final String deviceHash = getDeviceHash(ctx);
        final SharedPreferences prefs = ctx.getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE);
        final int requestedIndex = prefs.getInt(KEY_INDEX, 0);

        new Thread(() -> {
            HttpURLConnection conn = null;
            BufferedReader reader = null;
            try {
                String dataUrl = BASE_URL + "/api/widget/p2p-contacts";
                if (deviceHash != null)
                    dataUrl += "?device_id=" + Uri.encode(deviceHash);

                URL url = new URL(dataUrl);
                conn = (HttpURLConnection) url.openConnection();
                conn.setRequestMethod("GET");
                conn.setConnectTimeout(10000);
                conn.setReadTimeout(10000);
                conn.setRequestProperty("Accept", "application/json");
                // Disable keep-alive to prevent stale pooled sockets after device sleep
                conn.setRequestProperty("Connection", "close");
                conn.setRequestProperty("User-Agent",
                        "Mozilla/5.0 (Linux; Android 10) Wadsworth/1.0");

                int httpCode = conn.getResponseCode();
                if (httpCode != 200) {
                    views.setTextViewText(id(ctx, "widget_p2p_name"),
                            httpCode == 401 ? "Open app to log in" : "Server error " + httpCode);
                    mgr.updateAppWidget(widgetId, views);
                    return;
                }

                reader = new BufferedReader(
                        new InputStreamReader(conn.getInputStream(), "UTF-8"));
                StringBuilder sb = new StringBuilder();
                String line;
                while ((line = reader.readLine()) != null) sb.append(line);

                JSONObject data        = new JSONObject(sb.toString());
                JSONArray  contacts    = data.optJSONArray("contacts");
                boolean    mktClosed   = data.optBoolean("market_closed", false);
                int        total       = contacts != null ? contacts.length() : 0;

                if (total == 0) {
                    views.setTextViewText(id(ctx, "widget_p2p_name"), "No contacts yet");
                    views.setTextViewText(id(ctx, "widget_p2p_page"), "0 / 0");
                    views.setTextViewText(id(ctx, "widget_p2p_avatar"), "?");
                    mgr.updateAppWidget(widgetId, views);
                    return;
                }

                // Clamp index
                int idx = Math.min(requestedIndex, total - 1);
                if (idx != requestedIndex)
                    prefs.edit().putInt(KEY_INDEX, idx).apply();

                JSONObject c = contacts.getJSONObject(idx);

                // Identity
                String name     = c.optString("name", "Unknown");
                String initials = name.length() > 0 ? String.valueOf(name.charAt(0)).toUpperCase() : "?";
                String level    = c.optString("level_label", "");
                boolean founding = c.optBoolean("founding_tester", false);

                // Net worth & breakdown
                String netWorth   = c.optString("net_worth", "");
                String rank       = c.optString("wealth_rank", "");
                String landVal    = c.optString("land_value", "");
                String bizVal     = c.optString("biz_value", "");
                String invVal     = c.optString("inv_value", "");
                String shareVal   = c.optString("share_value", "");

                // Cash
                String cashUsd   = c.optString("cash_usd", "");
                String cashOther = c.optString("cash_other", "");

                // Debt
                String debt = c.optString("debt", "");

                // Business + land
                String bizList   = c.optString("biz_list", "");
                String landCount = c.optString("land_count", "");

                // Executives
                String execSummary = c.optString("exec_summary", "");

                // City + county
                String city   = c.optString("city", "");
                String county = c.optString("county", "");

                // Stocks + bonds
                String stockDetail = c.optString("stock_detail", "");
                String bondDetail  = c.optString("bond_detail", "");

                // Dividends
                String divRecv = c.optString("div_received", "");
                String divPaid = c.optString("div_paid", "");

                // Orders + social
                int comOrders  = c.optInt("commodity_orders", 0);
                int distOrders = c.optInt("district_orders", 0);
                int p2pOffers  = c.optInt("p2p_offers", 0);
                int contacts2  = c.optInt("contacts_count", 0);

                // Bankruptcy
                boolean bankrupt = c.optBoolean("bankruptcy_active", false);

                // ── Render ──

                views.setTextViewText(id(ctx, "widget_p2p_avatar"), initials);
                views.setTextViewText(id(ctx, "widget_p2p_name"), name);
                views.setTextViewText(id(ctx, "widget_p2p_page"), (idx + 1) + " / " + total);
                views.setTextViewText(id(ctx, "widget_p2p_level"), level);

                views.setTextViewText(id(ctx, "widget_p2p_founding"),
                        founding ? "📱 Founding Tester" : "");

                // Net worth + rank
                String nwLine = "";
                if (!netWorth.isEmpty() && !rank.isEmpty())
                    nwLine = "💰 " + netWorth + "  ·  Rank " + rank;
                else if (!netWorth.isEmpty())
                    nwLine = "💰 " + netWorth;
                views.setTextViewText(id(ctx, "widget_p2p_networth"), nwLine);

                // Worth breakdown
                StringBuilder wdSb = new StringBuilder();
                if (!landVal.isEmpty())  { if (wdSb.length()>0) wdSb.append(" · "); wdSb.append("Land ").append(landVal); }
                if (!bizVal.isEmpty())   { if (wdSb.length()>0) wdSb.append(" · "); wdSb.append("Biz ").append(bizVal); }
                if (!invVal.isEmpty())   { if (wdSb.length()>0) wdSb.append(" · "); wdSb.append("Inv ").append(invVal); }
                if (!shareVal.isEmpty()) { if (wdSb.length()>0) wdSb.append(" · "); wdSb.append("Stk ").append(shareVal); }
                views.setTextViewText(id(ctx, "widget_p2p_worth_detail"),
                        wdSb.length() > 0 ? "  " + wdSb : "");

                views.setTextViewText(id(ctx, "widget_p2p_cash"),
                        cashUsd.isEmpty() ? "" : "💵 USD " + cashUsd);
                views.setTextViewText(id(ctx, "widget_p2p_cash_other"),
                        cashOther.isEmpty() ? "" : "     " + cashOther);
                views.setTextViewText(id(ctx, "widget_p2p_debt"),
                        debt.isEmpty() ? "" : "💳 Debt: " + debt);

                // Business list + land
                String bizLine = "";
                if (!bizList.isEmpty() && !landCount.isEmpty())
                    bizLine = "🏭 " + bizList + "  ·  🌍 " + landCount;
                else if (!bizList.isEmpty())
                    bizLine = "🏭 " + bizList;
                else if (!landCount.isEmpty())
                    bizLine = "🌍 " + landCount;
                views.setTextViewText(id(ctx, "widget_p2p_biz"), bizLine);

                views.setTextViewText(id(ctx, "widget_p2p_execs"),
                        execSummary.isEmpty() ? "" : "👔 " + execSummary);

                // City + county
                String cityLine = "";
                if (!city.isEmpty() && !county.isEmpty())
                    cityLine = "🏙️ " + city + "  ·  🗺️ " + county;
                else if (!city.isEmpty())
                    cityLine = "🏙️ " + city;
                else if (!county.isEmpty())
                    cityLine = "🗺️ " + county;
                views.setTextViewText(id(ctx, "widget_p2p_city"), cityLine);

                // Stocks + bonds
                String mktLine = "";
                if (!stockDetail.isEmpty() && !bondDetail.isEmpty())
                    mktLine = "📈 " + stockDetail + "  ·  🏦 " + bondDetail;
                else if (!stockDetail.isEmpty())
                    mktLine = "📈 " + stockDetail;
                else if (!bondDetail.isEmpty())
                    mktLine = "🏦 " + bondDetail;
                views.setTextViewText(id(ctx, "widget_p2p_stocks"), mktLine);

                // Dividends
                String divLine = "";
                if (!divRecv.isEmpty() && !divPaid.isEmpty())
                    divLine = "💸 Recv " + divRecv + "  ·  Paid " + divPaid;
                else if (!divRecv.isEmpty())
                    divLine = "💸 Recv " + divRecv;
                else if (!divPaid.isEmpty())
                    divLine = "💸 Paid out " + divPaid;
                views.setTextViewText(id(ctx, "widget_p2p_divs"), divLine);

                // Orders + P2P + contacts
                StringBuilder ordSb = new StringBuilder();
                if (mktClosed) {
                    ordSb.append("⛔ MARKET CLOSED — PANDEMIC");
                } else {
                    if (comOrders > 0)  ordSb.append("📋 ").append(comOrders).append(" orders");
                    if (distOrders > 0) { if (ordSb.length()>0) ordSb.append("  ·  "); ordSb.append("🏗️ ").append(distOrders); }
                }
                if (p2pOffers > 0)  { if (ordSb.length()>0) ordSb.append("  ·  "); ordSb.append("📄 ").append(p2pOffers).append(" P2P"); }
                if (contacts2 > 0)  { if (ordSb.length()>0) ordSb.append("  ·  "); ordSb.append("🤝 ").append(contacts2); }
                views.setTextViewText(id(ctx, "widget_p2p_orders"), ordSb.toString());

                views.setTextViewText(id(ctx, "widget_p2p_bankrupt"),
                        bankrupt ? "⚖️ 🔴 ACTIVE BANKRUPTCY" : "");

                mgr.updateAppWidget(widgetId, views);

            } catch (Exception e) {
                String em = e.getClass().getSimpleName();
                if (e.getMessage() != null)
                    em += ": " + e.getMessage().substring(0, Math.min(40, e.getMessage().length()));
                views.setTextViewText(id(ctx, "widget_p2p_name"), em);
                views.setTextViewText(id(ctx, "widget_p2p_page"), "");
                mgr.updateAppWidget(widgetId, views);
            } finally {
                try { if (reader != null) reader.close(); } catch (Exception ignored) {}
                try { if (conn != null) conn.disconnect(); } catch (Exception ignored) {}
            }
        }).start();
    }
}
