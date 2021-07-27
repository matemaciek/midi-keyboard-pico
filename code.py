# SPDX-FileCopyrightText: 2021 Sandy Macdonald
#
# SPDX-License-Identifier: MIT

# Demonstrates how to send MIDI notes by attaching handler functions to key
# presses with decorators.

# You'll need to connect Keybow 2040 to a computer running a DAW like Ableton,
# or other software synth, or to a hardware synth that accepts USB MIDI.

# Drop the keybow2040.py file into your `lib` folder on your `CIRCUITPY` drive.

# NOTE! Requires the adafruit_midi CircuitPython library also!

import time
from keybow_hardware.pim551 import PIM551 as Hardware
from keybow2040 import Keybow2040


import usb_midi
import adafruit_midi

has_imu = True
if has_imu:
    import mpu9250

has_pixel = True
pixels = None
if has_pixel:
    import board, neopixel
    pixels = neopixel.NeoPixel(board.GP21, 1)

from adafruit_midi.note_off import NoteOff
from adafruit_midi.note_on import NoteOn
from adafruit_midi.pitch_bend import PitchBend
from adafruit_midi.control_change import ControlChange
from adafruit_midi.channel_pressure import ChannelPressure

# Set up Keybow
hardware = Hardware()
i2c = hardware.i2c()
imu = mpu9250.IMU(i2c) if has_imu else None
keybow = Keybow2040(hardware)
keys = keybow.keys
acc = None
MODIFIER_RGB = {
    -24: (3, 3, 3),
    -12: (7, 7, 7),
    0: (15, 15, 15),
    12: (31, 31, 31),
    24: (63, 63, 63),
}

NORMAL_KEYS = {
     1: 0,  2: 4,  3:  8,
     5: 1,  6: 5,  7:  9,
     9: 2, 10: 6, 11: 10,
    13: 3, 14: 7, 15: 11,
}

NORMAL_MODIFIERS = {
    0: -24,
    4: -12,
    8:  12,
    12: 24,
}

SCALES = {
     6: [0, 2, 4, 5, 7, 9, 11], # Ionian
    10: [0, 2, 3, 5, 7, 9, 10], # Dorian
    14: [0, 1, 3, 5, 7, 8, 10], # Phrygian
     3: [0, 2, 4, 6, 7, 9, 11], # Lydian
     7: [0, 2, 4, 5, 7, 9, 10], # Mixolydian
    11: [0, 2, 3, 5, 7, 8, 10], # Aeolian
    15: [0, 1, 3, 5, 6, 8, 10], # Locrian
     0: [0, 2, 4, 5, 7, 8, 11], # harmonic major
     4: [0, 2, 3, 5, 7, 8, 11], # harmonic minor
    12: [0, 2, 3, 5, 7, 9, 11], # melodic minor
     1: [0, 2, 4, 7, 9], # major pentatonic
     5: [0, 3, 5, 7, 10], # minor pentatonic
     9: [0, 2, 5, 7, 9], # major blues pentatonic
    13: [0, 3, 5, 8, 10], # minor blues pentatonic
}

def merge(d1, d2): # CP does not seem to like **
    return {k:v for k,v in list(d1.items()) + list(d2.items())}

def get(d, i):
    if i in d:
        return d[i]
    return None

class Layout:
    def __init__(self) -> None:
        self.root = 0

    def at(self, i):
        return get(self._keys, i)

    def modifiers(self):
        return [0, 4, 8, 12]

    def edit_keys(self):
        return {0: 'left', 12: 'right'}

class Semitones(Layout):
    def __init__(self):
        super().__init__()
        self._keys = merge(NORMAL_MODIFIERS, NORMAL_KEYS)

class MinThirdsBySemitone(Layout):
    def __init__(self):
        super().__init__()
        self._keys = merge(NORMAL_MODIFIERS, {
             1: 0,  2:  1,  3:  2,
             5: 3,  6:  4,  7:  5,
             9: 6, 10:  7, 11:  8,
            13: 9, 14: 10, 15: 11,
        })

class MinThirds(Layout):
    def __init__(self):
        super().__init__()
        self._keys = merge(NORMAL_MODIFIERS, {
             1: 0,  2:  4,  3:  8,
             5: 3,  6:  7,  7: 11,
             9: 6, 10: 10, 11:  2,
            13: 9, 14:  1, 15:  5,
        })

class Fourths(Layout):
    def __init__(self):
        super().__init__()
        self._keys = merge(NORMAL_MODIFIERS, {
             1:  1,  2: 6,  3: 11,
             5: 10,  6: 3,  7:  8,
             9:  7, 10: 0, 11:  5,
            13:  4, 14: 9, 15:  2,
        })

