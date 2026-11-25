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
public class MainActivity extends Activity implements Runnable {
    // The grip can brush the S Pen button: it flickers on for 60-800 ms at zero pressure. A press only counts once it has been down this long.
    private static final long BTN_CONFIRM_MS = 110;
    // A grip that squeezes the button mid-stroke can hold it for a long time, and each one erases. A press that begins while the tip is touching must last this long.
    private static final long BTN_CONFIRM_TOUCH_MS = 450;
    private static final String TAG = "sketchpad";
    private WebView web;
    private int lastButtons = -1;
    private boolean held = false, nativeDriven = false, rawHeld = false, touching = false;
    private boolean pressedInAir = false;
    private long rawSince = 0;

    @Override
    protected void onCreate(Bundle b) {
        super.onCreate(b);
        getWindow().addFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON);
        getWindow().setDecorFitsSystemWindows(false);
        getWindow().setBackgroundDrawable(new android.graphics.drawable.ColorDrawable(Color.parseColor("#0f0a1a")));
        show();
        hideBars(); // after the content view exists: on a cold start the decor view is still null before that
    }

    @Override
    protected void onNewIntent(Intent i) {
        super.onNewIntent(i);
        show(); // intent extras are ignored on purpose: the address comes only from ConfigReceiver (shell-only)
    }

    private void show() {
        SharedPreferences p = getSharedPreferences("cfg", MODE_PRIVATE);
        String url = p.getString("url", "");
        WebView.setWebContentsDebuggingEnabled(p.getBoolean("debug", false)); // chrome://inspect only when asked for over adb
        if (!Cfg.validUrl(url)) {
            TextView t = new TextView(this);
            t.setTextColor(Color.WHITE);
            t.setTextSize(18);
            t.setPadding(60, 120, 60, 60);
            t.setText("No address yet.\n\nOn the laptop run:  sketch app");
            setContentView(t);
            return;
        }
        Uri u = Uri.parse(url);
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
            s.setUserAgentString(s.getUserAgentString() + " SketchpadApp/1"); // the page uses this to know the app reports the S Pen button natively
            s.setMediaPlaybackRequiresUserGesture(true);
            setContentView(web);
        }
        web.setWebViewClient(new LockedClient(Cfg.origin(u))); // re-pinned every time the address changes
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

    private void js(String code) {
        if (web != null) web.evaluateJavascript(code, null);
    }

    // Raw pen events, before the web engine. Chromium hides touches made while the S Pen button is held, so the app tells the page itself:
    // window.__penBtn(down) on every button change, and window.__penXY(x, y, phase) for a stroke that started with the button held.
    private void logPen(MotionEvent e) {
        if (e.getPointerCount() == 0 || e.getToolType(0) != MotionEvent.TOOL_TYPE_STYLUS) return;
        int bs = e.getButtonState(), a = e.getActionMasked();
        if (bs != lastButtons) {
            lastButtons = bs;
            Log.d(TAG, "pen action=" + MotionEvent.actionToString(a) + " buttons=" + bs + " pressure=" + e.getPressure());
        }
        boolean raw = (bs & MotionEvent.BUTTON_STYLUS_PRIMARY) != 0;
        if (a == MotionEvent.ACTION_HOVER_EXIT) raw = false;
        long t = e.getEventTime();
        if (a == MotionEvent.ACTION_DOWN) touching = true;
        if (a == MotionEvent.ACTION_UP || a == MotionEvent.ACTION_CANCEL) touching = false;
        if (raw != rawHeld) { // the raw button state changed: start timing it
            rawHeld = raw;
            rawSince = t;
            pressedInAir = raw && !touching; // where the press began decides how long it must last
            if (raw && web != null) {  // re-check even if the pen then stays still
                web.postDelayed(this, BTN_CONFIRM_MS + 5);
                web.postDelayed(this, BTN_CONFIRM_TOUCH_MS + 5);
            }
        }
        updateHeld(t);
        if (a == MotionEvent.ACTION_DOWN) nativeDriven = held;
        if (nativeDriven) {
            int phase = a == MotionEvent.ACTION_DOWN ? 0 : (a == MotionEvent.ACTION_MOVE ? 1 : (a == MotionEvent.ACTION_UP || a == MotionEvent.ACTION_CANCEL ? 2 : -1));
            if (phase >= 0) {
                js("window.__penXY&&window.__penXY(" + e.getX() + "," + e.getY() + "," + phase + ")");
                if (phase == 2) nativeDriven = false;
            }
        }
    }

    // a release counts at once; a press only after it has lasted BTN_CONFIRM_MS
    private void updateHeld(long now) {
        boolean h = rawHeld && now - rawSince >= (pressedInAir ? BTN_CONFIRM_MS : BTN_CONFIRM_TOUCH_MS);
        if (h != held) {
            held = h;
            js("window.__penBtn&&window.__penBtn(" + h + ")");
        }
    }

    @Override
    public void run() {
        updateHeld(android.os.SystemClock.uptimeMillis());
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
