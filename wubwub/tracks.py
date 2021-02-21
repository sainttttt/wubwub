#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Feb  9 10:10:34 2021

@author: earnestt1234
"""

from abc import ABCMeta, abstractmethod
from collections.abc import Iterable
import itertools
from numbers import Number
import os
import warnings

import numpy as np
import pprint
import pydub
from pydub.playback import play
from sortedcontainers import SortedDict

from wubwub.audio import add_note_to_audio, add_effects
from wubwub.errors import WubWubError, WubWubWarning
from wubwub.notes import ArpChord, Chord, Note, arpeggiate, chordify
from wubwub.resources import random_choice_generator, MINUTE

class Track(metaclass=ABCMeta):

    handle_new_notes = 'skip'

    def __init__(self, name, sample, sequencer, basepitch='C4'):
        self.basepitch = basepitch
        self.effects = None
        self.notes = SortedDict()
        self.samplepath = None

        self._name = None
        self._sample = None
        self._sequencer = None
        self.sequencer = sequencer
        self.name = name
        self.sample = sample

    def __repr__(self):
        return f'GenericTrack(name="{self.name}", sample="{self.samplepath}")'

    @property
    def sequencer(self):
        return self._sequencer

    @sequencer.setter
    def sequencer(self, sequencer):
        if self._name in sequencer.tracknames():
            raise WubWubError(f'name "{self._name}" already in use by new sequencer')

        if self._sequencer is not None:
            self._sequencer.delete_track(self)
        self._sequencer = sequencer
        self._sequencer._trackmanager.add_track(self)
        if sequencer.handle_new_track_notes == 'clean':
            self.clean()

    @property
    def name(self):
        return self._name

    @name.setter
    def name(self, new):
        if new in self.sequencer.tracknames():
            raise WubWubError(f'track name "{new}" already in use.')
        self._name = new

    @property
    def sample(self):
        return self._sample

    @sample.setter
    def sample(self, sample):
        if isinstance(sample, str):
            self._sample = pydub.AudioSegment.from_wav(sample)
            self.samplepath = os.path.abspath(sample)
        elif isinstance(sample, pydub.AudioSegment):
            self._sample = sample
        else:
            raise WubWubError('sample must be a path or pydub.AudioSegment')

    def _insert_note(self, beat, new, merge=False):
        existing = self.notes.get(beat, None)
        if existing and merge:
            new = chordify(existing, new)
        self.notes[beat] = new


    def add_notes_from_dict(self, d, outsiders=None, merge=False):
        method = self.handle_new_notes if outsiders is None else outsiders
        options = ['skip', 'add', 'warn', 'raise']

        if method not in options:
            w = ('`method` not recognized, '
                 'defaulting to "skip".',)
            warnings.warn(w, WubWubWarning)

        if method == 'add':
            for k, v in d.items():
                self._insert_note(k, v, merge)
        if method == 'warn':
            beats = self.get_beats()
            for k, v in d.items():
                if k >= beats + 1:
                    s = ("Added note on beat beyond the "
                         "sequencer's length.  See `handle_new_notes` "
                         "in class docstring for `wb.Track` to toggle "
                         "this behavior.")
                    warnings.warn(s, WubWubWarning)
                self._insert_note(k, v, merge)
        if method == 'raise':
            beats = self.get_beats()
            for k, v in d.items():
                if k < beats + 1:
                    self._insert_note(k, v, merge)
                else:
                    s = ("Tried to add note on beat beyond the "
                         "sequencer's length.  See `handle_new_notes` "
                         "in class docstring for `wb.Track` to toggle "
                         "this behavior.")
                    raise WubWubError(s)
        else:
            beats = self.get_beats()
            for k, v in d.items():
                if k < beats + 1:
                    self._insert_note(k, v, merge)


    def get_bpm(self):
        return self.sequencer.bpm

    def get_beats(self):
        return self.sequencer.beats

    def pprint_notes(self):
        pprint.pprint(self.notes)

    def clean(self):
        maxi = self.get_beats()
        self.notes = SortedDict({b:note for b, note in self.notes.items()
                                 if b < maxi +1})

    def delete_all_notes(self):
        self.notes = SortedDict({})

    def delete_single_note(self, beat):
        del self.notes[beat]

    def delete_range_notes(self, lo, hi):
        self.notes = SortedDict({b:note for b, note in self.notes.items()
                                 if not lo <= b < hi+1})

    def unpack_notes(self):
        unpacked = []
        for b, element in self.notes.items():
            if isinstance(element, Note):
                unpacked.append((b, element))
            elif type(element) in [Chord, ArpChord]:
                for note in element.notes:
                    unpacked.append((b, note))
        return unpacked

    @abstractmethod
    def build(self):
        pass

    def play(self, overhang=0, overhang_type='beats'):
        play(self.build(overhang, overhang_type))

class Sampler(Track):
    def __init__(self, name, sample, sequencer, basepitch='C4', overlap=True):
        super().__init__(name, sample, sequencer, basepitch)
        self.overlap = overlap

    def __repr__(self):
        return f'Sampler(name="{self.name}", sample="{self.samplepath}")'

    def add_notes(self, beat, pitch=0, length=1, volume=0,
                  pitch_select='cycle', length_select='cycle',
                  volume_select='cycle', merge=False):

        if not isinstance(beat, Iterable):
            beat = [beat]

        pitch = self._convert_select_arg(pitch, pitch_select)
        length = self._convert_select_arg(length, length_select)
        volume = self._convert_select_arg(volume, volume_select)

        d = {b : Note(next(pitch), next(length), next(volume))
             for b in beat}

        self.add_notes_from_dict(d, merge=merge)

    def add_notes_every(self, freq, offset=0, pitch=0, length=1, volume=0,
                        pitch_select='cycle', length_select='cycle',
                        volume_select='cycle', merge=False):

        pitch = self._convert_select_arg(pitch, pitch_select)
        length = self._convert_select_arg(length, length_select)
        volume = self._convert_select_arg(volume, volume_select)

        b = 1 + offset
        d = {}
        while b < self.get_beats() + 1:
            d[b] = Note(next(pitch), next(length), next(volume))
            b += freq

        self.add_notes_from_dict(d, merge=merge)

    def add_chord(self, beat, pitches, lengths=1, volumes=0, merge=False):

        if not isinstance(beat, Iterable):
            beat = [beat]

        if not isinstance(pitches, Iterable) or isinstance(pitches, str):
            pitches = [pitches]

        if isinstance(lengths, Number):
            lengths = [lengths] * len(pitches)

        if isinstance(volumes, Number):
            volumes = [volumes] * len(pitches)

        notes = [Note(p, l, v) for p, l, v in zip(pitches, lengths, volumes)]

        d = {b : Chord(notes) for b in beat}

        self.add_notes_from_dict(d, merge=merge)

    def _convert_select_arg(self, arg, option):
        if not isinstance(arg, Iterable) or isinstance(arg, str):
            arg = [arg]

        if option == 'cycle':
            return itertools.cycle(arg)
        elif option == 'random':
            return random_choice_generator(arg)
        else:
            raise WubWubError('pitch, length, and volume select must be ',
                              '"cycle" or "random".')

    def build(self, overhang=0, overhang_type='beats'):
        b = (1/self.get_bpm()) * MINUTE
        if overhang_type == 'beats':
            overhang = b * overhang
        elif overhang_type in ['s', 'seconds']:
            overhang = overhang * 1000
        else:
            raise WubWubError('overhang must be "beats" or "s"')
        tracklength = self.get_beats() * b + overhang
        audio = pydub.AudioSegment.silent(duration=tracklength)
        sample = self.sample
        basepitch = self.basepitch
        next_position = np.inf
        for beat, value in sorted(self.notes.items(), reverse=True):
            position = (beat-1) * b
            if isinstance(value, Note):
                note = value
                duration = note.length * b
                if (position + duration) > next_position and not self.overlap:
                    duration = next_position - position
                next_position = position
                audio = add_note_to_audio(note=note,
                                          audio=audio,
                                          sample=sample,
                                          position=position,
                                          duration=duration,
                                          basepitch=basepitch)
            elif isinstance(value, Chord):
                chord = value
                for note in chord.notes:
                    duration = note.length * b
                    if (position + duration) > next_position and not self.overlap:
                        duration = next_position - position
                    audio = add_note_to_audio(note=note,
                                              audio=audio,
                                              sample=sample,
                                              position=position,
                                              duration=duration,
                                              basepitch=basepitch)
                next_position = position


        if self.effects:
            audio = add_effects(audio, self.effects)
        return audio

class Arpeggiator(Track):
    def __init__(self, name, sample, sequencer, basepitch='C4', freq=.5,
                 method='up'):
        super().__init__(name, sample, sequencer, basepitch)
        self.freq = freq
        self.method = method

    def __repr__(self):
        return (f'Arpeggiator(name="{self.name}", sample="{self.samplepath}", ' +
                f'freq={self.freq}, method="{self.method}")')

    def add_chord(self, beat, pitches, length=1, merge=False):
        notes = [Note(p) for p  in pitches]

        if not isinstance(beat, Iterable):
            beat = [beat]

        d = {b: ArpChord(notes, length) for b in beat}

        self.add_notes_from_dict(d, merge=merge)

    def build(self, overhang=0, overhang_type='beats'):
        b = (1/self.get_bpm()) * MINUTE
        if overhang_type == 'beats':
            overhang = b * overhang
        elif overhang_type in ['s', 'seconds']:
            overhang = overhang * 1000
        else:
            raise WubWubError('overhang must be "beats" or "s"')
        tracklength = self.get_beats() * b + overhang
        audio = pydub.AudioSegment.silent(duration=tracklength)
        sample = self.sample
        basepitch = self.basepitch
        next_beat = np.inf
        for beat, chord in sorted(self.notes.items(), reverse=True):
            length = max(note.length for note in chord.notes)
            if beat + length > next_beat:
                length = next_beat - beat
            next_beat = beat
            arpeggiated = arpeggiate(chord, beat=beat,
                                     freq=self.freq, method=self.method)
            for arpbeat, note in arpeggiated.items():
                position = (arpbeat-1) * b
                duration = note.length * b
                audio = add_note_to_audio(note=note,
                                          audio=audio,
                                          sample=sample,
                                          position=position,
                                          duration=duration,
                                          basepitch=basepitch)

        if self.effects:
            audio = add_effects(audio, self.effects)
        return audio


class TrackManager:
    def __init__(self, sequencer):
        self._sequencer = sequencer
        self.tracks = []

    def get_track(self, track):
        if track in self.tracks:
            return track
        try:
            return next(t for t in self.tracks if t.name == track)
        except:
            raise StopIteration(f'no track with name {track}')

    def get_tracknames(self):
        return [t.name for t in self.tracks]

    def add_track(self, track):
        if track not in self.tracks:
            self.tracks.append(track)

    def delete_track(self, track):
        self.tracks.remove(self.get_track(track))