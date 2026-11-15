package org.gminfo.audioprobe;

import android.app.Activity;
import android.content.Intent;
import android.media.AudioAttributes;
import android.media.AudioDeviceInfo;
import android.media.AudioFocusRequest;
import android.media.AudioFormat;
import android.media.AudioManager;
import android.media.AudioRouting;
import android.media.AudioTrack;
import android.os.Bundle;
import android.os.Handler;
import android.os.Looper;
import android.util.Log;
import android.view.Gravity;
import android.view.WindowManager;
import android.widget.ArrayAdapter;
import android.widget.Button;
import android.widget.LinearLayout;
import android.widget.ScrollView;
import android.widget.SeekBar;
import android.widget.Spinner;
import android.widget.TextView;

public final class MainActivity extends Activity {
    private static final String TAG = "AudioUsageProbe";
    private static final int RATE = 48000;
    private static final int BLOCK = 480;
    private static final String[] KEYS = {
        "media", "navigation", "assistant", "call", "ringtone", "alarm", "notification", "system",
        "unknown", "signalling", "request", "instant", "delayed", "event", "accessibility", "game",
        "call_assistant", "emergency", "safety", "vehicle_status", "announcement"
    };
    private static final String[] LABELS = {
        "Media", "Navigation guidance", "Voice assistant", "Phone / voice communication",
        "Call ringtone", "Alarm", "Notification", "System sonification",
        "Unknown / default", "Voice signalling", "Notification request (deprecated)",
        "Notification instant (deprecated)", "Notification delayed (deprecated)",
        "Notification event (deprecated)", "Accessibility", "Game",
        "Call assistant (system)", "Emergency (system)", "Safety (system)",
        "Vehicle status (system)", "Announcement (system)"
    };
    private static final int[] USAGES = {
        AudioAttributes.USAGE_MEDIA, AudioAttributes.USAGE_ASSISTANCE_NAVIGATION_GUIDANCE,
        AudioAttributes.USAGE_ASSISTANT, AudioAttributes.USAGE_VOICE_COMMUNICATION,
        AudioAttributes.USAGE_NOTIFICATION_RINGTONE, AudioAttributes.USAGE_ALARM,
        AudioAttributes.USAGE_NOTIFICATION, AudioAttributes.USAGE_ASSISTANCE_SONIFICATION,
        AudioAttributes.USAGE_UNKNOWN, AudioAttributes.USAGE_VOICE_COMMUNICATION_SIGNALLING,
        AudioAttributes.USAGE_NOTIFICATION_COMMUNICATION_REQUEST, AudioAttributes.USAGE_NOTIFICATION_COMMUNICATION_INSTANT,
        AudioAttributes.USAGE_NOTIFICATION_COMMUNICATION_DELAYED, AudioAttributes.USAGE_NOTIFICATION_EVENT,
        AudioAttributes.USAGE_ASSISTANCE_ACCESSIBILITY, AudioAttributes.USAGE_GAME,
        17, 1000, 1001, 1002, 1003
    };
    private static final int[] FREQUENCIES = {440, 660, 880, 550, 1100, 1320, 1540, 1760, 480, 720, 960, 1200, 1440, 1680, 1920, 2160, 600, 800, 1000, 1400, 1800};
    private static final int[] GAINS = {
        AudioManager.AUDIOFOCUS_GAIN, AudioManager.AUDIOFOCUS_GAIN_TRANSIENT,
        AudioManager.AUDIOFOCUS_GAIN_TRANSIENT_MAY_DUCK
    };

    private final Handler main = new Handler(Looper.getMainLooper());
    private AudioManager audio;
    private Spinner usageChoice, channelChoice, focusChoice;
    private SeekBar level;
    private TextView status, levelLabel;
    private AudioFocusRequest focusRequest;
    private Playback playback;
    private String last = "Idle. Select a usage, then play.";
    private String lastDetails = "";
    private boolean foreground;
    private int commandGeneration;

    @Override public void onCreate(Bundle state) {
        super.onCreate(state);
        audio = (AudioManager) getSystemService(AUDIO_SERVICE);
        getWindow().setFlags(WindowManager.LayoutParams.FLAG_FULLSCREEN,
                WindowManager.LayoutParams.FLAG_FULLSCREEN);
        buildUi();
        handleCommand(getIntent());
    }

