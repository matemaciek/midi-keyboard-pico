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
import board
from keybow2040 import Keybow2040

import usb_midi
import adafruit_midi
import mpu9250
from adafruit_midi.note_off import NoteOff
from adafruit_midi.note_on import NoteOn
from adafruit_midi.pitch_bend import PitchBend
from adafruit_midi.control_change import ControlChange
from adafruit_midi.channel_pressure import ChannelPressure

# Set up Keybow
i2c = board.I2C()
imu = mpu9250.IMU(i2c)
keybow = Keybow2040(i2c)
keys = keybow.keys
acc = None
MODIFIER_KEYS = [0, 4, 8, 12]
MODIFIER_RGB = {
    -24: (3, 3, 3),
    -12: (7, 7, 7),
    0: (15, 15, 15),
    12: (31, 31, 31),
    24: (63, 63, 63),
}
LAYOUTS_MODIFIERS = [
    MODIFIER_KEYS,
    MODIFIER_KEYS,
    MODIFIER_KEYS,
    MODIFIER_KEYS,
    [0, 2]
]
LAYOUTS = [{
    0: -24,
    1: 0,
    2: 4,
    3: 8,
    4: -12,
    5: 1,
    6: 5,
    7: 9,
    8: 12,
    9: 2,
    10: 6,
    11: 10,
    12: 24,
    13: 3,
    14: 7,
    15: 11,
}, {
    0: -24,
    1: 0,
    2: 1,
    3: 2,
    4: -12,
    5: 3,
    6: 4,
    7: 5,
    8: 12,
    9: 6,
    10: 7,
    11: 8,
    12: 24,
    13: 9,
    14: 10,
    15: 11,
}, {
    0: -24,
    1: 0,
    2: 4,
    3: 8,
    4: -12,
    5: 3,
    6: 7,
    7: 11,
    8: 12,
    9: 6,
    10: 10,
    11: 2,
    12: 24,
    13: 9,
    14: 1,
    15: 5,
}, {
    0: -24,
    1: 1,
    2: 6,
    3: 11,
    4: -12,
    5: 10,
    6: 3,
    7: 8,
    8: 12,
    9: 7,
    10: 0,
    11: 5,
    12: 24,
    13: 4,
    14: 9,
    15: 2,
},
{
    0: -24,
    1: -7,
    2: 24,
    3: 5,
    4: -12,
    5: -5,
    6: 0,
    7: 7,
    8: -10,
    9: -3,
    10: 2,
    11: 9,
    12: -8,
    13: -1,
    14: 4,
    15: 11,
}]

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
EDIT = False

def shift_layout(direction):
    delta = 1 if direction > 0 else -1
    set_layout((LAYOUT_NUM + delta) % len(LAYOUTS))

def set_layout(idx):
    global LAYOUT, LAYOUT_NUM
    LAYOUT_NUM = idx
    LAYOUT = LAYOUTS[LAYOUT_NUM]
    for key in keys:
        key.modifier = key.number in LAYOUTS_MODIFIERS[LAYOUT_NUM]

set_layout(0)

def shifted(c, octave_shift):
    offset = 0 if EDIT else -(octave_shift // 12 - 2)
    return (c >> offset for c in c)

def key_colour(key, octave_shift):
    if key.modifier:
        return ((0,0,0) if int(2*time.monotonic()) % 2 == 0 else (255, 0, 0) if LAYOUT[key.number] < 0 else (0, 255, 0)) if EDIT else MODIFIER_RGB[LAYOUT[key.number]]
    return shifted(NOTES[LAYOUT[key.number]], octave_shift)

# Set USB MIDI up on channel 0.
midi = adafruit_midi.MIDI(midi_out=usb_midi.ports[1], out_channel=0)

start_note = 60
notes = {}
pending_layout_switch = False

def active_modifiers():
    return [i for i in LAYOUTS_MODIFIERS[LAYOUT_NUM] if i in keybow.get_pressed()]

def octave_shift():
    modifiers = active_modifiers()
    if len(modifiers) != 1:
        return 0
    return LAYOUT[modifiers[0]]

def shifted_note(key_number):
    return start_note + LAYOUT[key_number] + octave_shift()

def trim(down, val, up):
    return max(down, min(up, val))

# Loop through keys and attach decorators.
for key in keys:
    @keybow.on_press(key)
    def press_handler(key):
        if key.modifier:
            global pending_layout_switch
            pending_layout_switch = True
        else:
            note = shifted_note(key.number)
            velocity = trim(0, sum(abs(v) for v in imu.raw_gyr)>>5, 127)
            notes[note] = velocity
            print(notes)
            midi.send(NoteOn(note, velocity))

    @keybow.on_release(key)
    def release_handler(key):
        if key.modifier:
            global EDIT, pending_layout_switch
            modifiers = active_modifiers()
            if len(modifiers) > 0 and sum(LAYOUT[i] for i in modifiers + [key.number]) == 0:
                EDIT = not EDIT
            else:
                if EDIT and pending_layout_switch:
                    shift_layout(LAYOUT[key.number])
            pending_layout_switch = False
        else:
            note = shifted_note(key.number)
            if note in notes:
                del notes[note]
                print(notes)
                midi.send(NoteOff(note, 0))

while True:
    acc = [min(255, abs(v) >> 7) for v in imu.raw_acc]
    keybow.update()
    o_shift = octave_shift()
    for key in keys:
        note = None if key.modifier else shifted_note(key.number)
        if note in notes:
            key.set_led(notes[note], notes[note], notes[note])
        else:
            key.set_led(*key_colour(key, o_shift))
    midi.send(PitchBend(trim(0, (1<<14) - imu.raw_acc[1]>>1, 16383)))
    midi.send(ControlChange(1, trim(0, abs(imu.raw_acc[0]>>7), 127)))
    midi.send(ChannelPressure(trim(0, (sum(abs(v) for v in imu.raw_mag)>>7) - 10, 127)))