class Scales(Layout):
    def __init__(self):
        super().__init__()
        self.set_scale(SCALES[6], 0)

    def set_scale(self, i, r):
        if i is not None:
            self.intervals = i
        else:
            i = self.intervals
        if r is not None:
            self.root = r
        else:
            r = self.root
        if len(i) == 7:
            self._normal_keys = {
                 0:        -24, 1: r+i[3]-12,  2:     24,  3: r+i[3],
                 4:  r+i[0]-12, 5: r+i[4]-12,  6: r+i[0],  7: r+i[4],
                 8:  r+i[1]-12, 9: r+i[5]-12, 10: r+i[1], 11: r+i[5],
                12: r+i[2]-12, 13: r+i[6]-12, 14: r+i[2], 15: r+i[6],
            }
            self._edit_keys = merge(NORMAL_MODIFIERS, {
                             3: r+i[3],
                 6: r+i[0],  7: r+i[4],
                10: r+i[1], 11: r+i[5],
                14: r+i[2], 15: r+i[6],
            })
        elif len(i) == 5:
            self._normal_keys = {
                 0:       -24,                 2:     24,
                                5: r+i[2]-12            ,  7: r+i[2],
                 8: r+i[0]-12,  9: r+i[3]-12, 10: r+i[0], 11: r+i[3],
                12: r+i[1]-12, 13: r+i[4]-12, 14: r+i[1], 15: r+i[4],
            }
            self._edit_keys = merge(NORMAL_MODIFIERS, {
                             7: r+i[2],
                10: r+i[0], 11: r+i[3],
                14: r+i[1], 15: r+i[4],
            })

    def at(self, i):
        if EDIT_ROOT:
            return get(merge({4: -12}, NORMAL_KEYS), i)
        if EDIT_SCALE:
            base = get(merge({8: 12}, NORMAL_KEYS), i)
            return None if base is None else base + self.root
        if EDIT:
            return get(self._edit_keys, i)
        return get(self._normal_keys, i)

    def modifiers(self):
        if not EDIT:
            return [0, 2]
        if EDIT_ROOT:
            return [4]
        if EDIT_SCALE:
            return [8]
        return super().modifiers()

    def edit_keys(self):
        return merge(super().edit_keys(), {4: 'root', 8: 'scale'})

LAYOUTS = [Semitones(), MinThirdsBySemitone(), MinThirds(), Fourths(), Scales()]

NOTES = [
    (254, 0,   0),
    (191, 63,  0),
    (127, 127, 0),
    (63,  191, 0),
    (0,   254, 0),
    (0,   191, 63),
    (0,   127, 127),
    (0,   63,  191),
    (0,   0,   254),
    (63,  0,   191),
    (127, 0,   127),
    (191, 0,   63),
]
EDIT_BUTTONS = {
    'left': {
        'c': (64, 0, 0),
        'on_press': False,
        'on_release': True,
    },
    'right': {
        'c': (0, 64, 0),
        'on_press': False,
        'on_release': True,
    },
    'root': {
        'c': (0, 32, 32),
        'on_press': True,
        'on_release': True,
    },
    'scale': {
        'c': (32, 0, 32),
        'on_press': True,
        'on_release': True,
    },
}
EDIT = False
EDIT_ROOT = False
EDIT_SCALE = False

def shift_layout(delta):
    set_layout((LAYOUT_NUM + delta) % len(LAYOUTS))

def set_layout(idx):
    #print('Setting layout:', idx, EDIT, EDIT_ROOT, EDIT_SCALE)
    global LAYOUT, LAYOUT_NUM
    LAYOUT_NUM = idx
    LAYOUT = LAYOUTS[LAYOUT_NUM]
    for key in keys:
        key.modifier = key.number in LAYOUT.modifiers()

set_layout(0)