    private void buildUi() {
        ScrollView scroll = new ScrollView(this);
        LinearLayout body = new LinearLayout(this);
        body.setOrientation(LinearLayout.VERTICAL);
        int pad = dp(20);
        body.setPadding(pad, pad, pad, pad);
        scroll.addView(body);
        TextView title = new TextView(this);
        title.setText("AAOS Audio Probe");
        title.setTextSize(26);
        body.addView(title);
        TextView info = new TextView(this);
        info.setText("Public audio usages • generated 48 kHz stereo PCM • routing is decided by AAOS\n"
                + "No global volume or call mode changes. Playback stops when this screen leaves the foreground.");
        info.setTextSize(15);
        body.addView(info);
        usageChoice = choice(body, "Requested audio usage", LABELS);
        channelChoice = choice(body, "Source channels", new String[]{"Stereo", "Left only", "Right only"});
        focusChoice = choice(body, "Audio focus", new String[]{"Gain / hold focus", "Transient", "Transient, may duck others"});
        levelLabel = new TextView(this);
        body.addView(levelLabel);
        level = new SeekBar(this);
        level.setMax(19);
        level.setProgress(4);
        updateLevelLabel();
        level.setOnSeekBarChangeListener(new SeekBar.OnSeekBarChangeListener() {
            public void onProgressChanged(SeekBar bar, int value, boolean fromUser) { updateLevelLabel(); }
            public void onStartTrackingTouch(SeekBar bar) {}
            public void onStopTrackingTouch(SeekBar bar) {}
        });
        body.addView(level);
        LinearLayout actions = new LinearLayout(this);
        actions.setGravity(Gravity.CENTER_VERTICAL);
        addButton(actions, "Play 8 seconds", () -> begin(8));
        addButton(actions, "Hold until Stop", () -> begin(0));
        addButton(actions, "Stop", () -> stop("Stopped by operator"));
        body.addView(actions);
        status = new TextView(this);
        status.setTextSize(16);
        status.setPadding(0, dp(12), 0, 0);
        status.setTextIsSelectable(true);
        body.addView(status);
        setContentView(scroll);
        refresh();
    }

    private int dp(int value) { return (int) (value * getResources().getDisplayMetrics().density + .5f); }
    private Spinner choice(LinearLayout body, String label, String[] options) {
        TextView caption = new TextView(this);
        caption.setText(label);
        caption.setTextSize(16);
        caption.setPadding(0, dp(10), 0, 0);
        body.addView(caption);
        Spinner spinner = new Spinner(this);
        ArrayAdapter<String> adapter = new ArrayAdapter<>(this,
                android.R.layout.simple_spinner_item, options);
        adapter.setDropDownViewResource(android.R.layout.simple_spinner_dropdown_item);
        spinner.setAdapter(adapter);
        body.addView(spinner, new LinearLayout.LayoutParams(-1, dp(48)));
        return spinner;
    }
    private void addButton(LinearLayout parent, String text, Runnable action) {
        Button button = new Button(this);
        button.setText(text);
        button.setOnClickListener(v -> action.run());
        parent.addView(button, new LinearLayout.LayoutParams(0, dp(54), 1));
    }
    private void updateLevelLabel() {
        levelLabel.setText("Signal amplitude: " + (level.getProgress() + 1)
                + "% peak (does not change radio volume)");
    }

    private final AudioManager.OnAudioFocusChangeListener focusListener = change -> {
        Log.i(TAG, "focus_change=" + change);
        Playback current = playback;
        if (change == AudioManager.AUDIOFOCUS_LOSS || change == AudioManager.AUDIOFOCUS_LOSS_TRANSIENT) {
            stop("Stopped after focus loss " + change);
        } else if (current != null) {
            current.duck = change == AudioManager.AUDIOFOCUS_LOSS_TRANSIENT_CAN_DUCK;
            last = "Focus change " + change + (current.duck ? " (ducked)" : "");
            refresh();
        }
    };

