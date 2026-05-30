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
import android.view.View;
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

    private static void clearRows(Context ctx, RemoteViews views) {
        int[] textIds = {
            id(ctx, "widget_p2p_founding"),
            id(ctx, "widget_p2p_pid"),
            id(ctx, "widget_p2p_networth"),
            id(ctx, "widget_p2p_worth_detail"),
            id(ctx, "widget_p2p_cash"),
            id(ctx, "widget_p2p_cash_other"),
            id(ctx, "widget_p2p_debt"),
            id(ctx, "widget_p2p_inv"),
            id(ctx, "widget_p2p_biz"),
            id(ctx, "widget_p2p_land"),
            id(ctx, "widget_p2p_city"),
            id(ctx, "widget_p2p_execs"),
            id(ctx, "widget_p2p_stocks"),
            id(ctx, "widget_p2p_bonds"),
            id(ctx, "widget_p2p_divs"),
            id(ctx, "widget_p2p_land_listings"),
            id(ctx, "widget_p2p_orders_com"),
            id(ctx, "widget_p2p_orders_dist"),
            id(ctx, "widget_p2p_orders"),
            id(ctx, "widget_p2p_bankrupt"),
        };
        for (int tid : textIds) views.setTextViewText(tid, "");
    }

    static void updateWidget(Context ctx, AppWidgetManager mgr, int widgetId) {
        RemoteViews views = new RemoteViews(ctx.getPackageName(), layoutId(ctx));

        int piFlags = Build.VERSION.SDK_INT >= 23 ? PendingIntent.FLAG_IMMUTABLE : 0;
        int muFlags = Build.VERSION.SDK_INT >= 23
                ? PendingIntent.FLAG_IMMUTABLE | PendingIntent.FLAG_UPDATE_CURRENT
                : PendingIntent.FLAG_UPDATE_CURRENT;

        // Tap name/avatar → open contacts page
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
                conn.setRequestProperty("Connection", "close");
                conn.setRequestProperty("User-Agent",
                        "Mozilla/5.0 (Linux; Android " + Build.VERSION.RELEASE + ") Wadsworth/1.0");

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

                JSONObject data      = new JSONObject(sb.toString());
                JSONArray  contacts  = data.optJSONArray("contacts");
                boolean    mktClosed = data.optBoolean("market_closed", false);
                int        total     = contacts != null ? contacts.length() : 0;

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

                // ── Identity ──
                String name       = c.optString("name", "Unknown");
                String initials   = name.length() > 0 ? String.valueOf(name.charAt(0)).toUpperCase() : "?";
                String pidStr     = c.optString("player_id_str", "");
                String level      = c.optString("level_label", "");
                boolean founding  = c.optBoolean("founding_tester", false);

                // ── Net Worth ──
                String netWorth  = c.optString("net_worth", "");
                String rank      = c.optString("wealth_rank", "");
                String landVal   = c.optString("land_value", "");
                String bizVal    = c.optString("biz_value", "");
                String invVal    = c.optString("inv_value", "");
                String shareVal  = c.optString("share_value", "");

                // ── Cash ──
                String cashUsd   = c.optString("cash_usd", "");
                String cashOther = c.optString("cash_other", "");

                // ── Debt ──
                String debt = c.optString("debt", "");

                // ── Inventory ──
                String inventory = c.optString("inventory", "");

                // ── Businesses ──
                String bizList = c.optString("biz_list", "");

                // ── Land ──
                String landDetail = c.optString("land_detail", "");

                // ── Executives ──
                String execDetail = c.optString("exec_detail", "");

                // ── Location ──
                String city   = c.optString("city", "");
                String county = c.optString("county", "");

                // ── Stocks ──
                String stockDetail = c.optString("stock_detail", "");

                // ── Bonds ──
                String bondDetail = c.optString("bond_detail", "");

                // ── Dividends ──
                String divRecv = c.optString("div_received", "");
                String divPaid = c.optString("div_paid", "");

                // ── Land Listings ──
                String landListings = c.optString("land_listings", "");

                // ── Market Orders ──
                String comOrderDetail  = c.optString("commodity_order_detail", "");
                String distOrderDetail = c.optString("district_order_detail", "");

                // ── P2P & Network ──
                int p2pOffers  = c.optInt("p2p_offers", 0);
                int contacts2  = c.optInt("contacts_count", 0);

                // ── Bankruptcy ──
                boolean bankrupt        = c.optBoolean("bankruptcy_active", false);
                String  bankruptDetail  = c.optString("bankruptcy_detail", "");

                // ══ RENDER ══

                views.setTextViewText(id(ctx, "widget_p2p_avatar"), initials);
                views.setTextViewText(id(ctx, "widget_p2p_name"),   name);
                views.setTextViewText(id(ctx, "widget_p2p_page"),   (idx + 1) + " / " + total);
                views.setTextViewText(id(ctx, "widget_p2p_pid"),    pidStr.isEmpty() ? "" : "Player ID " + pidStr);
                views.setTextViewText(id(ctx, "widget_p2p_level"),  level);
                views.setTextViewText(id(ctx, "widget_p2p_founding"),
                        founding ? "📱 Founding Tester" : "");

                // Net worth + rank
                String nwLine = "";
                if (!netWorth.isEmpty() && !rank.isEmpty())
                    nwLine = netWorth + "  ·  Rank " + rank;
                else if (!netWorth.isEmpty())
                    nwLine = netWorth;
                views.setTextViewText(id(ctx, "widget_p2p_networth"), nwLine);

                // Worth breakdown
                StringBuilder wdSb = new StringBuilder();
                if (!landVal.isEmpty())  { if (wdSb.length()>0) wdSb.append("  ·  "); wdSb.append("Land ").append(landVal); }
                if (!bizVal.isEmpty())   { if (wdSb.length()>0) wdSb.append("  ·  "); wdSb.append("Biz ").append(bizVal); }
                if (!invVal.isEmpty())   { if (wdSb.length()>0) wdSb.append("  ·  "); wdSb.append("Inv ").append(invVal); }
                if (!shareVal.isEmpty()) { if (wdSb.length()>0) wdSb.append("  ·  "); wdSb.append("Stk ").append(shareVal); }
                views.setTextViewText(id(ctx, "widget_p2p_worth_detail"), wdSb.toString());

                // Cash
                views.setTextViewText(id(ctx, "widget_p2p_cash"),
                        cashUsd.isEmpty() ? "" : "USD " + cashUsd);
                views.setTextViewText(id(ctx, "widget_p2p_cash_other"), cashOther);

                // Debt (green = clean, red = owed)
                if (debt.isEmpty()) {
                    views.setTextColor(id(ctx, "widget_p2p_debt"), 0xFF22c55e);
                    views.setTextViewText(id(ctx, "widget_p2p_debt"), "No outstanding debt");
                } else {
                    views.setTextColor(id(ctx, "widget_p2p_debt"), 0xFFef4444);
                    views.setTextViewText(id(ctx, "widget_p2p_debt"), debt);
                }

                // Inventory
                views.setTextViewText(id(ctx, "widget_p2p_inv"),
                        inventory.isEmpty() ? "Empty" : inventory);

                // Businesses
                views.setTextViewText(id(ctx, "widget_p2p_biz"),
                        bizList.isEmpty() ? "None" : bizList);

                // Land
                views.setTextViewText(id(ctx, "widget_p2p_land"),
                        landDetail.isEmpty() ? "No plots owned" : landDetail);

                // Location
                String cityLine = "";
                if (!city.isEmpty() && !county.isEmpty())
                    cityLine = "🏙️ " + city + "  ·  🗺️ " + county;
                else if (!city.isEmpty())
                    cityLine = "🏙️ " + city;
                else if (!county.isEmpty())
                    cityLine = "🗺️ " + county;
                else
                    cityLine = "No city or county";
                views.setTextViewText(id(ctx, "widget_p2p_city"), cityLine);

                // Executives
                views.setTextViewText(id(ctx, "widget_p2p_execs"),
                        execDetail.isEmpty() ? "None" : execDetail);

                // Stocks
                views.setTextViewText(id(ctx, "widget_p2p_stocks"),
                        stockDetail.isEmpty() ? "No positions" : stockDetail);

                // Bonds
                views.setTextViewText(id(ctx, "widget_p2p_bonds"),
                        bondDetail.isEmpty() ? "No active bonds" : bondDetail);

                // Dividends
                String divLine = "";
                if (!divRecv.isEmpty() && !divPaid.isEmpty())
                    divLine = "Received " + divRecv + "  ·  Paid out " + divPaid;
                else if (!divRecv.isEmpty())
                    divLine = "Received " + divRecv;
                else if (!divPaid.isEmpty())
                    divLine = "Paid out " + divPaid;
                else
                    divLine = "No dividends";
                views.setTextViewText(id(ctx, "widget_p2p_divs"), divLine);

                // Land listings
                views.setTextViewText(id(ctx, "widget_p2p_land_listings"),
                        landListings.isEmpty() ? "None active" : landListings);

                // Market orders (commodity)
                if (mktClosed) {
                    views.setTextViewText(id(ctx, "widget_p2p_orders_com"),
                            "⛔ MARKET CLOSED — PANDEMIC");
                    views.setTextViewText(id(ctx, "widget_p2p_orders_dist"), "");
                } else {
                    views.setTextViewText(id(ctx, "widget_p2p_orders_com"),
                            comOrderDetail.isEmpty() ? "None active" : comOrderDetail);
                    views.setTextViewText(id(ctx, "widget_p2p_orders_dist"),
                            distOrderDetail.isEmpty() ? "" : "District:\n" + distOrderDetail);
                }

                // P2P & Network
                StringBuilder netSb = new StringBuilder();
                if (p2pOffers > 0)
                    netSb.append("📄 ").append(p2pOffers).append(" P2P offer").append(p2pOffers == 1 ? "" : "s");
                if (contacts2 > 0) {
                    if (netSb.length() > 0) netSb.append("  ·  ");
                    netSb.append("🤝 ").append(contacts2).append(" contact").append(contacts2 == 1 ? "" : "s");
                }
                views.setTextViewText(id(ctx, "widget_p2p_orders"),
                        netSb.length() > 0 ? netSb.toString() : "No P2P activity");

                // Bankruptcy
                if (bankrupt) {
                    views.setTextColor(id(ctx, "widget_p2p_bankrupt"), 0xFFef4444);
                } else if (bankruptDetail.equals("Clean record")) {
                    views.setTextColor(id(ctx, "widget_p2p_bankrupt"), 0xFF22c55e);
                } else {
                    views.setTextColor(id(ctx, "widget_p2p_bankrupt"), 0xFF94a3b8);
                }
                views.setTextViewText(id(ctx, "widget_p2p_bankrupt"),
                        bankruptDetail.isEmpty() ? "Clean record" : bankruptDetail);

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
