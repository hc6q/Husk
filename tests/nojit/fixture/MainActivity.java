package org.husk.nojitsmoke;

import android.app.Activity;
import android.media.AudioManager;
import android.media.ToneGenerator;
import android.os.Bundle;
import android.widget.Button;
import android.widget.LinearLayout;
import android.widget.TextView;

/** Offline fixture: visible frame, touch counter, and an audible tone. */
public final class MainActivity extends Activity {
    private int count;
    private ToneGenerator tone;

    @Override public void onCreate(Bundle state) {
        super.onCreate(state);
        LinearLayout column = new LinearLayout(this);
        column.setOrientation(LinearLayout.VERTICAL);
        column.setPadding(24, 48, 24, 24);
        TextView label = new TextView(this);
        label.setText("Husk No-JIT: Android app running\nTouches: 0");
        label.setTextSize(24);
        Button tap = new Button(this);
        tap.setText("Count touch");
        tap.setOnClickListener(view -> label.setText(
            "Husk No-JIT: Android app running\nTouches: " + (++count)));
        Button sound = new Button(this);
        sound.setText("Play tone");
        sound.setOnClickListener(view -> {
            if (tone == null) tone = new ToneGenerator(AudioManager.STREAM_MUSIC, 80);
            tone.startTone(ToneGenerator.TONE_PROP_BEEP, 400);
        });
        column.addView(label);
        column.addView(tap);
        column.addView(sound);
        setContentView(column);
    }

    @Override public void onDestroy() {
        if (tone != null) tone.release();
        super.onDestroy();
    }
}
