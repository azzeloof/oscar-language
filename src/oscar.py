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
        self.synth_name = name
        self.frequency = frequency
        self.amplitude = amplitude
        self.wave_fn = wave_fn
        self.fn_args = fn_args
        self.table_size = 2048
        self.wavetable = None
        self.regen(update=False)
        self.ptr = engine.get_or_create_synth(self.synth_name, self.wavetable)
        self.start()
    
    def regen(self, update=True):
        wavetable = self.wave_fn(self.table_size, **self.fn_args)
        # Normalize the table to be between -1.0 and 1.0
        wavetable /= np.max(np.abs(wavetable))
        self.wavetable = wavetable
        if update:
            self.ptr.update_wavetable(self.wavetable)

    def name(self):
        return self.synth_name
    
    def start(self):
        self.ptr.start()

    def stop(self):
        self.ptr.stop()

    def playing(self):
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

    def wave(self, wave_fn=None, fn_args={}):
        if wave_fn == None:
            return self.wave_fn
        else:
            self.wave_fn = wave_fn
            self.regen()
    
class Patch:
    global engine
    def __init__(self, patch_name, synth, channels):
        self.patch_name = patch_name
        if isinstance(synth, str):
            self.synth_name = synth
        else:
            self.synth_name = synth.name()
        self.channels = channels
        self.ptr = engine.get_or_create_patch(self.patch_name, self.synth_name, self.channels)

    def get_synth_name(self):
        return self.synth_name
    
    def synth(self, s=None):
        """
        Gets or sets the synth being patched in one of three cases:
            - s=None: Queries the engine for the synth name and returns it
            - s="s1": Sets the synth to be the one named "s1"
            - s=s1: Retrieves the name of synth s1 and sets the patch to use it
        """
        if s == None:
            self.synth_name = self.ptr.get_synth_name()
            return self.synth_name
        if isinstance(s, str):
            self.synth_name = s
        else:
            self.synth_name = s.name()
        self.ptr.set_synth_name(self.synth_name)


    def ch(self, c=None):
        """
        Gets or sets the list of channels being patched into
        """
        if c == None:
            self.channels = self.ptr.get_channels()
            return self.channels
        else:
            self.channels = c
            self.ptr.set_channels(self.channels)



def example():
    global engine
    s1 = Synth("s1")
    s1.freq(100)
    s2 = Synth("s2", wave_fn=Synth.WAVES['sine'])
    s2.freq(100)
    patches = [
        Patch('p1', "s1", [0]),
        Patch('p2', "s2", [1])
    ]
    time.sleep(2)
    s1.amp(0.8)
    s2.amp(0.8)
    s1.wave(wave_fn=Synth.WAVES['square'])
    time.sleep(2)
    patches[0].ch([1])
    patches[1].ch([0])
    time.sleep(2)
    patches[0].synth(s2)
    patches[1].synth('s1')
    time.sleep(2)
    engine.set_master_volume(0.5)
    time.sleep(2)
    engine.set_master_volume(1.0)
    time.sleep(2)
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
    engine.stop_all()
    oscar_server.terminate()

if __name__ == '__main__':
    run()
