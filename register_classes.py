"""
user_devices/NI_DAQmx_PhotonCounter/register_classes.py
"""
import labscript_devices

labscript_devices.register_classes(
    'NI_DAQmxPhotonCounter',
    BLACS_tab='user_devices.NI_DAQmx_PhotonCounter.blacs_tabs.NI_DAQmxPhotonCounterTab',
   )