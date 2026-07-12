
import unittest
import numpy as np
import time
import threading
import oscar_server
import sys
import socket

import os
# Add the project's source directory to the Python path.
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "src")))
from oscar import Synth, Patch, Master, MidiInput, run

class TestOscarFramework(unittest.TestCase):
    """A test suite for the Oscar live coding framework.

    This suite covers core functionality, error handling, and stability to ensure
    the framework is reliable for live performance environments.
    """

    @classmethod
    def setUpClass(cls):
        """Initializes the PortAudio library and the audio engine once for all tests."""
        try:
            oscar_server.initialize()
            devices = oscar_server.get_device_details()
            if not devices:
                raise unittest.SkipTest("No audio devices found. Cannot run integration tests.")
            
            # Find the first device with output channels to use for testing.
            output_device_index = -1
            for i, device in enumerate(devices):
                if device.max_output_channels > 0:
                    output_device_index = i
                    break
            
            if output_device_index == -1:
                raise unittest.SkipTest("No audio devices with output channels found.")

            cls.engine = oscar_server.AudioEngine.get_instance()
            cls.engine.initialize_devices([output_device_index])
            Synth.bind_engine(cls.engine)
            Patch.bind_engine(cls.engine)
            Master.bind_engine(cls.engine)
            cls.master = Master()
        except Exception as e:
            print(f"Failed to initialize audio engine for tests: {e}")
            raise

    @classmethod
    def tearDownClass(cls):
        """Terminates the PortAudio library after all tests are complete."""
        cls.engine.shutdown()
        oscar_server.terminate()

    def setUp(self):
        """Cleans up synths and patches before each individual test."""
        self.engine.stop_all()
        # Ensure a clean state by deleting all existing synths and patches.
        for s_name in self.engine.list_synths():
            self.engine.delete_synth(s_name)
        for p_name in self.engine.list_patches():
            self.engine.delete_patch(p_name)
        # Allow a brief moment for the audio engine to process the deletions.
        time.sleep(0.1)

    # --- Core Functionality Tests ---

    def test_01_initialization_and_device_listing(self):
        """Verifies that the server initializes and can enumerate audio devices."""
        devices = oscar_server.get_device_details()
        self.assertIsInstance(devices, list)
        self.assertGreater(len(devices), 0)

    def test_02_synth_and_patch_creation(self):
        """Tests the basic functionality of the Python wrappers for Synth and Patch."""
        s1 = Synth("s1", frequency=220.0, amplitude=0.7)
        self.assertEqual(s1.name(), "s1")
        self.assertAlmostEqual(s1.freq(), 220.0)
        p1 = Patch("p1", s1, [0])
        self.assertEqual(p1.ptr.get_synth_name(), "s1")
        self.assertEqual(p1.ch(), [0])

    # --- Graceful Failure and Error Handling Tests ---

    def test_10_invalid_argument_type(self):
        """Ensures that passing incorrect data types to engine functions raises a TypeError."""
        s = Synth("error_synth")
        with self.assertRaises(TypeError):
            s.freq("not-a-number")
        with self.assertRaises(TypeError):
            s.amp([1, 2, 3])
        with self.assertRaises(TypeError):
            Patch("p_error", s, "not-a-list")

    def test_11_out_of_bounds_channel(self):
        """Verifies that patching to an out-of-bounds channel does not crash the engine."""
        s = Synth("oob_synth")
        # The C++ render loop is expected to safely ignore out-of-bounds channels.
        p = Patch("oob_patch", s, [99, 100])
        s.start()
        time.sleep(0.1) # Allow the engine to render a few frames.
        s.stop()
        # The test succeeds if no crash occurs.
        self.assertTrue(True)

    def test_12_patching_non_existent_synth(self):
        """Ensures that creating a patch for a non-existent synth raises a RuntimeError."""
        with self.assertRaises(RuntimeError):
            Patch("p_no_synth", "no_such_synth", [0])

    # --- Advanced Functionality and Live Workflow Tests ---

    def test_20_dynamic_repatching(self):
        """Tests the ability to change a patch's synth dynamically."""
        s1 = Synth("repatch_s1")
        s2 = Synth("repatch_s2")
        p = Patch("repatch_p", s1, [0])
        self.assertEqual(p.ptr.get_synth_name(), "repatch_s1")
        p.synth(s2)
        self.assertEqual(p.ptr.get_synth_name(), "repatch_s2")

    def test_21_duplicate_synth_name(self):
        """Verifies that creating a synth with a duplicate name returns the existing instance."""
        s1 = Synth("duplicate_synth")
        s2 = Synth("duplicate_synth")
        # The pointers to the underlying C++ objects should be identical.
        self.assertEqual(s1.ptr, s2.ptr)

    def test_22_state_inspection(self):
        """Tests the accuracy of the state inspection functions."""
        s1 = Synth("state_s1")
        s2 = Synth("state_s2")
        Patch("state_p1", s1, [0])
        Patch("state_p2", s2, [1])
        self.assertCountEqual(self.master.getSynths(), ["state_s1", "state_s2"])
        self.assertCountEqual(self.master.getPatches(), ["state_p1", "state_p2"])
        self.engine.delete_synth("state_s1")
        time.sleep(0.1)
        self.assertCountEqual(self.master.getSynths(), ["state_s2"])
        self.assertCountEqual(self.master.getPatches(), ["state_p2"])

    # --- Resource Management and Stability Tests ---

    def test_30_midi_thread_cleanup(self):
        """Verifies that the MidiInput threads can be stopped gracefully."""
        devices = MidiInput.devices()
        if not devices:
            self.skipTest("No MIDI devices found, skipping thread cleanup test.")
        
        midi_in = MidiInput(device=devices[0])
        self.assertTrue(midi_in.listen_thread.is_alive())
        self.assertTrue(midi_in.parse_thread.is_alive())
        
        midi_in.stop()
        time.sleep(0.1) # Give the threads a moment to shut down.
        self.assertFalse(midi_in.listen_thread.is_alive())
        self.assertFalse(midi_in.parse_thread.is_alive())

    def test_31_rapid_creation_deletion(self):
        """Tests the creation and deletion of many objects to check for instability."""
        for i in range(100):
            s_name = f"stress_s_{i}"
            p_name = f"stress_p_{i}"
            s = Synth(s_name)
            Patch(p_name, s, [0])
        
        time.sleep(0.1)
        self.assertEqual(len(self.master.getSynths()), 100)
        self.assertEqual(len(self.master.getPatches()), 100)

        for i in range(100):
            self.engine.delete_synth(f"stress_s_{i}")

        time.sleep(0.1)
        self.assertEqual(len(self.master.getSynths()), 0)
        self.assertEqual(len(self.master.getPatches()), 0)

if __name__ == '__main__':
    # Note: The REPL tests are in a separate file (test_repl.py) as they
    # require a running server instance and client interaction.
    unittest.main()
