package local.sketchpad;

import android.net.Uri;
import android.webkit.WebResourceRequest;
import android.webkit.WebView;
import android.webkit.WebViewClient;

/** Keeps the WebView on the one host:port it was given; every other navigation is refused. */
public class LockedClient extends WebViewClient {
    private final String host;

    public LockedClient(String host) {
        this.host = host;
    }

    @Override
    public boolean shouldOverrideUrlLoading(WebView v, WebResourceRequest r) {
        Uri t = r.getUrl();
        return !((t.getHost() == null ? "" : t.getHost()) + ":" + t.getPort()).equals(host);
    }
}
