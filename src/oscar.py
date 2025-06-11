
"""
import code
import oscar_server
import time
import sys


def run():
    # --- 1. Get the list of available audio devices from our C++ module ---
    print("Discovering audio devices...")
    oscar_server.initialize()
    try:
        devices = oscar_server.get_device_details()
        if not devices:
            print("Error: No audio devices found. Please ensure PortAudio is installed and working.")
            sys.exit(1)
    except Exception as e:
        print(f"An unexpected error occurred while getting device details: {e}")
        sys.exit(1)

    # --- 2. Print the list of devices for the user to choose from ---
    print("\nAvailable Audio Devices:")
    for device in devices:
        print(f"  {device}")

    # --- 3. Prompt the user for input and validate it ---
    chosen_index = -1
    while True:
        try:
            raw_input = input(f"\nPlease enter the index of the device you want to use [0-{len(devices)-1}]: ")
            chosen_index = int(raw_input)
            
            # Check if the chosen index is valid
            if 0 <= chosen_index < len(devices):
                break  # Exit the loop if input is valid
            else:
                print(f"Error: Index out of range. Please enter a number between 0 and {len(devices)-1}.")
        except ValueError:
            print("Error: Invalid input. Please enter a number.")
        except (KeyboardInterrupt, EOFError):
            print("\nSelection cancelled. Exiting.")
            sys.exit(0)

    # --- 4. Initialize the AudioEngine with the selected device ---
    chosen_device = devices[chosen_index]
    
    # We will request to use all available output channels on the selected device.
    num_channels_to_use = chosen_device.max_output_channels

    if num_channels_to_use == 0:
        print(f"Error: Device '{chosen_device.name}' has no output channels and cannot be used.")
        sys.exit(1)

    print(f"\nInitializing audio engine with device '{chosen_device.name}' using {num_channels_to_use} channels...")
    
    try:
        # This is where we create the C++ AudioEngine object
        engine = oscar_server.AudioEngine(
            device_index=chosen_index,
            num_channels=num_channels_to_use
        )
        print("Engine initialized successfully!")
        
    except RuntimeError as e:
        print(f"\nFATAL: Failed to initialize audio engine: {e}")
        sys.exit(1)

    print("\nAudio engine is active. You can now create synths and patches.")
    print("(The C++ audio callback is running in the background)")
    code.InteractiveConsole(locals=locals()).interact()

    
    print("Done.")


if __name__ == '__main__':
    run()

"""

import numpy as np
import time
import oscar_server
import sys

## --- Boilerplate setup ---
#oscar_server.initialize()
#engine = oscar_server.AudioEngine(device_index=21, num_channels=2)
## -------------------------


class Synth:
    global engine
    WAVE_FUNCTIONS = {
        'sine': lambda table_size: np.sin(np.linspace(0, 2 * np.pi, table_size, endpoint=False)).astype(np.float32)
    }

    def __init__(self, name, frequency=440.0, amplitude=0.5, wave_fn=WAVE_FUNCTIONS['sine'], fn_args={}):
        self.name = name
        self.frequency = frequency
        self.amplitude = amplitude
        self.wave_fn = wave_fn
        self.fn_args = fn_args
        self.table_size = 2048
        self.wavetable = None
        self.regen()
        self.ptr = engine.get_or_create_synth(self.name, self.wavetable)

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
    
class Patch:
    global engine
    def __init__(self, patch_name, synth_name, channels):
        self.patch_name = patch_name
        self.synth_name = synth_name
        self.channels = channels
        self.ptr = engine.get_or_create_patch(self.patch_name, self.synth_name, self.channels)

    def get_channels(self):
        return self.channels

    def get_synth_name(self):
        return self.synth_name
"""
class Oscar:
    def __init__(self, device_index, num_channels):
        print("initializing audio engine...")
        try:
            self.audio_engine = oscar_server.AudioEngine(device_index, num_channels)
        except RuntimeError as e:
            print(f"FATAL: Failed to initialize audio engine: {e}")
    
    def get_or_create_synth(self, name, wavetable):
        return self.audio_engine.get_or_create_synth(name, wavetable)

    def get_or_create_patch(self, patch_name, synth_name, channels):
        return self.audio_engine.get_or_create_patch(patch_name, synth_name, channels)
"""   

def example():
    global engine
    s1 = Synth("s1")
    s1.start()
    s2 = Synth("s2")
    s2.freq(110.2)
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
    #ngine = Oscar(chosen_index, chosen_device.max_output_channels)
    engine = oscar_server.AudioEngine(chosen_index, chosen_device.max_output_channels)



    oscar_server.terminate()

if __name__ == '__main__':
    run()
