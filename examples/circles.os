"""
circles.os
OSCAR Live Coding Example
Adam Zeloof
9/5/2025
"""

s1 = Synth('s1')
s2 = Synth('s2')

s3 = Synth('s3')
s4 = Synth('s4')

s5 = Synth('s5')
s6 = Synth('s6')

patches = [
    Patch('p1', "s1", [0]),
    Patch('p2', "s2", [1]),
    Patch('p3', "s3", [3]),
    Patch('p4', "s4", [2]),
    Patch('p5', "s5", [4]),
    Patch('p6', "s6", [5])
]


scope.ch[0].thickness(6.0)
scope.ch[0].samples(10000)
scope.ch[0].blur(1)
scope.ch[0].color(255, 193, 79, 255)
scope.ch[0].alphaScale(3000)

scope.ch[1].thickness(4.0)
scope.ch[1].blur(2)
scope.ch[1].alphaScale(300)
scope.ch[1].samples(20000)
scope.ch[1].color(0, 255, 255)
scope.ch[1].color(255, 193, 79, 255)

scope.ch[2].thickness(2)
scope.ch[2].blur(2)
scope.ch[2].alphaScale(1000)
scope.ch[2].samples(40000)
scope.ch[2].color(0, 255, 0)
scope.ch[2].color(255, 193, 79, 255)
s3.phase(0.25)

def a(b):
    return b*10

s2.phase(0.25)
s4.phase(0.25)
s2.freq(440.1)
s2.freq(88.02)
s4.freq(440/9.0+0.01)
s4.freq(440-.1)

s1.wave(Synth.WAVES['saw'])
s2.wave(Synth.WAVES['sine'])

s1.amp(1)
s2.amp(0.6)

s3.amp(1)
s4.amp(1)

s5.freq(400)
s6.freq(480.1)
s5.wave(Synth.WAVES['sine'])
s6.wave(Synth.WAVES['triangle'])