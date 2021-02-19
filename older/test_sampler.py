import librosa

import pydub
from pydub.playback import play

y, sr = librosa.load('trumpet.WAV')

second = 1000
minute = 60 * second
bpm = 120
mpb = (1/bpm) * minute

signature = (4,4)
measures = 4
total_beats = measures * signature[1]
total_length = mpb*total_beats

track1 = pydub.AudioSegment.silent(duration=total_length)
hihat = pydub.AudioSegment.from_wav('808/hi hat (1).wav')
snare = pydub.AudioSegment.from_wav('808/snare (1).wav')
kick = pydub.AudioSegment.from_wav('808/kick (11).wav')
sound = pydub.AudioSegment.from_file('trumpet.wav', format="wav")
sound = sound - 10

for i in range(0, int(total_length), int(mpb)):
    track1 = track1.overlay(hihat, position=i)

for i in range(1000, int(total_length), 4*int(mpb)):
    track1 = track1.overlay(snare, position=i)

for i in [0, 100, 250, 1750, 2500]:
    track1 = track1.overlay(kick, position=i)

for n, i in enumerate(range(0, int(total_length), int(mpb))):
    octaves = 1 + (n/12)
    new_sample_rate = int(sound.frame_rate * (2.0 ** octaves))
    new_sound = sound._spawn(sound.raw_data, overrides={'frame_rate': new_sample_rate})
    new_sound = new_sound.set_frame_rate(44100)
    track1 = track1.overlay(new_sound[:500], position=i)

play(track1)
