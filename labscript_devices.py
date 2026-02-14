"""
user_devices/NI_DAQmx_PhotonCounter/labscript_devices.py
"""
from labscript import IntermediateDevice, set_passed_properties


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

    def generate_code(self, hcdf5_file):
        IntermediateDevice.generate_code(self, hcdf5_file)
        # The parent's generate_code creates the group. Access it via
        # the underlying h5py File object, not the wrapper.
        grp = hcdf5_file['devices'].require_group(self.name)
        grp.attrs['stop_time'] = self.pseudoclock_device.stop_time
