#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Notes are objects representing musical notes in wubwub.  They are akin to
MIDI notes in a real DAW; they are used to tell Tracks what musical notes
should be played (specifically their pitch, length, and volume).  Note that
the placement of Notes (the beat they are on) is not referenced within the Note
class; that is specified within each Track.

The Note is a single atomic note with a pitch, length, and volume.  Notes can
be combined to create Chords (basically a collection of Notes).  There are also
ArpChords, which are similar to Chords, but are intended to be specifically
used by the `wubwub.tracks.Arpeggiator`.

.. include:: ../docs/notes.md

"""

__all__ = ['Note', 'Chord', 'ArpChord', 'arpeggiate',
           'alter_notes', 'new_chord', 'chord_from_name']

from collections.abc import Iterable
from fractions import Fraction
from itertools import cycle, chain
from sortedcontainers import SortedList

from wubwub.errors import WubWubError
from wubwub.pitch import named_chords, pitch_from_semitones, relative_pitch_to_int
from wubwub.resources import random_choice_generator

class Note(object):
    '''Class to represent an atomic MIDI-like note in wubwub.'''
    __slots__ = ('pitch', 'length', 'volume')

    def __init__(self, pitch=0, length=1, volume=0):
        '''
        Initialize the note.

        Parameters
        ----------
        pitch : number or str, optional
            Relative pitch in semitones or scientific pitch string.
            The default is 0.
        length : number, optional
            The length of the note in beats. The default is 1.  The
            actual length in seconds is determined by the BPM
            of the Sequencer.
        volume : number, optional
            Relative amount of decibels to change the volume of the
            sample. The default is 0.

        Returns
        -------
        None.

        '''
        object.__setattr__(self, "pitch", pitch)
        object.__setattr__(self, "length", length)
        object.__setattr__(self, "volume", volume)

    def __setattr__(self, *args):
        '''Lock setting of attributes for Notes.'''
        name = self.__class__.__name__
        raise AttributeError(f"'{name}' object doesn't support item assignment")

    def __delattr__(self, *args):
        '''Lock deleting of attributes for Notes.'''
        name = self.__class__.__name__
        raise AttributeError(f"'{name}' object doesn't support item deletion")

    def __repr__(self):
        '''The string representation of the Note.'''
        attribs = ('pitch', 'length', 'volume')
        output = ', '.join([a + '=' + str(getattr(self, a)) for a in attribs])
        return f'Note({output})'

    def __eq__(self, other):
        '''Check if the other object is a Note where the pitch, length,
        and volume are equal.'''
        try:
            return all((self.pitch == other.pitch,
                        self.length == other.length,
                        self.volume == other.volume))
        except:
            return False

    def __add__(self, other):
        '''Create a Chord by summing this and another Note.'''
        if hasattr(other, 'notes'):
            other = other.notes
        else:
            other = [other]
        return Chord([self] + other)

    def __radd__(self, other):
        '''Create a Chord by summing this and another Note.'''
        if other == 0:
            return self
        else:
            return self.__add__(other)

    def alter(self, pitch=False, length=False, volume=False):
        '''
        Create a new note which has the same attributes as self,
        except where specified.

        Parameters
        ----------
        pitch : number or str, optional
            The new pitch. The default is False.
        length : number, optional
            The new length. The default is False.
        volume : number, optional
            The new volume. The default is False.

        Returns
        -------
        wubwub.notes.Note
            The new Note.

        '''
        pitch = self.pitch if pitch is False else pitch
        length = self.length if length is False else length
        volume = self.volume if volume is False else volume
        return Note(pitch, length, volume)

class Chord(object):
    '''Class to represent an atomic MIDI-like chord in wubwub.'''
    __slots__ = ('notes')
    def __init__(self, notes):
        '''
        Initialze the Chord with a set of Notes.

        Parameters
        ----------
        notes : list-like
            Collection of `wubwub.notes.Note` objects.  These are added
            to a SortedList, where the key is the pitch.  Any notes with
            scientific pitch notation values for the pitch are given a semitone
            value relative to C4 for sorting purposes.

        Returns
        -------
        None

        '''
        def keyfunc(note):
            if isinstance(note.pitch, str):
                val = relative_pitch_to_int('C4', note.pitch)
            else:
                val = note.pitch
            return val
        object.__setattr__(self, "notes", SortedList(notes, key=keyfunc))

    def __repr__(self):
        '''String representation of the Chord.'''
        pitches = []
        lengths = []
        volumes = []

        for note in self.notes:
            pitches.append(note.pitch)
            lengths.append(note.length)
            volumes.append(note.volume)

        s = f'Chord(pitches={pitches}, lengths={lengths}, volumes={volumes})'
        return s

    def __setattr__(self, *args):
        '''Lock attribute setting.'''
        name = self.__class__.__name__
        raise AttributeError(f"'{name}' object doesn't support item assignment")

    def __delattr__(self, *args):
        '''Lock attribute deletion.'''
        name = self.__class__.__name__
        raise AttributeError(f"'{name}' object doesn't support item deletion")

    def __iter__(self):
        '''Iterate over the Notes of the Chord.'''
        return iter(self.notes)

    def __getitem__(self, i):
        '''Return the ith Note of the Chord.'''
        return self.notes[i]

    def __len__(self):
        '''Return the number of Notes in the Chord.'''
        return len(self.notes)

    def __eq__(self, other):
        '''Check for equivalence with another Chord.  Returns True only if
        other is of the same length of self, and if all of its `notes`
        are equal to all the `notes` of self.'''
        try:
            return (len(self) == len(other) and
                    all((a == b for a, b in zip(self.notes, other.notes))))
        except:
            return False

    def __add__(self, other):
        '''Create a new Chord by adding another Note or Chord.'''
        if hasattr(other, 'notes'):
            other = other.notes
        else:
            other = [other]
        return Chord(self.notes + other)

    def __radd__(self, other):
        '''Create a new Chord by adding another Note or Chord.'''
        if other == 0:
            return self
        else:
            return self.__add__(other)

    @property
    def pitches(self):
        '''Return the `pitch` value for each Note.'''
        return [note.pitch for note in self.notes]

    @property
    def lengths(self):
        '''Return the `length` value for each Note.'''
        return [note.length for note in self.notes]

    @property
    def volumes(self):
        '''Return the `volume` value for each Note.'''
        return [note.volume for note in self.notes]

class ArpChord(Chord):
    __slots__ = ('notes', 'length')
    def __init__(self, notes, length):
        super().__init__(notes)
        object.__setattr__(self, "length", length)

    def __repr__(self):
        pitches = [note.pitch for note in self.notes]
        s = f'ArpChord(pitches={pitches}, length={self.length})'
        return s

    def __eq__(self, other):
        try:
            return (len(self) == len(other) and
                    all((a == b for a, b in zip(self.notes, other.notes))) and
                    self.length == other.length)
        except:
            return False

    def __add__(self, other):
        newl = self.length
        if hasattr(other, 'notes'):
            other = other.notes
            if hasattr(other, 'length'):
                newl = max(newl, other.length)
        else:
            other = [other]
        return ArpChord(self.notes + other, newl)

    def __radd__(self, other):
        if other == 0:
            return self
        else:
            return self.__add__(other)

    def changelength(self, newlength):
        return ArpChord(self.notes, newlength)


_notetypes_ = [Note, Chord, ArpChord]

def arpeggio_generator(notes, method):
    methods = ['up', 'down', 'updown', 'downup', 'up&down', 'down&up',
               'random']
    if method not in methods:
        formatted = ', '.join(m for m in methods)
        raise WubWubError(f'method must be in {formatted}')

    if method == 'up':
        return cycle(notes)
    if method == 'down':
        return cycle(notes[::-1])
    if method == 'updown':
        return cycle(chain(notes, notes[-2:0:-1]))
    if method == 'downup':
        return cycle(chain(notes[::-1], notes[1:-1]))
    if method == 'up&down':
        return cycle(chain(notes, notes[::-1]))
    if method == 'down&up':
        return cycle(chain(notes[::-1], notes))
    if method == 'random':
        return random_choice_generator(notes)

def arpeggiate(chord, beat, length=None, freq=0.5, method='up', auto_chord_length='max'):

    notes = chord.notes

    if length is None:
        if isinstance(chord, ArpChord):
            length = chord.length

        elif isinstance(chord, Chord):
            choices = {'min':min, 'max':max}
            length = choices[auto_chord_length]([note.length for note in notes])

        else:
            raise WubWubError('chord must be wubwub.Chord or wubwub.ArpChord')

    freq = Fraction(freq).limit_denominator()
    current = Fraction(beat).limit_denominator()
    end = beat + length
    arpeggiated = {}
    gen = arpeggio_generator(notes, method)

    while current < end:
        note = next(gen)
        notelength = freq if current + freq <= end else end-current
        pos = current.numerator / current.denominator
        notelength = notelength.numerator / notelength.denominator
        arpeggiated[pos] = Note(pitch=note.pitch, length=notelength,
                                volume=note.volume)
        current += freq

    return arpeggiated

def alter_notes(array, pitch=False, length=False, volume=False):
    return [n.alter(pitch, length, volume) for n in array]

def new_chord(pitches, lengths=1, volumes=0):
    size = len(pitches)
    if not isinstance(lengths, Iterable):
        lengths = [lengths] * size
    if not isinstance(volumes, Iterable):
        volumes = [volumes] * size

    notes = [Note(p, l, v) for p, l, v in zip(pitches, lengths, volumes)]
    return Chord(notes)

def chord_from_name(root, kind='', voicing=0, lengths=1, volumes=0, add=None):
    try:
        pitches = list(named_chords[kind])
    except KeyError:
        raise WubWubError(f'Chord "{kind}" either not recognized or not '
                          'implemented.')

    if add is None:
        add = []

    if add:
        if not isinstance(add, Iterable):
            add = [add]
        pitches += add
    if isinstance(root, str):
        pitches = [pitch_from_semitones(root, p) for p in pitches]
    return new_chord(pitches, lengths, volumes)

