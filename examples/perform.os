"""
perform.os
OSCAR Live Coding Example for CMU Performance
Adam Zeloof
9/5/2025
"""

#import pyaudio
import math

s1 = Synth('s1')
s2 = Synth('s2')

s3 = Synth('s3')
s4 = Synth('s4')

patches = [
    Patch('p1', "s1", [0]),
    Patch('p2', "s2", [1]),
    Patch('p3', "s3", [2]),
    Patch('p4', "s4", [3])
]

### Eye ###
s1.freq(440.0)
s1.wave(Synth.WAVES['triangle'])
s2.phase(0)
s2.amp(0.3)
s3.amp(0.1)
s4.amp(0.10)
s4.phase(0.25)
s3.freq(10)
s4.freq(12, smooth=True)
s1.freq(11)
s2.freq(11)


scope.ch[0].thickness(6.0)
scope.ch[0].samples(10000)
scope.ch[0].blur(1.5)
scope.ch[0].color(20, 220, 30, 255)
scope.ch[0].alphaScale(6000)

scope.ch[1].thickness(4.0)
scope.ch[1].blur(0)
scope.ch[1].alphaScale(300)
scope.ch[1].samples(40000)
scope.ch[1].color(0, 255, 255)
scope.ch[1].color(0, 193, 220, 255)


s1.freq(440)
s2.freq(440.5)
s2.amp(0.5)
s2.phase(.25)

## side-scroll sine wave
s1.wave(Synth.WAVES['saw'])
s2.wave(Synth.WAVES['sine'])
s2.freq(440.1, smooth=True)
s1.amp(0.5)
s2.amp(0.25)


s3.stop()
s4.stop()

s1.wave(Synth.WAVES['sine'])
# cool squiggle
doublesine = lambda table_size: (np.sin(2*np.linspace(0, 2 * np.pi, table_size, endpoint=False))*np.sin(np.linspace(0, 2 * np.pi, table_size, endpoint=False))).astype(np.float32)

s2.wave(doublesine)

master.vol(1.0)

master.registerClockAction({
    's1amps': lambda t: s1.amp(math.sin(t*5))
})

master.clockActions

master.removeClockAction('s1amps')

"""
p = pyaudio.PyAudio()
stream = p.open(format=pyaudio.paInt16,
                channels=1,
                rate=44100,
                input=True,
                frames_per_buffer=1024)

data = stream.read(1024)
audio_data = np.frombuffer(data, dtype=np.int16)
rms_amplitude = np.sqrt(np.mean(np.square(audio_data)))
print(rms_amplitude)

stream.stop_stream()
stream.close()
p.terminate()
"""

s1.amp(1.0)
s2.amp(1.0)


s3.wave(Synth.WAVES['saw'])
s4.wave(Synth.WAVES['sine']) # square for texture
s3.amp(1.0)
s4.amp(1.0)

######## MIDI Stuff ########
MidiInput.devices()


slider1 = Control(0, lambda x: s1.amp(x/127.0))
dial1 = Control(0, lambda x: s1.freq(x/127.0*2.0 + 439, smooth=True))

def parseMidi(msg):
    match msg.control:
        case 0:
            # Slider 1
            slider1.update(msg.value)
        case 1:
            # Slider 2
            pass
        case 2:
            # Slider 3
            pass
        case 3:
            # Slider 4
            pass
        case 4:
            # Slider 5
            pass
        case 5:
            # Slider 6
            pass
        case 6:
            # Slider 7
            pass
        case 7:
            # Slider 8
            pass
        case 10:
            # Dial 1
            dial1.update(msg.value)
        case 11:
            # Dial 2
            pass
        case 12:
            # Dial 3
            pass
        case 13:
            # Dial 4
            pass
        case 14:
            # Dial 5
            pass
        case 15:
            # Dial 6
            pass
        case 16:
            # Dial 7
            pass
        case 17:
            # Dial 8
            pass



######## MIDI Binding ########
def midiCB(msg):
    parseMidi(msg)

# Only run this once, it spawns a thread!
midi = MidiInput(device='nanoKONTROL2:nanoKONTROL2 _ CTRL 20:0', callback=midiCB)
midi.stop()
##############################
