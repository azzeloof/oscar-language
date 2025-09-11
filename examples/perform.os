"""
perform.os
OSCAR Live Coding Example for CMU Performance
Adam Zeloof
9/5/2025
"""

#### HIT RECORD !!! ####

# 135Grilled Asparagus
# 144
# 144
# 126 double

#import pyaudio

s1 = Synth('s1')
s2 = Synth('s2')

s3 = Synth('s3')
s4 = Synth('s4')

patches = [
    Patch('p1', "s1", [0]),
    Patch('p2', "s2", [1]),
    Patch('p3', "s3", [2]),
    Patch('p4', "s4", [3]),
    Patch('p5', "s5", [4]),
    Patch('p6', "s6", [5])
]

### Eye ###
s1.freq(440.0)
s1.wave(Synth.WAVES['triangle'])
s2.phase(0)
s2.amp(0.3)
s3.amp(1)
s4.amp(1)
s4.phase(0.25)
s3.freq(10)
s4.freq(12, smooth=True)
s1.freq(11)
s2.freq(11)


scope.ch[0].thickness(6.0)
scope.ch[0].samples(10000)
scope.ch[0].blur(1.5)
scope.ch[0].color(20, 220, 30, 255)
scope.ch[0].alphaScale(900)

scope.ch[1].thickness(6.0)
scope.ch[1].blur(0.5)
scope.ch[1].alphaScale(3000)
scope.ch[1].samples(10000)
scope.ch[1].color(0, 255, 255)
scope.ch[1].color(0, 193, 220, 255)


s1.freq(440)
s2.freq(440.5)
s2.amp(0)
s2.phase(.25)

## side-scroll sine wave
s3.wave(Synth.WAVES['sine'])
s4.wave(Synth.WAVES['triangle'])
s3.freq(10.0, smooth=True)
s4.freq(8.1, smooth=True)
s3.amp(0.9)
s4.amp(0.9)


s3 = Synth('s3')
s4 = Synth('s4')
s3.amp(0)
s4.amp(0)


s3.stop()
s4.stop()

s3.start()
s4.start()

s1.wave(Synth.WAVES['sine'])
# cool squiggle
doublesine = lambda table_size: (np.sin(2*np.linspace(0, 2 * np.pi, table_size, endpoint=False))*np.sin(np.linspace(0, 2 * np.pi, table_size, endpoint=False))).astype(np.float32)
s4.wave(doublesine)
# increase the n that pi is multiplied by for more cycles 
supersquare = lambda table_size: np.sign(np.sin(np.linspace(0, 4 * np.pi, table_size, endpoint=False))).astype(np.float32)
s2.wave(supersquare)


s3.wave(Synth.WAVES['saw'])

"""
lotsa vertical texture:
s1 saw 100 hz
s2 square 440 hz
other waves look cool for s2 texture too (sine)
"""

s2.wave(doublesine)

master.vol(1.0)

master.registerClockAction({
    's1amps': lambda t: s1.amp(np.sin(t*1.2)),
    's2amps': lambda t: s2.amp(np.cos(t*0.5)),

})

s3.amp(1)
s4.amp(1)

master.clockActions

master.removeClockAction('s3amps')
master.removeClockAction('s4amps')

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


s3.freq(30)
s4.freq(20, smooth=True)
s3.wave(Synth.WAVES['sine'])
s4.wave(Synth.WAVES['sine']) # square for texture
s3.amp(0.25)
s4.amp(0.25)

s3.stop()
s4.stop()

s1.freq(440)
s2.freq(440)
s2.phase(0.25)
s1.wave(Synth.WAVES['sine'])
s2.wave(Synth.WAVES['sine'])

##### Piece 1
tempo = 135

scope.ch[0].thickness(3.0)
scope.ch[0].samples(10000)
scope.ch[0].blur(1.5)
scope.ch[0].color(20, 220, 30, 255)
scope.ch[0].alphaScale(1000)

s1 = Synth('s1')
s2 = Synth('s2')
patches = [
    Patch('p1', "s1", [0]),
    Patch('p2', "s2", [1])
]
f0 = 100
s1.wave(Synth.WAVES['square'])
s2.wave(Synth.WAVES['sine'])
s1.freq(f0)
s2.freq(f0+tempo/(60*8), smooth=True)
s1.amp(1.0)
s2.amp(0.5)
s2.freq(220.6, smooth=True)

s2.wave(Synth.WAVES['sine'])
master.vol(0.95)

######## MIDI Stuff ########
MidiInput.devices()


slider1 = Control(0, lambda x: s1.amp(x/127.0))
dial1 = Control(0, lambda x: s1.freq(x/127.0*2.0 + 439, smooth=True))

slider2 = Control(0, lambda x: s2.amp(x/127.0))
dial2 = Control(0, lambda x: s2.freq(x/127.0*2.0 + 439, smooth=True))

slider8 = Control(0, lambda x: master.vol(x/127.0))

def parseMidi(msg):
    match msg.control:
        case 0:
            # Slider 1
            slider1.update(msg.value)
        case 1:
            # Slider 2
            slider2.update(msg.value)
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
            slider8.update(msg.value)
        case 8:
            # Slider 9
            pass
        case 10:
            # Dial 1
            dial1.update(msg.value)
        case 11:
            # Dial 2
            dial2.update(msg.value)
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


))))]]]] # sometimes I miss a close paren/bracket, and this terminates it before it messes up the MIDI bindings
######## MIDI Binding ########
def midiCB(msg):
    parseMidi(msg)

# Only run this once, it spawns a thread!
midi = MidiInput(device='nanoKONTROL2:nanoKONTROL2 _ CTRL 24:0', callback=midiCB)
midi.stop()
##############################



scope.ch[2].thickness(3.0)
scope.ch[2].samples(10000)
scope.ch[2].blur(1.5)
scope.ch[2].color(255, 220, 30, 255)
scope.ch[2].alphaScale(100)

s5 = Synth('s5')
s6 = Synth('s6')

s5.freq(100)
s6.freq(98)

s5.stop()
s6.stop()

s5.start()
s6.start(

)

master.stopAll()