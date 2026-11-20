"""Sound effects and background music, synthesised in code (no audio files). Every call is a safe no-op when the mixer is missing
or ROGUE_SOUND=0 is set, so the game never depends on an audio device."""
import array, math, os, random
import pygame

ON = os.environ.get("ROGUE_SOUND", "1") != "0"
VOL_FX, VOL_MUSIC = 0.55, 0.22
_state = {"ok": None, "fx": {}, "music": {}, "now": None, "ch": None}
NOTE = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}


def _freq(name):
    """'A4' -> 440.0, 'C#5' -> ... (a rest is None)."""
    if name is None: return None
    n, octv = name[0], int(name[-1])
    semi = NOTE[n] + (1 if "#" in name else 0) + (octv - 4) * 12 - 9
    return 440.0 * 2 ** (semi / 12)


def _ready():
    if _state["ok"] is None:
        try:
            if not pygame.mixer.get_init(): pygame.mixer.init()
            _state["ok"] = bool(pygame.mixer.get_init()) and pygame.mixer.get_init()[1] == -16
        except pygame.error:
            _state["ok"] = False
    return _state["ok"] and ON


def _wave(kind, ph):
    ph -= math.floor(ph)
    if kind == "square": return 1.0 if ph < 0.5 else -1.0
    if kind == "tri": return 4 * abs(ph - 0.5) - 1
    return math.sin(2 * math.pi * ph)


def _tone(sr, f0, f1, dur, wave="square", vol=0.5, noise=0.0, decay=2.0):
    """Samples of a tone sweeping f0 -> f1 (Hz) with an exponential-ish decay. Mono floats."""
    n, ph, out = max(1, int(sr * dur)), 0.0, []
    for i in range(n):
        t = i / n
        ph += (f0 + (f1 - f0) * t) / sr
        w = _wave(wave, ph)
        if noise: w = (1 - noise) * w + noise * random.uniform(-1, 1)
        out.append(w * (1 - t) ** decay * vol)
    return out


def _to_sound(samples):
    """Mono float samples -> a pygame Sound in the mixer's own rate and channel count."""
    _, _, ch = pygame.mixer.get_init()
    buf = array.array("h")
    for v in samples:
        q = int(max(-1.0, min(1.0, v)) * 12000)
        buf.extend([q] * ch)
    return pygame.mixer.Sound(buffer=buf.tobytes())


def _sfx_samples(name, sr):
    T = lambda *a, **k: _tone(sr, *a, **k)
    if name == "menu": return T(660, 880, 0.05, vol=0.3, decay=1)
    if name == "select": return T(440, 880, 0.12, vol=0.35, decay=1)
    if name == "swing": return T(900, 200, 0.12, wave="tri", vol=0.4, noise=0.3)
    if name == "jump": return T(300, 700, 0.15, vol=0.3, decay=1)
    if name == "hit": return T(200, 60, 0.12, vol=0.6, noise=0.6)
    if name == "block": return T(1200, 900, 0.08, wave="tri", vol=0.4, noise=0.3)
    if name == "hurt": return T(500, 120, 0.25, vol=0.45)
    if name == "wave": return T(330, 495, 0.2, vol=0.35, decay=1)
    if name == "portal": return T(300, 1200, 0.5, wave="sine", vol=0.4, decay=1)
    if name == "boss": return T(110, 55, 0.6, vol=0.5, noise=0.2, decay=1)
    if name == "fail": return T(400, 150, 0.35, wave="tri", vol=0.4)
    if name == "loot":  # a quick rising arpeggio
        out = []
        for f in (523, 659, 784, 1046): out += T(f, f, 0.07, vol=0.35, decay=1)
        return out
    return []


# ---- background music: two short loops, a calm one for menus and a faster one for battles
TRACKS = {
    "menu": (96, ["A4", "C5", "E5", "C5", "G4", "B4", "D5", "B4", "F4", "A4", "C5", "A4", "E4", "G#4", "B4", "E5"],
             ["A2", None, "A2", None, "F2", None, "F2", None, "C3", None, "C3", None, "E2", None, "E2", None]),
    "battle": (150, ["E5", "E5", "G5", "E5", "D5", "B4", "D5", "B4", "C5", "E5", "G5", "E5", "A4", "C5", "E5", "A5"],
              ["E2", "E2", "E2", "E2", "D2", "D2", "D2", "D2", "C2", "C2", "C2", "C2", "A1", "A1", "A1", "A1"]),
}


def _music_sound(name):
    sr = pygame.mixer.get_init()[0]
    bpm, lead, bass = TRACKS[name]
    beat = 60 / bpm
    total = int(len(lead) * beat * sr)
    mix = [0.0] * total
    for notes, wave, vol in ((lead, "square", 0.5), (bass, "tri", 0.8)):
        pos = 0
        for nm in notes:
            n = int(beat * sr)
            f = _freq(nm)
            if f:
                for i, v in enumerate(_tone(sr, f, f, beat * 0.9, wave=wave, vol=vol, decay=0.6)): mix[pos + i] += v
            pos += n
    return _to_sound([v * 0.8 for v in mix])


def play(name):
    """Play one sound effect by name (see _sfx_samples). Does nothing if audio is off."""
    if not _ready(): return
    try:
        if name not in _state["fx"]:
            _state["fx"][name] = _to_sound(_sfx_samples(name, pygame.mixer.get_init()[0]))
            _state["fx"][name].set_volume(VOL_FX)
        _state["fx"][name].play()
    except (pygame.error, KeyError):
        pass


def music(name):
    """Switch the background loop to "menu" or "battle". Calling it again with the same track does nothing."""
    if not _ready() or name == _state["now"] or name not in TRACKS: return
    try:
        if name not in _state["music"]: _state["music"][name] = _music_sound(name)
        if _state["ch"]: _state["ch"].stop()
        _state["ch"] = _state["music"][name].play(loops=-1)
        _state["ch"].set_volume(VOL_MUSIC)
        _state["now"] = name
    except pygame.error:
        pass
