"""
user_devices/NI_DAQmx_PhotonCounter/labscript_devices.py
"""
import math
from labscript import IntermediateDevice, LabscriptError, set_passed_properties


class NI_DAQmxPhotonCounter(IntermediateDevice):
    """
    Labscript device for photon counting using an NI-DAQmx counter channel.
    """
    
    description = 'NI-DAQmx Photon Counter'
    allowed_children = []
    
    @set_passed_properties(
        property_names={
            'connection_table_properties': [
                'MAX_name',
                'counter_channel',
                'photon_input_terminal',
                'sample_clock_terminal',
                'counter_sample_rate',
                'start_trigger_terminal',],
            'device_properties': [],
        }
    )
    def __init__(self, name, parent_device,
                 MAX_name,
                 counter_channel='ctr0',
                 photon_input_terminal='/PXI1Slot2/PFI0',
                 sample_clock_terminal=None,
                 counter_sample_rate=100000,
                 start_trigger_terminal=None,   # <-- add this
                 **kwargs):
        IntermediateDevice.__init__(self, name, parent_device, **kwargs)
        self.BLACS_connection = MAX_name
        self.counter_sample_rate = counter_sample_rate
        self._acquisition = None  # set by acquire(); (t, number_of_counts) or None

    def acquire(self, t, number_of_counts):
        """Schedule a photon-counting acquisition.

        Args:
            t: Start time (seconds) in the labscript sequence. Stored in the
               shot file for reference; hardware start is determined by
               start_trigger_terminal.
            number_of_counts: Number of samples to acquire at counter_sample_rate.
               E.g. 50_000 at 100 kHz = 500 ms of data.
        """
        if self._acquisition is not None:
            raise LabscriptError(
                f"{self.name}: acquire() called twice in one shot. "
                "Only one acquisition window per shot is supported."
            )
        if int(number_of_counts) <= 0:
            raise LabscriptError(
                f"{self.name}: number_of_counts must be positive, "
                f"got {number_of_counts}."
            )
        self._acquisition = (t, int(number_of_counts))

    # Alias: photon_counter.start(n) works identically to photon_counter.acquire(t, n)
    start = acquire

    def generate_code(self, hdf5_file):
        IntermediateDevice.generate_code(self, hdf5_file)
        grp = hdf5_file['devices'].require_group(self.name)
        grp.attrs['stop_time'] = self.pseudoclock_device.stop_time
        if self._acquisition is not None:
            t, number_of_counts = self._acquisition
            grp.attrs['number_of_counts'] = number_of_counts
            grp.attrs['t_start'] = t
        else:
            # Fallback: fill the whole shot at the configured sample rate
            grp.attrs['number_of_counts'] = math.ceil(
                self.pseudoclock_device.stop_time * self.counter_sample_rate
            )
