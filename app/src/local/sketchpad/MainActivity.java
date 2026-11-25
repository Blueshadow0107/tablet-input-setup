package local.sketchpad;

import android.app.Activity;
import android.content.Intent;
import android.content.SharedPreferences;
import android.graphics.Color;
import android.net.Uri;
import android.os.Bundle;
import android.util.Log;
import android.view.MotionEvent;
import android.view.WindowInsets;
import android.view.WindowInsetsController;
import android.view.WindowManager;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.widget.TextView;

/**
 * One full-screen WebView on the sketchpad page. The URL (with its token) is given once with
 *   adb shell am start -n local.sketchpad/.MainActivity --es url "http://localhost:5099/?t=..."
 * and kept in this app's private storage. It never navigates away from that host.
 * Pen events are logged (adb logcat -s sketchpad) before the web engine sees them, so we can tell what
 * Chromium hides from the page, e.g. the S Pen side button held down while touching.
 */
public class MainActivity extends Activity {
    private static final String TAG = "sketchpad";
    private WebView web;
    private String lockedHost = "";
    private int lastButtons = -1;

    @Override
    protected void onCreate(Bundle b) {
        super.onCreate(b);
        getWindow().addFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON);
        getWindow().setDecorFitsSystemWindows(false);
        getWindow().setBackgroundDrawable(new android.graphics.drawable.ColorDrawable(Color.parseColor("#0f0a1a")));
        hideBars();
        WebView.setWebContentsDebuggingEnabled(true); // chrome://inspect over adb, handy for pen debugging
        show(getIntent());
    }

    @Override
    protected void onNewIntent(Intent i) {
        super.onNewIntent(i);
        setIntent(i);
        show(i);
    }

    private void show(Intent i) {
        SharedPreferences p = getSharedPreferences("cfg", MODE_PRIVATE);
        String url = i != null ? i.getStringExtra("url") : null;
        if (url != null && !url.isEmpty()) p.edit().putString("url", url).apply();
        url = p.getString("url", "");
        if (url.isEmpty()) {
            TextView t = new TextView(this);
            t.setTextColor(Color.WHITE);
            t.setTextSize(18);
            t.setPadding(60, 120, 60, 60);
            t.setText("No address yet.\n\nOn the laptop run:  sketch app");
            setContentView(t);
            return;
        }
        Uri u = Uri.parse(url);
        lockedHost = (u.getHost() == null ? "" : u.getHost()) + ":" + u.getPort();
        if (web == null) {
            web = new WebView(this);
            web.setBackgroundColor(Color.parseColor("#0f0a1a"));
            WebSettings s = web.getSettings();
            s.setJavaScriptEnabled(true);
            s.setDomStorageEnabled(true);
            s.setAllowFileAccess(false);
            s.setAllowContentAccess(false);
            s.setSupportZoom(false);
            s.setBuiltInZoomControls(false);
            s.setTextZoom(100);
            s.setMediaPlaybackRequiresUserGesture(true);
            web.setWebViewClient(new LockedClient(lockedHost)); // stay on our own server
            setContentView(web);
        }
        web.loadUrl(url);
    }

    private void hideBars() {
        WindowInsetsController c = getWindow().getInsetsController();
        if (c != null) {
            c.hide(WindowInsets.Type.systemBars());
            c.setSystemBarsBehavior(WindowInsetsController.BEHAVIOR_SHOW_TRANSIENT_BARS_BY_SWIPE);
        }
    }

    @Override
    public void onWindowFocusChanged(boolean hasFocus) {
        super.onWindowFocusChanged(hasFocus);
        if (hasFocus) hideBars();
    }

    // Raw pen events, before the web engine: log only when the button state changes
    private void logPen(MotionEvent e) {
        if (e.getPointerCount() > 0 && e.getToolType(0) == MotionEvent.TOOL_TYPE_STYLUS) {
            int bs = e.getButtonState();
            if (bs != lastButtons) {
                lastButtons = bs;
                Log.d(TAG, "pen action=" + MotionEvent.actionToString(e.getActionMasked()) + " buttons=" + bs + " pressure=" + e.getPressure());
            }
        }
    }

    @Override
    public boolean dispatchTouchEvent(MotionEvent e) {
        logPen(e);
        return super.dispatchTouchEvent(e);
    }

    @Override
    public boolean dispatchGenericMotionEvent(MotionEvent e) {
        logPen(e);
        return super.dispatchGenericMotionEvent(e);
    }

    @Override
    public void onBackPressed() {
        if (web != null && web.canGoBack()) web.goBack(); else super.onBackPressed();
    }
}
