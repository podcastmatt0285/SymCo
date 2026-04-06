package PACKAGE_NAME;

import android.app.Application;
import android.app.NotificationChannel;
import android.app.NotificationManager;
import android.media.AudioAttributes;
import android.net.Uri;
import android.os.Build;
import android.webkit.CookieManager;

/**
 * Custom Application class that pre-seeds notification channels with the
 * Wadsworth custom sound before Chrome/TWA can create them with a default.
 *
 * Android never overwrites an existing NotificationChannel, so we delete
 * any existing channel that lacks our custom sound, then re-create it.
 * This handles the case where Chrome already created the channel before the
 * app had a chance to seed it (e.g. on first install or after app-data clear).
 */
public class WadsworthApplication extends Application {

    // Increment this when the desired sound/settings change so existing
    // installs have their stale channels replaced on the next app launch.
    private static final int CHANNEL_VERSION = 2;
    private static final String PREF_CHANNEL_VER = "notif_channel_ver";

    @Override
    public void onCreate() {
        super.onCreate();
        // Pre-initialize CookieManager on the main thread.
        // On Android 9+, CookieManager.getInstance() must be called from the
        // main thread at least once before background threads can use it.
        // Without this the widget's background thread gets null cookies.
        try {
            CookieManager.getInstance().setAcceptCookie(true);
        } catch (Exception ignored) {}

        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            seedNotificationChannels();
        }
    }

    private void seedNotificationChannels() {
        NotificationManager nm = (NotificationManager) getSystemService(NOTIFICATION_SERVICE);
        if (nm == null) return;

        android.content.SharedPreferences prefs =
                getSharedPreferences("wadsworth_prefs", MODE_PRIVATE);
        int installedVer = prefs.getInt(PREF_CHANNEL_VER, 0);

        Uri soundUri = Uri.parse(
                "android.resource://" + getPackageName() + "/raw/notification");

        AudioAttributes aa = new AudioAttributes.Builder()
                .setUsage(AudioAttributes.USAGE_NOTIFICATION)
                .setContentType(AudioAttributes.CONTENT_TYPE_SONIFICATION)
                .build();

        // Chrome / android-browser-helper rotate through several channel IDs for
        // web push.  Pre-register all of them with our sound so the first one
        // Chrome lands on already has the custom sound locked in.
        String[] ids = {"default", "browser", "browser_notify_default", "Browser"};

        if (installedVer < CHANNEL_VERSION) {
            // Delete stale channels so we can recreate them with updated settings.
            // Android won't let you change sound on an existing channel, so we
            // must delete and recreate.  The user-visible importance/badge setting
            // is preserved because Android merges the user's choice back in on
            // the next createNotificationChannel() call.
            for (String id : ids) {
                if (nm.getNotificationChannel(id) != null) {
                    nm.deleteNotificationChannel(id);
                }
            }
            prefs.edit().putInt(PREF_CHANNEL_VER, CHANNEL_VERSION).apply();
        }

        for (String id : ids) {
            if (nm.getNotificationChannel(id) != null) continue; // already seeded this session
            NotificationChannel ch = new NotificationChannel(
                    id, "Wadsworth Alerts", NotificationManager.IMPORTANCE_HIGH);
            ch.setSound(soundUri, aa);
            ch.enableVibration(true);
            ch.setVibrationPattern(new long[]{100, 50, 100, 50, 100});
            nm.createNotificationChannel(ch);
        }
    }
}
