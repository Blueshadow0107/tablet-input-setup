package local.sketchpad;

import android.net.Uri;

/** What URL the app may load: plain http, an explicit port, a token, and only loopback / private-LAN / Tailscale addresses. */
final class Cfg {
    private Cfg() {
    }

    static boolean validUrl(String s) {
        if (s == null || s.length() > 512) return false;
        Uri u = Uri.parse(s);
        if (!"http".equals(u.getScheme()) || u.getHost() == null || u.getPort() < 1) return false;
        String t = u.getQueryParameter("t");
        return t != null && !t.isEmpty() && localHost(u.getHost());
    }

    static boolean localHost(String h) {
        if (h.equals("localhost")) return true;
        String[] p = h.split("\\.");
        if (p.length != 4) return false;
        int[] a = new int[4];
        for (int i = 0; i < 4; i++) {
            try {
                a[i] = Integer.parseInt(p[i]);
            } catch (NumberFormatException e) {
                return false;
            }
            if (a[i] < 0 || a[i] > 255) return false;
        }
        return a[0] == 127 || a[0] == 10 || (a[0] == 192 && a[1] == 168) || (a[0] == 172 && a[1] >= 16 && a[1] <= 31) || (a[0] == 100 && a[1] >= 64 && a[1] <= 127);
    }

    static String origin(Uri u) {
        return u.getScheme() + "://" + u.getHost() + ":" + u.getPort();
    }
}