    private void begin(int seconds) {
        if (!foreground) return;
        stop("Starting new probe");
        lastDetails = "";
        final int index = usageChoice.getSelectedItemPosition();
        int content = (index == 1 || index == 2 || index == 3 || index == 14)
                ? AudioAttributes.CONTENT_TYPE_SPEECH
                : (index == 0 || index == 15) ? AudioAttributes.CONTENT_TYPE_MUSIC : AudioAttributes.CONTENT_TYPE_SONIFICATION;
        try {
            AudioAttributes.Builder builder = new AudioAttributes.Builder().setContentType(content);
            if (index >= 16) {
                // Use the system setter when available; never substitute UNKNOWN or bypass policy.
                AudioAttributes.Builder.class.getMethod("setSystemUsage", int.class)
                        .invoke(builder, USAGES[index]);
            } else {
                builder.setUsage(USAGES[index]);
            }
            AudioAttributes attrs = builder.build();
            int effectiveUsage = index >= 16
                    ? (Integer) AudioAttributes.class.getMethod("getSystemUsage").invoke(attrs)
                    : attrs.getUsage();
            focusRequest = new AudioFocusRequest.Builder(GAINS[focusChoice.getSelectedItemPosition()])
                    .setAudioAttributes(attrs).setOnAudioFocusChangeListener(focusListener, main)
                    .setAcceptsDelayedFocusGain(false).setWillPauseWhenDucked(false).build();
            int result = audio.requestAudioFocus(focusRequest);
            Log.i(TAG, "focus_result=" + result + " usage=" + KEYS[index] + " usage_id=" + USAGES[index] + " effective_usage=" + effectiveUsage);
            if (result != AudioManager.AUDIOFOCUS_REQUEST_GRANTED) {
                stop("Focus was not granted (result " + result + "); no signal played");
                return;
            }
            Playback next = new Playback(index, channelChoice.getSelectedItemPosition(),
                    (level.getProgress() + 1) / 100.0, seconds, attrs);
            playback = next;
            last = "Focus granted; starting " + KEYS[index];
            getWindow().addFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON);
            next.thread.start();
            main.post(ticker);
            refresh();
        } catch (ReflectiveOperationException | RuntimeException e) {
            Throwable cause = e.getCause() == null ? e : e.getCause();
            String error = "Could not start: " + cause.getClass().getSimpleName() + ": " + cause.getMessage();
            Log.e(TAG, "usage=" + KEYS[index] + " " + error);
            stop(error);
        }
    }

    private void stop(String reason) {
        Playback old = playback;
        playback = null;
        if (old != null) {
            old.running = false;
            old.thread.interrupt();
            lastDetails = details(old);
        }
        if (focusRequest != null) {
            audio.abandonAudioFocusRequest(focusRequest);
            focusRequest = null;
        }
        getWindow().clearFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON);
        main.removeCallbacks(ticker);
        last = reason;
        Log.i(TAG, "stop=" + reason);
        refresh();
    }

    private final Runnable ticker = new Runnable() {
        @Override public void run() {
            if (playback != null) {
                refresh();
                main.postDelayed(this, 500);
            }
        }
    };

    private void refresh() {
        if (status == null) return;
        Playback current = playback;
        status.setText(last + (current == null ? lastDetails : details(current)));
    }

    private String details(Playback current) {
        return "\nRequested: " + LABELS[current.index] + " (usage " + USAGES[current.index] + ")"
                + "\nSignal: " + FREQUENCIES[current.index] + " Hz, 500 ms on / 250 ms off"
                + "\nPCM: 48 kHz, 16-bit, stereo; " + (current.seconds == 0 ? "hold until Stop" : current.seconds + " seconds")
                + "\nRoute: " + current.route
                + "\nAudioTrack session: " + current.audioSession
                + "\nWritten: " + current.framesWritten + " frames; underruns: " + current.underruns
                + (current.duck ? "\nDucked following focus request" : "");
    }

    private static String routeName(AudioTrack track) {
        AudioDeviceInfo device = track.getRoutedDevice();
        if (device == null) return "pending";
        String address = device.getAddress();
        if (address == null || !address.matches("bus[0-9]+_[a-zA-Z0-9_]+")) address = "<non-bus or unspecified>";
        return "type=" + device.getType() + ", id=" + device.getId() + ", " + address;
    }

    private final class Playback implements Runnable {
        final int index, channels, seconds;
        final double amplitude;
        final AudioAttributes attrs;
        final Thread thread;
        volatile boolean running = true, duck;
        volatile long framesWritten;
        volatile int audioSession, underruns;
        volatile String route = "pending";
        Playback(int index, int channels, double amplitude, int seconds, AudioAttributes attrs) {
            this.index = index; this.channels = channels; this.amplitude = amplitude;
            this.seconds = seconds; this.attrs = attrs;
            thread = new Thread(this, "AudioUsageProbePCM");
        }
        @Override public void run() {
            AudioTrack track = null;
            String ending = "Playback completed";
            try {
                try { android.os.Process.setThreadPriority(android.os.Process.THREAD_PRIORITY_AUDIO); }
                catch (SecurityException ignored) {}
                int minimum = AudioTrack.getMinBufferSize(RATE, AudioFormat.CHANNEL_OUT_STEREO,
                        AudioFormat.ENCODING_PCM_16BIT);
                if (minimum <= 0) throw new IllegalStateException("No supported 48 kHz stereo buffer");
                track = new AudioTrack.Builder().setAudioAttributes(attrs)
                        .setAudioFormat(new AudioFormat.Builder().setSampleRate(RATE)
                                .setEncoding(AudioFormat.ENCODING_PCM_16BIT)
                                .setChannelMask(AudioFormat.CHANNEL_OUT_STEREO).build())
                        .setTransferMode(AudioTrack.MODE_STREAM).setBufferSizeInBytes(Math.max(minimum, RATE / 10 * 4))
                        .build();
                if (track.getState() != AudioTrack.STATE_INITIALIZED) throw new IllegalStateException("AudioTrack not initialized");
                audioSession = track.getAudioSessionId();
                track.addOnRoutingChangedListener((AudioRouting.OnRoutingChangedListener) changed -> {
                    if (playback == this && running) main.post(tickerRefresh);
                }, main);
                track.play();
                Log.i(TAG, "play usage=" + KEYS[index] + " hz=" + FREQUENCIES[index]
                        + " session=" + audioSession + " amplitude=" + amplitude);
                byte[] data = new byte[BLOCK * 4];
                long generated = 0;
                long limit = seconds == 0 ? Long.MAX_VALUE : (long) seconds * RATE;
                int offset = 0, remaining = 0, chunk = 0;
                String previousRoute = "";
                while (running && generated < limit) {
                    if (remaining == 0) {
                        chunk = (int) Math.min(BLOCK, limit - generated);
                        for (int i = 0; i < chunk; i++) {
                            long frame = generated + i;
                            int position = (int) (frame % 36000);
                            double envelope = position >= 24000 ? 0
                                    : Math.min(1.0, Math.min(position / 240.0, (23999 - position) / 240.0));
                            int sample = (int) (Math.sin(2 * Math.PI * FREQUENCIES[index] * (frame % RATE) / RATE)
                                    * 32767 * amplitude * envelope);
                            int left = channels == 2 ? 0 : sample;
                            int right = channels == 1 ? 0 : sample;
                            int at = i * 4;
                            data[at] = (byte) left; data[at + 1] = (byte) (left >> 8);
                            data[at + 2] = (byte) right; data[at + 3] = (byte) (right >> 8);
                        }
                        offset = 0; remaining = chunk * 4;
                    }
                    track.setVolume(duck ? .2f : 1f);
                    int written = track.write(data, offset, remaining, AudioTrack.WRITE_NON_BLOCKING);
                    if (written < 0) throw new IllegalStateException("AudioTrack write returned " + written);
                    if (written == 0) { Thread.sleep(2); continue; }
                    framesWritten += written / 4;
                    offset += written; remaining -= written;
                    if (remaining == 0) generated += chunk;
                    route = routeName(track);
                    underruns = track.getUnderrunCount();
                    if (!route.equals(previousRoute)) {
                        previousRoute = route;
                        Log.i(TAG, "route usage=" + KEYS[index] + " " + route);
                    }
                }
                long deadline = android.os.SystemClock.elapsedRealtime() + 2000;
                while (running && (track.getPlaybackHeadPosition() & 0xffffffffL) < framesWritten
                        && android.os.SystemClock.elapsedRealtime() < deadline) Thread.sleep(5);
            } catch (InterruptedException e) {
                ending = "Playback stopped";
            } catch (RuntimeException e) {
                ending = "Playback error: " + e.getClass().getSimpleName() + ": " + e.getMessage();
                Log.e(TAG, ending);
            } finally {
                running = false;
                if (track != null) {
                    try { track.stop(); } catch (IllegalStateException ignored) {}
                    track.release();
                }
                final String result = ending;
                Log.i(TAG, "finished usage=" + KEYS[index] + " frames=" + framesWritten + " " + result);
                main.post(() -> { if (playback == this) stop(result); });
            }
        }
    }

    private final Runnable tickerRefresh = this::refresh;

    private void handleCommand(Intent intent) {
        int generation = ++commandGeneration;
        if (intent == null) return;
        if ("stop".equals(intent.getStringExtra("command"))) { stop("Stopped by command"); return; }
        int channel = intent.getIntExtra("channel", -1);
        if (channel >= 0 && channel <= 2) channelChoice.setSelection(channel);
        String key = intent.getStringExtra("usage");
        if (key != null) for (int i = 0; i < KEYS.length; i++) if (KEYS[i].equals(key)) usageChoice.setSelection(i);
        if (intent.getBooleanExtra("autoplay", false)) {
            int seconds = Math.max(1, Math.min(30, intent.getIntExtra("seconds", 8)));
            main.postDelayed(() -> { if (generation == commandGeneration && foreground) begin(seconds); }, 400);
        }
    }
    @Override protected void onNewIntent(Intent intent) {
        super.onNewIntent(intent); setIntent(intent); handleCommand(intent);
    }
    @Override protected void onResume() { super.onResume(); foreground = true; }
    @Override protected void onPause() {
        foreground = false; commandGeneration++; stop("Stopped when screen left foreground"); super.onPause();
    }
}
