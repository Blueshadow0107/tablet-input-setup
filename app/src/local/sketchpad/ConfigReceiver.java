package local.sketchpad;

import android.content.BroadcastReceiver;
import android.content.Context;
import android.content.Intent;
import android.util.Log;

/**
 * The only way to set the address: adb shell am broadcast -f 32 -n local.sketchpad/.ConfigReceiver --es url 'http://...' [--ez debug true]
 * The manifest requires android.permission.DUMP, which the adb shell holds and ordinary apps do not.
 */
public class ConfigReceiver extends BroadcastReceiver {
    @Override
    public void onReceive(Context c, Intent i) {
        String url = i.getStringExtra("url");
        if (!Cfg.validUrl(url)) {
            Log.w("sketchpad", "config rejected: need http://<loopback|LAN|Tailscale ip>:<port>/?t=<token>");
            return;
        }
        c.getSharedPreferences("cfg", Context.MODE_PRIVATE).edit()
                .putString("url", url)
                .putBoolean("debug", i.getBooleanExtra("debug", false))
                .apply();
        Log.i("sketchpad", "config stored");
    }
}
