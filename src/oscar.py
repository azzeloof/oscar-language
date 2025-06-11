import code
import oscar_server
import time
import sys


def run():
    """
    A script to discover, select, and initialize an audio device
    using the oscar_server module.
    """
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