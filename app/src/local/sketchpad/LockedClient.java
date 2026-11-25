package local.sketchpad;

import android.app.Activity;
import android.content.pm.ActivityInfo;
import android.net.Uri;
import android.webkit.WebResourceRequest;
import android.webkit.WebResourceResponse;
import android.webkit.WebView;
import android.webkit.WebViewClient;

import java.io.ByteArrayInputStream;
import java.util.HashMap;

/** Pins the WebView to one origin (scheme + host + port): other navigations AND other subresource requests are refused. */
public class LockedClient extends WebViewClient {
    private final String origin;
    private final Activity activity;

    public LockedClient(Activity activity, String origin) {
        this.activity = activity;
        this.origin = origin;
    }

    // The page asks for a screen orientation by navigating its TOP frame to sketchpad://orientation/<auto|portrait|landscape>. Sub-frames (pages) cannot.
    private void orientation(String mode) {
        int o = ActivityInfo.SCREEN_ORIENTATION_UNSPECIFIED;
        if ("portrait".equals(mode)) o = ActivityInfo.SCREEN_ORIENTATION_SENSOR_PORTRAIT;
        else if ("landscape".equals(mode)) o = ActivityInfo.SCREEN_ORIENTATION_SENSOR_LANDSCAPE;
        activity.setRequestedOrientation(o);
    }

    private boolean same(Uri u) {
        return u != null && origin.equals(Cfg.origin(u));
    }

    @Override
    public boolean shouldOverrideUrlLoading(WebView v, WebResourceRequest r) {
        Uri t = r.getUrl();
        if (t != null && "sketchpad".equals(t.getScheme())) {
            if (r.isForMainFrame() && "orientation".equals(t.getHost())) orientation(t.getLastPathSegment());
            return true; // never actually navigates
        }
        return !same(t);
    }

    @Override
    public WebResourceResponse shouldInterceptRequest(WebView v, WebResourceRequest r) {
        if (same(r.getUrl())) return null;
        return new WebResourceResponse("text/plain", "utf-8", 403, "Blocked", new HashMap<String, String>(), new ByteArrayInputStream(new byte[0]));
    }
}
