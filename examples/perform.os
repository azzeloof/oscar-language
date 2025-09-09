"""
perform.os
OSCAR Live Coding Example for CMU Performance
Adam Zeloof
9/5/2025
"""


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
s3.freq(11)
s4.freq(10.1)
s1.freq(11)
s2.freq(11)


scope.ch[0].thickness(6.0)
scope.ch[0].samples(10000)
scope.ch[0].blur(1.0)
scope.ch[0].color(255, 193, 79, 255)
scope.ch[0].alphaScale(3000)

scope.ch[1].thickness(4.0)
scope.ch[1].blur(0)
scope.ch[1].alphaScale(300)
scope.ch[1].samples(20000)
scope.ch[1].color(0, 255, 255)
scope.ch[1].color(0, 193, 220, 255)


s1.freq(440)
s2.freq(440.0)
s2.amp(0.5)
s2.phase(0.25)

s2.freq(440.0, smooth=True)