package PACKAGE_NAME;

import android.app.NotificationChannel;
import android.app.NotificationManager;
import android.media.AudioAttributes;
import android.net.Uri;
import android.os.Build;

import com.google.androidbrowserhelper.trusted.TrustedWebActivityService;

import androidx.core.app.NotificationManagerCompat;

/**
 * Subclass of TrustedWebActivityService that intercepts Chrome's notification
 * channel creation and pre-seeds it with our custom notification sound.
 *
 * Android never overwrites an existing NotificationChannel, so by creating
 * the channel (with our sound) the first time Chrome asks about it, we lock
 * in the custom sound for all future push notifications — even when the app
 * is backgrounded.
 */
public class WadsworthTwaService extends TrustedWebActivityService {

    @Override
    protected boolean onAreNotificationsEnabled(String channelName) {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O && channelName != null) {
            seedChannel(channelName);
        }
        return NotificationManagerCompat.from(this).areNotificationsEnabled();
    }

    /**
     * Create a notification channel with the given ID wired to notification.mp3.
     * No-ops if the channel already exists (Android ignores duplicate creates,
     * preserving the first-registered sound).
     */
    private void seedChannel(String channelId) {
        NotificationManager nm = (NotificationManager) getSystemService(NOTIFICATION_SERVICE);
        if (nm == null) return;
        if (nm.getNotificationChannel(channelId) != null) return; // already seeded

        Uri soundUri = Uri.parse(
                "android.resource://" + getPackageName() + "/raw/notification");

        AudioAttributes aa = new AudioAttributes.Builder()
                .setUsage(AudioAttributes.USAGE_NOTIFICATION)
                .setContentType(AudioAttributes.CONTENT_TYPE_SONIFICATION)
                .build();

        NotificationChannel channel = new NotificationChannel(
                channelId, "Wadsworth Alerts", NotificationManager.IMPORTANCE_HIGH);
        channel.setSound(soundUri, aa);
        channel.enableVibration(true);
        channel.setVibrationPattern(new long[]{100, 50, 100, 50, 100});
        nm.createNotificationChannel(channel);
    }
}
