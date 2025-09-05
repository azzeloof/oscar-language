"""
triangles.os
OSCAR Live Coding Example
Adam Zeloof
9/5/2025
"""

import time

# Define a vector graphic to draw. This is a simple triangle.
points = [
    (0.0, 0.0),
    (0.0, 1.0),
    (1.0, 0.0),
    (0.0, 0.0)
]


def graphicX(n):
    nPts = len(points)
    ret = np.zeros(n)
    nSeg = int(n/nPts)
    for i in range(nPts-1):
        x0 = points[i][0]
        x1 = points[i+1][0]
        ret[i*nSeg:(i+1)*nSeg] = np.linspace(x0, x1, nSeg, endpoint=False)
    return ret


def graphicY(n):
    nPts = len(points)
    ret = np.zeros(n)
    nSeg = int(n/nPts)
    for i in range(nPts-1):
        y0 = points[i][1]
        y1 = points[i+1][1]
        ret[i*nSeg:(i+1)*nSeg] = np.linspace(y0, y1, nSeg, endpoint=False)
    return ret


sx = Synth('sx')
sy = Synth('sy')

px = Patch('px', sx, [0])
py = Patch('py', sy, [1])

sx.wave(graphicX)
sy.wave(graphicY)

# Play with slightly offset frequencies for some fun
sx.freq(20)
sy.freq(20)

sx.stop()
sy.stop()

s1.stop()
s2.stop()

master.stopAll()