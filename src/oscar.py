import numpy as np
import time
import oscar_server
import sys
import code
import socket
import selectors
from collections.abc import Callable
import threading
import mido
import queue
from pythonosc.udp_client import SimpleUDPClient
import struct

class Scope:
    """Interface for one channel of the OSCAR Renderer"""
    def __init__(self, n:int, client):
        self.client = client
        self.n = n
    
    def thickness(self, t:float) -> None:
        """Sets the trace thickness (float, 1.0 is default)"""
        self.client.send_message(f'/scope/{self.n}/trace/thickness', float(t))

    def samples(self, n:int) -> None:
        """Sets the number of samples to retain (int)"""
        self.client.send_message(f'/scope/{self.n}/persistence/samples', int(n))
    
    def strength(self, s:float) -> None:
        """Sets the persistence strength (float)"""
        self.client.send_message(f'/scope/{self.n}/persistence/strength', float(s))

    def color(self, r:int, g:int, b:int, a:int = 255) -> None:
        """Sets the trace color (8 bits per channel, RGB)"""
        packedColor = struct.pack('BBBB', r, g, b, a)
        c = struct.unpack('>i', packedColor)[0]
        self.client.send_message(f'/scope/{self.n}/trace/color', c)

    def blur(self, b:float) -> None:
        """Sets the trace blur (float, default 0.0)"""
        self.client.send_message(f'/scope/{self.n}/trace/blur', float(b))

    def alphaScale(self, a:int) -> None:
        """Sets the trace alpha scale, or how transparent "fast" portions of the trace are (int)"""
        self.client.send_message(f'/scope/{self.n}/alpha_scale', int(a))
    
    def scale(self, s:float) -> None:
        """Sets the trace scale (float, 0.0 - 1.0)"""
        self.client.send_message(f'/scope/{self.n}/scale', float(s))

class Renderer:
    """Interface to control the OSCAR Renderer"""
    def __init__(self, host='127.0.0.1', port=7000, nCh=4):
        self.host = host
        self.port = port
        self.client = SimpleUDPClient(self.host, self.port)
        self.ch = [Scope(i, self.client) for i in range(nCh)]

class MidiInput:
    """A class to handle MIDI input in a separate thread."""
    def devices():
        """Returns a list of available MIDI input devices."""
        return mido.get_input_names()

    def __init__(self, device:int = 0, callback:Callable = None):
        self.device = device
        self.callback = callback
        self.queue = queue.Queue()
        self.running = True
        self.listen_thread = threading.Thread(
            target=self.listener,
            args=(self.device, self.queue),
            daemon=True)
        self.parse_thread = threading.Thread(
            target=self.parse,
            daemon=True)
        self.listen_thread.start()
        self.parse_thread.start()

    def listener(self, port, message_queue) -> None:
        """The MIDI listener thread function."""
        try:
            with mido.open_input(port) as in_port:
                while self.running:
                    msg = in_port.poll()
                    if msg:
                        message_queue.put(msg)
                    time.sleep(0.01)
        except Exception as e:
            print(f"Error in MIDI listener: {e}")

    def parse(self) -> None:
        """The MIDI parser thread function."""
        while self.running:
            try:
                msg = self.queue.get_nowait()
                if self.callback != None:
                    self.callback(msg)
            except queue.Empty:
                time.sleep(0.01)

    def stop(self) -> None:
        """Stops the MIDI listener and parser threads gracefully."""
        print("Stopping MIDI threads...")
        self.running = False
        if self.listen_thread.is_alive():
            self.listen_thread.join()
        if self.parse_thread.is_alive():
            self.parse_thread.join()
        print("MIDI threads stopped.")


class Control:
    """A simple observable value for controlling parameters."""
    def __init__(self, value=0):
        self.value = value
        self.callbacks = {}

    def register_callback(self, identifier, callback) -> None:
        """Registers a callback function to be called when the value changes."""
        self.callbacks.update({identifier: callback})

    def unregister_callback(self, identifier) -> None:
        """Unregisters a callback function."""
        if identifier in self.callbacks:
            del self.callbacks[identifier]

    def update(self, value) -> None:
        """Updates the value and calls all registered callbacks."""
        self.value = value
        for callback in self.callbacks.values():
            callback(value)


