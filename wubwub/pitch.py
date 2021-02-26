#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Feb  9 10:13:16 2021

@author: earnestt1234
"""
from collections import deque
import re

import pandas as pd

# from wubwub.errors import WubWubError

NOTES = ['C' , 'C#', 'Db', 'D' , 'D#', 'Eb', 'E' , 'F', 'F#',
         'Gb', 'G' , 'G#', 'Ab', 'A' , 'A#', 'Bb', 'B',]
NOTES_JOIN = '|'.join(NOTES)
DIFF =  [0   , 1   , 1   , 2   , 3   , 3   , 4   , 5   , 6   ,
         6   , 7   , 8   , 8   , 9   , 10  , 10  , 11  ]

named_chords = (
    {''     : [0, 4, 7],
     'M'    : [0, 4, 7],
     'major': [0, 4, 7],
     'm'    : [0, 3, 7],
     'minor': [0, 3, 7],
     'maj7' : [0, 4, 7, 11],
     'min7' : [0, 3, 7, 10],})

chordnames_re = '|'.join(named_chords.keys())

DIFF_DEQUE = deque(DIFF)
DIFFDF = pd.DataFrame(index=NOTES, columns=NOTES,)

def valid_chord_str(s):
    pattern = f"^({NOTES_JOIN})({chordnames_re})$"
    return bool(re.match(pattern, s))

def valid_pitch_str(s):
    pattern = f"^({NOTES_JOIN})[0-9]$"
    return bool(re.match(pattern, s))

def int_to_relative_pitch(note, diff):
    octaves = 0 if diff == 0 else diff // 12
    posdiff = diff % 12 if diff > 0 else (12 + diff) % 12
    oldpitch, oldoct = splitoctave(note)
    idx_old = NOTES.index(oldpitch)
    idx_new = DIFF.index((idx_old + posdiff) % len(NOTES))
    newpitch = NOTES[idx_new]
    if idx_new < idx_old and diff > 0:
        octaves += 1
    if idx_new > idx_old and diff < 0:
        octaves -= 1
    return newpitch + str(oldoct + octaves)



def relative_pitch_to_int(a, b):
    pitch_a, octave_a = splitoctave(a)
    pitch_b, octave_b = splitoctave(b)
    octave_diff = octave_b - octave_a
    pitch_diff = DIFF[NOTES.index(pitch_b)] - DIFF[NOTES.index(pitch_a)]
    return pitch_diff + (12 * octave_diff)

def splitoctave(pitch_str, octave_type=int):
    if not valid_pitch_str(pitch_str):
        raise WubWubError(f'"{pitch_str}" is not a valid pitch string')
    return pitch_str[:-1], octave_type(pitch_str[-1])

def splitchordname(chord_str):
    if not valid_chord_str(chord_str):
        raise WubWubError(f'"{chord_str}" is not a valid chord string')
    if chord_str[1] in ['#, b']:
        return chord_str[:2], chord_str[2:]
    else:
        return chord_str[:1], chord_str[1:]

def shift_pitch(sound, semitones):
    octaves = (semitones/12)
    new_sample_rate = int(sound.frame_rate * (2.0 ** octaves))
    new_sound = sound._spawn(sound.raw_data, overrides={'frame_rate': new_sample_rate})
    new_sound = new_sound.set_frame_rate(44100)
    return new_sound