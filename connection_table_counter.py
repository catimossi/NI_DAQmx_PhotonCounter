import labscript, sys
from labscript import *
from labscript import AnalogOut
from labscript_devices.DummyPseudoclock.labscript_devices import DummyPseudoclock
from labscript_devices.DummyIntermediateDevice import DummyIntermediateDevice
from labscript_devices.NI_DAQmx.models.NI_PXIe_6738 import NI_PXIe_6738
from labscript_devices.NI_DAQmx.models.NI_PXIe_6363 import NI_PXIe_6363
from labscript_devices.IMAQdxCamera.labscript_devices import IMAQdxCamera
from user_devices.NI_DAQmx_PhotonCounter.labscript_devices import NI_DAQmxPhotonCounter

# ... existing master, clk, ni6738, ni6363 definitions ...

# REMOVE the set_property lines from ni6363:
# ni6363.set_property('counter_enabled', True, ...)   # DELETE
# ni6363.set_property('counter_channel', 'ctr0', ...) # DELETE
# ni6363.set_property('counter_sample_rate', ...)      # DELETE

# ADD the counter as a separate device:
photon_counter = NI_DAQmxPhotonCounter(
    name='photon_counter',
    parent_device=clk,
    connection='internal',
    MAX_name=SLOT_6363,
    counter_channel='ctr0',
    photon_input_terminal=f'/{SLOT_6363}/PFI0',  # wire your photon source here
    sample_clock_terminal=None,  # None = internal clock (matches DummyPseudoclock)
    counter_sample_rate=100000,
)