class EngineBoundType(type):
    """A metaclass that binds a class to a single audio engine instance.

    This allows for a simplified syntax in the live coding environment, where
    the user doesn't have to explicitly pass the engine instance to every
    object that needs it.
    """
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
    """A Python wrapper for the C++ Synth class.

    This class provides a more Pythonic interface to the underlying C++ synth
    object, and includes methods for wavetable generation and management.
    """
    WAVES = {
        'sine': lambda table_size: np.sin(np.linspace(0, 2 * np.pi, table_size, endpoint=False)).astype(np.float32),
        'square': lambda table_size: np.sign(np.sin(np.linspace(0, 2 * np.pi, table_size, endpoint=False))).astype(np.float32),
        'saw': lambda table_size: np.linspace(-1, 1, table_size, endpoint=False).astype(np.float32),
        'triangle': lambda table_size: 1-2*np.abs(np.linspace(-1, 1, table_size, endpoint=False)).astype(np.float32)
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
        self.freq(frequency)
        self.amp(amplitude)
        self.phase(offset)
        self.start()
    
    def regen(self, rebuild:bool = True, update:bool = True, norm:bool = True) -> None:
        """Rebuilds the wavetable and optionally updates the engine."""
        if rebuild:
            wavetable = self.wave_fn(self.table_size, **self.fn_args)
            # Normalize the table to be between -1.0 and 1.0
            if norm:
                wavetable /= np.max(np.abs(wavetable))
        self.wavetable = wavetable
        if update:
            self.ptr.update_wavetable(self.wavetable)

    def name(self) -> str:
        """Returns the name of the synth."""
        return self.synth_name
    
    def start(self) -> None:
        """Starts the synth."""
        self.ptr.start()

    def stop(self) -> None:
        """Stops the synth."""
        self.ptr.stop()

    def playing(self) -> bool:
        """Returns True if the synth is currently playing."""
        return self.ptr.is_playing()

    def freq(self, freq:float = None) -> None | float:
        """Gets or sets the frequency of the synth."""
        if freq == None:
            return self.ptr.get_frequency()
        else:
            self.ptr.set_frequency(freq)

    def phase(self, offset:float = None) -> None | float:
        """Gets or sets the phase offset of the synth."""
        if offset == None:
            return self.ptr.get_phase_offset()
        else:
            self.ptr.set_phase_offset(offset % 1.0)

    def amp(self, amp:float = None) -> None | float:
        """Gets or sets the amplitude of the synth."""
        if amp == None:
            return self.ptr.get_amplitude()
        else:
            self.ptr.set_amplitude(amp)

    def wave(self, wave_fn:callable = None, fn_args:dict = {}, norm:bool = True) -> None | Callable:
        """Gets or sets the wavetable function for the synth."""
        if wave_fn == None:
            return self.wave_fn
        else:
            self.wave_fn = wave_fn
            self.regen(norm=norm)
    
class Patch(metaclass=EngineBoundType):
    """A Python wrapper for the C++ Patch class.

    This class provides a more Pythonic interface to the underlying C++ patch
    object.
    """
    def __init__(self, patch_name:str, synth:str|Synth, channels:list[int]):
        self.engine = self.__class__.get_engine()
        self.patch_name = patch_name
        if isinstance(synth, str):
            synth_name = synth
        else:
            synth_name = synth.name()
        self.synth_name = synth_name
        self.ptr = self.engine.get_or_create_patch(self.patch_name, self.synth_name, channels)

    def get_synth_name(self) -> str:
        """Returns the name of the synth being patched."""
        return self.synth_name
    
    def synth(self, s:str|Synth|None = None) -> None | str:
        """Gets or sets the synth being patched."""
        if s == None:
            self.synth_name = self.ptr.get_synth_name()
            return self.synth_name
        if isinstance(s, str):
            synth_name = s
        else:
            synth_name = s.name()
        self.ptr.set_synth_name(synth_name)
        self.synth_name = synth_name


    def ch(self, c:list[int]|None = None) -> None | list[int]:
        """Gets or sets the list of channels being patched into."""
        if c == None:
            return self.ptr.get_channels()
        else:
            self.ptr.set_channels(c)

class Master(metaclass=EngineBoundType):
    """A class for controlling global engine parameters."""
    def __init__(self):
        self.engine = self.__class__.get_engine()

    def vol(self, v:float|None = None) -> None | float:
        """Gets or sets the master volume of the engine."""
        if v == None:
            return self.engine.get_master_volume()
        else:
            self.engine.set_master_volume(v)

    def getSynths(self) -> list[str]:
        """Returns a list of all synths currently in use."""
        return self.engine.list_synths()

    def getPatches(self) -> list[str]:
        """Returns a list of all patches currently in use."""
        return self.engine.list_patches()
    
    def stopAll(self) -> None:
        """Stops all synths in the engine."""
        self.engine.stop_all()

    def shutdown(self) -> None:
        """Shuts down the audio engine and terminates all streams."""
        self.engine.shutdown()


def run(emulator=True, nCh=4):
    """The main entry point for the Oscar live coding environment."""
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

    if emulator:
        try:
            for deviceName in devices:
                print(deviceName)
                if "OSCAR Renderer" in str(deviceName):
                    chosen_index = devices.index(deviceName)
                    break
        except Exception as e:
            print("Could not bind to OSCAR Renderer. Check that it's running and try again.")
            sys.exit(1)
    else:
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
   
    # Bind the audio engine to the high-level classes.
    Synth.bind_engine(engine)
    Patch.bind_engine(engine)
    Master.bind_engine(engine)
    
    print("\nEngine Initialization Completed\n")
    
    master = Master()
    scope = Renderer(nCh=4)
    vars = globals().copy()
    vars.update({
        'master': master,
        'scope': scope
        })


    repl = code.InteractiveConsole(locals=vars)
    repl.write("--- Oscar Live Coding Session ---\n")
        
    HOST, PORT = "localhost", 5555
    sel = selectors.DefaultSelector()
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setblocking(False)
    server_socket.bind((HOST, PORT))
    server_socket.listen()
    
    print(f"--- Listening for VS Code on {HOST}:{PORT} ---")
    sel.register(sys.stdin, selectors.EVENT_READ)
    sel.register(server_socket, selectors.EVENT_READ)

    while True:
        # Check for I/O activity from keyboard or network
        events = sel.select(timeout=0.01) # Use a short timeout
        for key, mask in events:
            if key.fileobj == server_socket:
                conn, addr = server_socket.accept()
                conn.setblocking(False)
                sel.register(conn, selectors.EVENT_READ)
            elif key.fileobj not in [sys.stdin, server_socket]:
                conn = key.fileobj
                data = conn.recv(4096)
                if data:
                    code_to_run = data.decode('utf-8')
                    for line in code_to_run.splitlines():
                        repl.push(line)
                    repl.push('\n')
                else:
                    sel.unregister(conn)
                    conn.close()
            else: # Input from stdin
                line = sys.stdin.readline()
                if not line: raise EOFError
                repl.push(line)

if __name__ == '__main__':
    try:
        run()
    except (RuntimeError, KeyboardInterrupt, EOFError):
        print("\nExiting Oscar.")
    finally:
        oscar_server.terminate()