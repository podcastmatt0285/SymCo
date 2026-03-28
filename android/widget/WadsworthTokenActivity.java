package PACKAGE_NAME;

import android.app.Activity;
import android.content.SharedPreferences;
import android.net.Uri;
import android.os.Bundle;

/**
 * Transparent no-UI activity that receives the widget auth token from the
 * web app via an intent:// URL fired by JavaScript, then stores it in
 * SharedPreferences so the home-screen widget can use it to authenticate
 * API requests without needing access to Chrome's cookie store.
 *
 * Invoked by:
 *   intent://widget-auth?token=TOKEN#Intent;scheme=wadsworth;package=PACKAGE;end
 */
public class WadsworthTokenActivity extends Activity {

    static final String PREFS    = "wadsworth_widget";
    static final String KEY_TOKEN = "widget_token";

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        Uri data = getIntent().getData();
        if (data != null) {
            String token = data.getQueryParameter("token");
            if (token != null && !token.isEmpty()) {
                SharedPreferences prefs =
                        getSharedPreferences(PREFS, MODE_PRIVATE);
                prefs.edit().putString(KEY_TOKEN, token).apply();
            }
        }
        finish(); // close immediately — no UI shown
    }
}
