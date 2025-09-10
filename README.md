# OSCAR Language
**OS**cilloscope **C**ode **A**nd **R**enderer

OSCAR is a live coding environment for creating visuals using sound waves, which are plotted on an x-y oscilloscope. For example, two offset sine waves on different audio channels produce a circle. The language in this repo can be used for generating the audio signals that are then visualized by the [OSCAR Renderer](https://github.com/azzeloof/oscar-render) (or an oscilloscope) and can be interracted with via the [OSCAR VSCode plugin](https://github.com/azzeloof/oscar-vscode).

**This is still under active development and may change significantly**

## Getting Started

### Prerequisites

*   Python 3.7+
*   [PortAudio](http://www.portaudio.com/): A cross-platform audio I/O library. You can install it on macOS with `brew install portaudio` or on Debian-based Linux with `sudo apt-get install libportaudio-dev`.
*   The [OSCAR Renderer](https://github.com/adamz/oscar-render) must be running to visualize the output.

### Installation

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/adamz/oscar-lc.git
    cd oscar-lc
    ```

2.  **Set up a Python virtual environment:**
    ```bash
    python3 -m venv .venv
    source .venv/bin/activate
    ```
    The python-rtmidi library doesn't currently work for Python 3.13 on Apple Silicon Macs, so use Python 3.12 for now.

3.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Build the audio server:**
    The audio server is a C++ extension that handles the audio processing. It needs to be built and installed from within the virtual environment.
    ```bash
    cd src/oscar_server
    pip install .
    cd ../.. 
    ```

## Usage

Once the installation is complete, you can run the OSCAR live coding environment:

```bash
python src/oscar.py
```

This will start an interactive Python shell where you can control the audio signals in real-time. For a more integrated experience, you can use the [OSCAR VSCode Plugin](https://github.com/azzeloof/oscar-vscode), which allows you to send code from your editor to the running OSCAR environment.

## Core Concepts

The OSCAR environment is built around a few key concepts:

### Synths

A `Synth` is a synthesizer that generates a waveform. You can create a synth and control its parameters like this:

```python
# Create a synth named 's1'
s1 = Synth('s1')

# Set the frequency to 220 Hz
s1.freq(220)

# Set the amplitude to 0.8
s1.amp(0.8)

# Set the phase offset
s1.phase(0.25)

# Change the waveform to a sawtooth wave
s1.wave(Synth.WAVES['saw'])
```

OSCAR comes with several built-in waveforms:
* `Synth.WAVES['sine']`
* `Synth.WAVES['square']`
* `Synth.WAVES['saw']`
* `Synth.WAVES['triangle']`

You can also define your own custom waveforms using a Python function that returns a NumPy array. This allows for complex, dynamic waveform generation.

### Patches

A `Patch` routes the output of a `Synth` to one or more audio channels. The first channel is typically used for the X-axis of the oscilloscope, and the second channel for the Y-axis.

```python
# Create two synths
s1 = Synth('s1')
s2 = Synth('s2')

# Set the phase of the second synth to create a circle
s2.phase(0.25)

# Patch s1 to the first channel (X-axis)
p1 = Patch('p1', s1, [0])

# Patch s2 to the second channel (Y-axis)
p2 = Patch('p2', s2, [1])
```

### Scope

The `scope` object allows you to control the appearance of the visuals in the OSCAR Renderer. You can control parameters like color, thickness, and blur for each channel.

```python
# Set the thickness of the line for the first channel
scope.ch[0].thickness(4.0)

# Set the color of the line for the second channel (R, G, B, A)
scope.ch[1].color(255, 0, 0, 255)

# Apply some blur
scope.ch[1].blur(2.0)

# Set the number of samples to retain for the persistence effect
scope.ch[0].samples(10000)

# Control the transparency of "fast" portions of the trace
scope.ch[0].alphaScale(3000)

# Set the overall scale of the trace
scope.ch[0].scale(0.8)
```

### Controls

A `Control` is an observable value that can be used to control synth parameters. This is useful for creating interactive performances, for example, by linking controls to MIDI inputs.

```python
# Create a control for the frequency
freq_control = Control(440)

# Register the synth's frequency to the control
s1 = Synth('s1')
freq_control.register_callback('s1_freq', s1.freq)

# Now, updating the control will update the synth's frequency
freq_control.update(880)
```

### MIDI Control

OSCAR has built-in support for MIDI input, allowing you to control your visuals with MIDI controllers.

First, you can list the available MIDI devices:

```python
MidiInput.devices()
```

Then, you can create a `MidiInput` instance and provide a callback function to handle incoming MIDI messages.

```python
# Define a callback function to process MIDI messages
def midi_callback(message):
    if message.type == 'control_change' and message.control == 21:
        # Map MIDI CC 21 to the frequency of s1
        # The value is scaled from 0-127 to a frequency range
        new_freq = (message.value / 127.0) * 880.0
        s1.freq(new_freq)

# Create a MidiInput instance with the callback
# Replace 0 with the index of your MIDI device
midi = MidiInput(device=0, callback=midi_callback)
```

### Master Controls

The `master` object provides control over the global audio engine.

```python
# Set the master volume
master.vol(0.5)

# Get a list of all active synths
master.getSynths()

# Get a list of all active patches
master.getPatches()

# Stop all running synths
master.stopAll()

# Shutdown the audio engine
master.shutdown()
```

## Advanced Usage

### Custom Waveform Arguments

When creating a custom waveform function for a `Synth`, you can pass arguments to it using the `fn_args` parameter in the `Synth` constructor. This is useful for creating dynamic and parameter-driven waveforms.

```python
def my_custom_wave(table_size, my_arg=1.0):
    # ... create a waveform using my_arg ...
    return waveform_array

# Pass the argument to the synth
s1 = Synth('s1', wave_fn=my_custom_wave, fn_args={'my_arg': 2.0})
```

### Using Standard Python Libraries

The OSCAR live coding environment is a full Python environment. You can import and use standard Python libraries like `time`, `math`, and `numpy` to create complex and evolving patterns.

```python
import time

# Create a synth that changes frequency over time
s1 = Synth('s1')

def update_freq():
    while True:
        new_freq = 440 + (math.sin(time.time()) * 100)
        s1.freq(new_freq)
        time.sleep(0.01)

# Run this in a separate thread
import threading
threading.Thread(target=update_freq, daemon=True).start()
```

## Examples

The `examples` directory contains several `.os` files that demonstrate the capabilities of OSCAR.

## Contributing

Contributions are welcome! Please feel free to open an issue or submit a pull request.
