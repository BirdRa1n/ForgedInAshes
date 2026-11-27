"""Machine sound loops for ForgedInAshes, synthesized from scratch (original, no third-party audio).

Every sound is a seamless loop: noise is built in the frequency domain (periodic by construction), tones are
rounded to whole cycles of the loop length and repeating events are placed a whole number of times per loop.
Output: Art/feSounds/<name>.wav (mono, 44.1 kHz, 16 bit). FeBuild puts them in the asset bundle; Config/sounds.xml
declares the SoundDataNodes; src/ForgedInAshes/MachineSound.cs plays them while a machine runs.

    python Art/feSounds/make_sounds.py
"""
import os
import wave

import numpy as np

SR = 44100
OUT = os.path.dirname(os.path.abspath(__file__))


def tt(T):
    return np.arange(int(T * SR)) / SR


def band(T, lo, hi, rng, tilt=0.0, soft=0.25):
    """Periodic band-limited noise (lo..hi Hz, soft edges, spectral tilt in dB/octave), unit RMS."""
    n = int(T * SR)
    f = np.fft.rfftfreq(n, 1 / SR)
    mag = np.zeros_like(f)
    ok = f > 0
    lo_e, hi_e = lo * (1 - soft), hi * (1 + soft)
    w = np.clip((f - lo_e) / max(lo - lo_e, 1e-6), 0, 1) * np.clip((hi_e - f) / max(hi_e - hi, 1e-6), 0, 1)
    mag[ok] = w[ok] * (f[ok] / max(lo, 1.0)) ** (tilt / 6.02)
    spec = mag * np.exp(2j * np.pi * rng.random(len(f)))
    x = np.fft.irfft(spec, n)
    return x / (np.sqrt(np.mean(x ** 2)) + 1e-9)


def tone(T, f, harm=(1.0,), phase=0.0):
    t = tt(T)
    fq = round(f * T) / T                                   # whole cycles in the loop
    x = np.zeros_like(t)
    for k, a in enumerate(harm, 1):
        x += a * np.sin(2 * np.pi * fq * k * t + phase * k)
    return x


def lfo(T, f, depth, base=1.0):
    fq = max(1, round(f * T)) / T
    return base + depth * np.sin(2 * np.pi * fq * tt(T))


def events(T, times, make, n_len):
    """Adds the signal make(k) (n_len samples) at each time, wrapping round the loop end."""
    n = int(T * SR)
    x = np.zeros(n)
    for k, t0 in enumerate(times):
        e = make(k)[:n_len]
        i0 = int((t0 + 0.013) * SR) % n                     # never right on the loop seam
        idx = (np.arange(len(e)) + i0) % n
        np.add.at(x, idx, e)
    return x


def decay(n, tau):
    """Exponential decay with a 2 ms attack (no click at the onset)."""
    e = np.exp(-np.arange(n) / (tau * SR))
    a = min(n, int(0.002 * SR))
    e[:a] *= np.linspace(0.0, 1.0, a)
    return e


def ping(freqs, tau, rng, n):
    t = np.arange(n) / SR
    return sum(np.sin(2 * np.pi * f * t + rng.random() * 6.28) / (i + 1) for i, f in enumerate(freqs)) * decay(n, tau)


def burst(rng, n, tau, lo, hi):
    x = rng.standard_normal(n)
    X = np.fft.rfft(x)
    f = np.fft.rfftfreq(n, 1 / SR)
    X[(f < lo) | (f > hi)] = 0
    return np.fft.irfft(X, n) * decay(n, tau)


