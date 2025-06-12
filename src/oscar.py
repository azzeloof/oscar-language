import numpy as np
import time
import oscar_server
import sys
import code

class Synth:
    global engine
    WAVES = {
        'sine': lambda table_size: np.sin(np.linspace(0, 2 * np.pi, table_size, endpoint=False)).astype(np.float32),
        'square': lambda table_size: np.sign(np.sin(np.linspace(0, 2 * np.pi, table_size, endpoint=False))).astype(np.float32),
        'saw': lambda table_size: np.linspace(-1, 1, table_size, endpoint=False).astype(np.float32),
        'triangle': lambda table_size: np.abs(np.linspace(-1, 1, table_size, endpoint=False)).astype(np.float32)
    }

    def __init__(self, name, frequency=440.0, amplitude=0.5, wave_fn=WAVES['sine'], fn_args={}):
        self.name = name
        self.frequency = frequency
        self.amplitude = amplitude
        self.wave_fn = wave_fn
        self.fn_args = fn_args
        self.table_size = 2048
        self.wavetable = None
        self.regen()
        self.ptr = engine.get_or_create_synth(self.name, self.wavetable)
        self.start()

    def get_name(self):
        return self.name

    def regen(self):
        wavetable = self.wave_fn(self.table_size, **self.fn_args)
        # Normalize the table to be between -1.0 and 1.0
        wavetable /= np.max(np.abs(wavetable))
        self.wavetable = wavetable

    def start(self):
        self.ptr.start()

    def stop(self):
        self.ptr.stop()

    def is_playing(self):
        return self.ptr.is_playing()

    def freq(self, freq=None):
        if freq == None:
            return self.frequency
        else:
            self.frequency = freq
            self.ptr.set_frequency(freq)

    def amp(self, amp=None):
        if amp == None:
            return self.amplitude
        else:
            self.amplitude = amp
            self.ptr.set_amplitude(amp)

    def set_wave_fn(self, wave_fn, fn_args={}):
        self.wave_fn = wave_fn
    
class Patch:
    global engine
    def __init__(self, patch_name, synth, channels):
        self.patch_name = patch_name
        if isinstance(synth, str):
            self.synth_name = synth
        else:
            self.synth_name = synth.get_name()
        self.channels = channels
        self.ptr = engine.get_or_create_patch(self.patch_name, self.synth_name, self.channels)

    def get_channels(self):
        return self.channels

    def get_synth_name(self):
        return self.synth_name

def example():
    global engine
    s1 = Synth("s1", wave_fn=Synth.WAVES['square'])
    s1.start()
    s1.freq(100)
    s2 = Synth("s2", wave_fn=Synth.WAVES['triangle'])
    s2.freq(100.2)
    s2.start()
    patches = [
        Patch('p1', "s1", [0]),
        Patch('p2', "s2", [1])
    ]
    time.sleep(10)
    s1.stop()
    s2.stop()

def run():
    global engine
    print("Discovering audio devices...")
    try:
        oscar_server.initialize()
    except RuntimeError as e:
        print(f"FATAL: Failed to initialize PortAudio: {e}")
        sys.exit(1)
    try:
        devices = oscar_server.get_device_details()
        if not devices:
            print("Error: No audio devices found. Please ensure PortAudio is installed and working.")
            sys.exit(1)
    except Exception as e:
        print(f"An unexpected error occurred while enumerating devices: {e}")
        sys.exit(1)

    print("\nAvailable Audio Devices:")
    for device in devices:
        print(f"  {device}")
        chosen_index = -1
    while True:
        try:
            raw_input = input(f"\nPlease enter the index of the device you want to use [0-{len(devices)-1}]: ")
            chosen_index = int(raw_input)
                
            if 0 <= chosen_index < len(devices):
                break
            else:
                print(f"Error: Index out of range. Please enter a number between 0 and {len(devices)-1}.")
        except ValueError:
            print("Error: Invalid input. Please enter a number.")
        except (KeyboardInterrupt, EOFError):
            print("\nSelection cancelled. Exiting.")
            sys.exit(0)

    chosen_device = devices[chosen_index]
    #engine = Oscar(chosen_index, chosen_device.max_output_channels)
    engine = oscar_server.AudioEngine(chosen_index, chosen_device.max_output_channels)
    print("\nEngine Initialization Completed\n")
    banner = "Oscar Interpreter Version 0.1"
    exitmsg = "Exiting Oscar..."
    repl = code.InteractiveConsole(locals=globals())
    repl.interact(banner=banner, exitmsg=exitmsg)

    oscar_server.terminate()

if __name__ == '__main__':
    run()