def shifted(note, octave_shift):
    offset = -(octave_shift // 12 - 2)
    if EDIT:
        offset = 0
    if EDIT_ROOT:
        offset = 0 if note == LAYOUT.root else 3
    if EDIT_SCALE:
        offset = 0 if (note - LAYOUT.root) % 12 in LAYOUT.intervals else 3
    c = NOTES[note % 12]
    return (c >> offset for c in c)

def key_colour(key, octave_shift):
    note = LAYOUT.at(key.number)
    #print(LAYOUT.modifiers())
    if note is None:
        return (0,0,0)
    if key.modifier:
        if not EDIT:
            #print(key.number, key.modifier, note)
            return MODIFIER_RGB[note]
        if key.number in LAYOUT.edit_keys():
            c = EDIT_BUTTONS[LAYOUT.edit_keys()[key.number]]['c']
            return c if int(2*time.monotonic()) % 2 == 0 else (c >> 3 for c in c)
        else:
            return (0,0,0)
    return shifted(note, octave_shift - 12*(note < LAYOUT.root))

# Set USB MIDI up on channel 0.
midi = adafruit_midi.MIDI(midi_out=usb_midi.ports[1], out_channel=0)

start_note = 60
notes = {}
pending_command = 0

def active_modifiers():
    return [i for i in LAYOUT.modifiers() if i in keybow.get_pressed()]

def octave_shift():
    if EDIT_ROOT or EDIT_SCALE:
        return 0
    modifiers = active_modifiers()
    if len(modifiers) != 1:
        return 0
    return LAYOUT.at(modifiers[0])

def shifted_note(note):
    if note is None:
        return None
    return start_note + note + octave_shift()

def shifted_note_for_key(key_number):
    note = LAYOUT.at(key_number)
    if note is None:
        return None
    return start_note + note + octave_shift()

def trim(down, val, up):
    return max(down, min(up, val))

def run_command(command):
    if command == 'left':
        shift_layout(-1)
    elif command == 'right':
        shift_layout(1)
    elif command == 'root':
        global EDIT_ROOT
        EDIT_ROOT = not EDIT_ROOT
        set_layout(LAYOUT_NUM) # modifiers might have changed
    elif command == 'scale':
        global EDIT_SCALE
        EDIT_SCALE = not EDIT_SCALE
        set_layout(LAYOUT_NUM) # modifiers might have changed

def notes_on(n):
    velocity = trim(0, sum(abs(v) for v in imu.raw_gyr)>>5, 127) if has_imu else 127
    for note in [note for note in n if note is not None]:
        notes[note] = velocity
        midi.send(NoteOn(note, velocity))
        #time.sleep(0.05)
    print(notes)

def notes_off(n):
    for note in n:
        if note in notes:
            del notes[note]
            midi.send(NoteOff(note))
    print(notes)

# Loop through keys and attach decorators.
for key in keys:
    @keybow.on_press(key)
    def press_handler(key):
        if key.modifier:
            if EDIT and key.number in LAYOUT.edit_keys():
                name = LAYOUT.edit_keys()[key.number]
                command = EDIT_BUTTONS[name]
                if command['on_press']:
                    run_command(name)
                global pending_command
                pending_command += 1
        else:
            if EDIT_ROOT or EDIT_SCALE:
                intervals = SCALES[key.number] if EDIT_SCALE and key.number in SCALES else None
                root = LAYOUT.at(key.number) if EDIT_ROOT else None
                LAYOUT.set_scale(intervals, root)
                #notes_on([shifted_note(LAYOUT.root + LAYOUT.intervals[i]) for i in [0, 3, 4]])
                if EDIT_ROOT or key.number in SCALES:
                    notes_on([shifted_note(LAYOUT.root + i) for i in LAYOUT.intervals])
            else:
                notes_on([shifted_note_for_key(key.number)])

    @keybow.on_release(key)
    def release_handler(key):
        if key.modifier:
            global EDIT, pending_command
            modifiers = active_modifiers()
            if len(modifiers) == 1 and sorted([LAYOUT.at(i) for i in modifiers + [key.number]]) == [-24, 24]:
                EDIT = not EDIT
                set_layout(LAYOUT_NUM) # modifiers might have changed
                pending_command = 0
            else:
                if EDIT and key.number in LAYOUT.edit_keys():
                    name = LAYOUT.edit_keys()[key.number]
                    command = EDIT_BUTTONS[name]
                    if command['on_release'] and pending_command > 0:
                        pending_command -= 1
                        run_command(name)
        else:
            if EDIT_ROOT or EDIT_SCALE:
                if EDIT_ROOT or key.number in SCALES:
                    notes_off([shifted_note(LAYOUT.root + i) for i in LAYOUT.intervals])
            else:
                notes_off([shifted_note_for_key(key.number)])

while True:
    keybow.update()
    o_shift = octave_shift()
    for key in keys:
        note = None if key.modifier else shifted_note_for_key(key.number)
        if note in notes:
            key.set_led(notes[note], notes[note], notes[note])
        else:
            key.set_led(*key_colour(key, o_shift))
    if has_imu:
        acc = imu.raw_acc
        mag = (sum(abs(v) for v in imu.raw_mag)>>7) - 10
        if has_pixel:
            pixels[0] = (trim(0, mag, 255), abs(acc[0]>>7), abs(acc[1]>>7))
        midi.send(PitchBend(trim(0, (1<<14) - acc[1]>>1, 16383)))
        midi.send(ControlChange(1, trim(0, abs(acc[0]>>7), 127)))
        midi.send(ChannelPressure(trim(0, mag, 127)))