def save(name, x, peak=0.70):
    x = x - np.mean(x)
    x = x / (np.max(np.abs(x)) + 1e-9) * peak
    data = (np.clip(x, -1, 1) * 32767).astype(np.int16)
    with wave.open(os.path.join(OUT, name + ".wav"), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(data.tobytes())
    print("[sound]", name, f"{len(x) / SR:.2f}s")


def make_all():
    r = np.random.default_rng(1901)
    # --- Steam Turbine: a high rotor whine (with blade-pass tone), steam rush and a low rumble
    T = 6.0
    whine = tone(T, 410, (1.0, 0.35, 0.18, 0.08)) * lfo(T, 0.33, 0.06)
    blade = tone(T, 1640, (1.0, 0.3)) * 0.18 * lfo(T, 0.5, 0.3)
    rush = band(T, 1800, 9000, r, tilt=-3) * 0.35
    rumble = band(T, 30, 140, r) * 0.6
    save("fe_turbine_lp", whine * 0.45 + blade + rush + rumble)
    # --- Steam / coal engine: two exhaust chuffs and a rod knock per turn (2.25 turns / s), rumble under it
    T, rev = 4.0, 2.25
    n_turns = int(T * rev)
    chuffs = events(T, [k / (2 * rev) for k in range(2 * n_turns)],
                    lambda k: burst(r, 9000, 0.07, 250, 3500) * (1.0 if k % 2 == 0 else 0.75), 9000)
    knock = events(T, [k / rev + 0.09 for k in range(n_turns)], lambda k: ping((620, 1310, 2420), 0.045, r, 4000), 4000)
    save("fe_engine_lp", chuffs * 0.9 + knock * 0.5 + band(T, 25, 160, r) * 0.35 + band(T, 700, 2500, r) * 0.05)
    # --- Steam hiss (safety valve blowing off, relief valve): a strong broadband hiss that flutters
    T = 5.0
    save("fe_steam_hiss_lp", band(T, 1200, 12000, r, tilt=-1.5) * lfo(T, 3.6, 0.10) + band(T, 300, 1200, r) * 0.25)
    # --- Electric motor / dynamo: mains hum with harmonics, magnetic whine, bearing noise
    T = 4.0
    hum = tone(T, 100, (1.0, 0.5, 0.35, 0.2, 0.12, 0.08))
    save("fe_motor_lp", hum * 0.6 + tone(T, 2350, (1.0,)) * 0.08 * lfo(T, 0.5, 0.4) + band(T, 2000, 7000, r) * 0.12
         + band(T, 60, 300, r) * 0.25)
    # --- Gearbox / transmission: tooth-mesh tone amplitude-modulated by the shaft, soft rattle
    T = 4.0
    mesh = tone(T, 540, (1.0, 0.6, 0.4, 0.25)) * lfo(T, 18, 0.35)
    rattle = events(T, sorted(r.random(40) * T), lambda k: ping((1800 + 600 * r.random(), 3100), 0.012, r, 1500) * (0.4 + 0.6 * r.random()), 1500)
    save("fe_gear_lp", mesh * 0.35 + rattle * 0.35 + band(T, 80, 400, r) * 0.35)
    # --- Crusher / mill: grinding noise that surges, low thumps, stone cracks
    T = 5.0
    grind = band(T, 120, 2400, r, tilt=-2) * lfo(T, 1.4, 0.35)
    thumps = events(T, [k * 0.625 for k in range(8)], lambda k: np.sin(2 * np.pi * 62 * np.arange(8000) / SR) * decay(8000, 0.09), 8000)
    cracks = events(T, sorted(r.random(18) * T), lambda k: burst(r, 2500, 0.015, 1500, 9000), 2500)
    save("fe_crusher_lp", grind * 0.55 + thumps * 0.9 + cracks * 0.5)
    # --- Industrial fan / blower: air rush with blade-pass beating
    T = 4.0
    save("fe_fan_lp", band(T, 200, 1800, r, tilt=-2) * lfo(T, 14, 0.18) + band(T, 1800, 6000, r) * 0.25 + band(T, 40, 160, r) * 0.3)
    # --- Pump: piston strokes (water slosh + valve thunk) over a motor hum
    T, spm = 4.0, 1.5
    strokes = events(T, [k / spm for k in range(int(T * spm))], lambda k: burst(r, 20000, 0.18, 150, 1200), 20000)
    thunk = events(T, [k / spm + 0.33 for k in range(int(T * spm))], lambda k: ping((140, 380), 0.05, r, 5000), 5000)
    save("fe_pump_lp", strokes * 0.8 + thunk * 0.6 + tone(T, 100, (1.0, 0.4)) * 0.15 + band(T, 50, 200, r) * 0.2)
    # --- Conveyor belt: a soft rumble and roller clicks
    T = 4.0
    clicks = events(T, [k * 0.25 + 0.02 * r.random() for k in range(16)], lambda k: ping((900, 2200), 0.01, r, 1200) * (0.5 + 0.5 * r.random()), 1200)
    save("fe_belt_lp", band(T, 60, 500, r) * 0.45 + clicks * 0.35 + band(T, 800, 3000, r) * 0.06)
    # --- Bubbling (biodigester, fermenter): random rising blips over a low liquid murmur
    T = 6.0

    def blip(k):
        n = 3500
        t = np.arange(n) / SR
        f0 = 250 + 500 * r.random()
        return np.sin(2 * np.pi * (f0 * t + 900 * t * t)) * decay(n, 0.025)
    save("fe_bubble_lp", events(T, sorted(r.random(26) * T), blip, 3500) * 0.8 + band(T, 80, 600, r) * 0.25)
    # --- Mechanical drill: a high whine with chatter and rock grinding
    T = 4.0
    save("fe_drill_lp", tone(T, 980, (1.0, 0.4, 0.2)) * lfo(T, 22, 0.25) * 0.35 + band(T, 400, 5000, r, tilt=-2) * 0.5
         + band(T, 40, 200, r) * 0.3)
    # --- Mechanical saw: a blade whine and the cut noise
    T = 4.0
    save("fe_saw_lp", tone(T, 1450, (1.0, 0.5, 0.3, 0.15)) * 0.3 * lfo(T, 0.75, 0.1) + band(T, 1500, 9000, r, tilt=-1) * 0.45
         + band(T, 80, 300, r) * 0.2)
    # --- Press / stamping: a heavy stroke every 1.25 s (thump + metal clank + hiss)
    T = 5.0
    stroke = events(T, [k * 1.25 for k in range(4)], lambda k: np.sin(2 * np.pi * 52 * np.arange(12000) / SR) * decay(12000, 0.12), 12000)
    clank = events(T, [k * 1.25 + 0.01 for k in range(4)], lambda k: ping((410, 1180, 2650, 3900), 0.08, r, 9000), 9000)
    hiss = events(T, [k * 1.25 + 0.55 for k in range(4)], lambda k: burst(r, 16000, 0.12, 1500, 8000), 16000)
    save("fe_press_lp", stroke * 1.0 + clank * 0.6 + hiss * 0.25 + band(T, 60, 300, r) * 0.15)
    # --- Electric buzz (induction furnace, welder, electric heaters): 100 Hz rich buzz, crackle
    T = 4.0
    buzz = np.sign(tone(T, 100, (1.0,))) * 0.3 + tone(T, 100, (1.0, 0.7, 0.5, 0.4, 0.3, 0.2, 0.15))
    crackle = events(T, sorted(r.random(30) * T), lambda k: burst(r, 600, 0.004, 2000, 12000), 600)
    save("fe_buzz_lp", buzz * 0.4 + crackle * 0.3 + band(T, 3000, 9000, r) * 0.06)


if __name__ == "__main__":
    make_all()
