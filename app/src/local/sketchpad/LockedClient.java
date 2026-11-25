package local.sketchpad;

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

    public LockedClient(String origin) {
        this.origin = origin;
    }

    private boolean same(Uri u) {
        return u != null && origin.equals(Cfg.origin(u));
    }

    @Override
    public boolean shouldOverrideUrlLoading(WebView v, WebResourceRequest r) {
        return !same(r.getUrl());
    }

    @Override
    public WebResourceResponse shouldInterceptRequest(WebView v, WebResourceRequest r) {
        if (same(r.getUrl())) return null;
        return new WebResourceResponse("text/plain", "utf-8", 403, "Blocked", new HashMap<String, String>(), new ByteArrayInputStream(new byte[0]));
    }
}
