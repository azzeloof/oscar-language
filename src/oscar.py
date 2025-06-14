import numpy as np
import time
import oscar_server
import sys
import code
from collections.abc import Callable


class EngineBoundType(type):
    """Magic to simplify the live coding syntax."""
    _active_engine = None

    def bind_engine(cls, engine_instance:oscar_server.AudioEngine) -> None:
        """Binds a single engine instance to this class."""
        cls._active_engine = engine_instance

    def get_engine(cls) -> oscar_server.AudioEngine:
        """Returns the bound engine instance."""
        if not cls._active_engine:
            raise RuntimeError(f"{cls.__name__} is not bound to an engine.")
        return cls._active_engine

class Synth(metaclass=EngineBoundType):
    """Wrapper on the Synth class from the c++ engine."""
    WAVES = {
        'sine': lambda table_size: np.sin(np.linspace(0, 2 * np.pi, table_size, endpoint=False)).astype(np.float32),
        'square': lambda table_size: np.sign(np.sin(np.linspace(0, 2 * np.pi, table_size, endpoint=False))).astype(np.float32),
        'saw': lambda table_size: np.linspace(-1, 1, table_size, endpoint=False).astype(np.float32),
        'triangle': lambda table_size: np.abs(np.linspace(-1, 1, table_size, endpoint=False)).astype(np.float32)
    }

    def __init__(self, name:str, frequency:float = 440.0, amplitude:float = 0.5, offset:float = 0.0, wave_fn:Callable = WAVES['sine'], fn_args:dict = {}):
        self.engine = self.__class__.get_engine()
        self.synth_name = name
        self.wave_fn = wave_fn
        self.fn_args = fn_args
        self.table_size = 2048
        self.wavetable = None
        self.regen(update=False)
        self.ptr = self.engine.get_or_create_synth(self.synth_name, self.wavetable)
        self.start()
    
    def regen(self, rebuild:bool = True, update:bool = True) -> None:
        """Rebuilds the wavetable and optionally updates the engine."""
        if rebuild:
            wavetable = self.wave_fn(self.table_size, **self.fn_args)
            # Normalize the table to be between -1.0 and 1.0
            wavetable /= np.max(np.abs(wavetable))
        self.wavetable = wavetable
        if update:
            self.ptr.update_wavetable(self.wavetable)

    def name(self) -> str:
        """Returns the name of the synth."""
        return self.synth_name
    
    def start(self) -> None:
        self.ptr.start()

    def stop(self) -> None:
        self.ptr.stop()

    def playing(self) -> bool:
        return self.ptr.is_playing()

    def freq(self, freq:float = None) -> None | float:
        if freq == None:
            return self.ptr.get_frequency()
        else:
            self.ptr.set_frequency(freq)

    def phase(self, offset:float = None) -> None | float:
        if offset == None:
            return self.ptr.get_phase_offset()
        else:
            self.ptr.set_phase_offset(offset % 1.0)

    def amp(self, amp:float = None) -> None | float:
        if amp == None:
            return self.ptr.get_amplitude()
        else:
            self.ptr.set_amplitude(amp)

    def wave(self, wave_fn:callable = None, fn_args:dict = {}) -> None | Callable:
        if wave_fn == None:
            return self.wave_fn
        else:
            self.wave_fn = wave_fn
            self.regen()
    
class Patch(metaclass=EngineBoundType):
    """Wrapper on the Patch class from the c++ engine."""
    def __init__(self, patch_name:str, synth:str|Synth, channels:list[int]):
        self.engine = self.__class__.get_engine()
        self.patch_name = patch_name
        if isinstance(synth, str):
            synth_name = synth
        else:
            synth_name = synth.name()
        self.ptr = self.engine.get_or_create_patch(self.patch_name, synth_name, channels)

    def get_synth_name(self) -> str:
        """Returns the name of the synth being patched."""
        return self.synth_name
    
    def synth(self, s:str|Synth|None = None) -> None | str:
        """
        Gets or sets the synth being patched in one of three cases:
            - s=None: Queries the engine for the synth name and returns it
            - s="s1": Sets the synth to be the one named "s1"
            - s=s1: Retrieves the name of synth s1 and sets the patch to use it
        """
        if s == None:
            return self.ptr.get_synth_name()
        if isinstance(s, str):
            synth_name = s
        else:
            synth_name = s.name()
        self.ptr.set_synth_name(synth_name)


    def ch(self, c:list[int]|None = None) -> None | list[int]:
        """
        Gets or sets the list of channels being patched into
        """
        if c == None:
            return self.ptr.get_channels()
        else:
            self.ptr.set_channels(c)

class Master(metaclass=EngineBoundType):
    def __init__(self):
        self.engine = self.__class__.get_engine()

    def vol(self, v:float|None = None) -> None | float:
        if v == None:
            return self.engine.get_master_volume()
        else:
            self.engine.set_master_volume(v)

    def getSynths(self) -> list[str]:
        return self.engine.list_synths()

    def getPatches(self) -> list[str]:
        return self.engine.list_patches()
    
    def stopAll(self) -> None:
        self.engine.stop_all()


def example(master=None):
    s1 = Synth("s1")
    s1.freq(100)
    s2 = Synth("s2", wave_fn=Synth.WAVES['sine'])
    s2.freq(100)
    patches = [
        Patch('p1', "s1", [0]),
        Patch('p2', "s2", [1])
    ]
    time.sleep(2)
    #s1.amp(0.8)
    #s2.amp(0.8)
    s2.phase(0.25)
    time.sleep(2)
    s1.wave(wave_fn=Synth.WAVES['square'])
    time.sleep(2)
    patches[0].ch([1])
    patches[1].ch([0])
    time.sleep(2)
    patches[0].synth(s2)
    patches[1].synth('s1')
    time.sleep(2)
    master.vol(0.5)
    time.sleep(2)
    master.vol(1.0)
    time.sleep(2)
    s1.stop()
    s2.stop()


def run():
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
    engine = oscar_server.AudioEngine(chosen_index, chosen_device.max_output_channels)
    Synth.bind_engine(engine)
    Patch.bind_engine(engine)
    Master.bind_engine(engine)
    print("\nEngine Initialization Completed\n")
    banner = "Oscar Interpreter Version 0.1"
    exitmsg = "Exiting Oscar..."
    master = Master()
    vars = globals().copy()
    vars.update({'master': master})
    repl = code.InteractiveConsole(locals=vars)
    repl.interact(banner=banner, exitmsg=exitmsg)
    master.stopAll()
    oscar_server.terminate()

if __name__ == '__main__':
    run()
