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
 * Android never overwrites an existing NotificationChannel, so whichever
 * channel ID Chrome picks for web push, it will find ours (with our sound)
 * already registered and use it as-is.
 */
public class WadsworthApplication extends Application {

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
        for (String id : ids) {
            if (nm.getNotificationChannel(id) != null) continue; // already exists — leave it
            NotificationChannel ch = new NotificationChannel(
                    id, "Wadsworth Alerts", NotificationManager.IMPORTANCE_HIGH);
            ch.setSound(soundUri, aa);
            ch.enableVibration(true);
            ch.setVibrationPattern(new long[]{100, 50, 100, 50, 100});
            nm.createNotificationChannel(ch);
        }
    }
}
