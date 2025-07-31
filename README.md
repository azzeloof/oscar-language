s1 = Synth('s1')
s2 = Synth('s2')
s3 = Synth('s3')

patches = [
    Patch('p1', "s1", [0]),
    Patch('p2', "s2", [1, 2]),
    Patch('p3', "s3", [3, 4, 5])
]

bpm = 120
df = bpm/120

s2.phase(0.25)
s3.phase(0.5)
s1.freq(220)
s2.freq(220.1)
s3.freq(21.99)

s1.wave(Synth.WAVES['triangle'])
s2.wave(Synth.WAVES['sine'])

s1.amp(1.0)
s2.amp(1.0)
s3.amp(1.0)

exit()