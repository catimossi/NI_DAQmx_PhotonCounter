"""
user_devices/NI_DAQmx_PhotonCounter/blacs_tabs.py
"""
from blacs.device_base_class import DeviceTab


class NI_DAQmxPhotonCounterTab(DeviceTab):
    
    def initialise_GUI(self):
        # No GUI widgets needed for a simple counter
        pass
    
    def initialise_workers(self):
        worker_initialisation_kwargs = self.connection_table.\
            find_by_name(self.device_name).properties.get(
                'connection_table_properties', {}
            )
        
        self.create_worker(
            'main_worker',
            'user_devices.NI_DAQmx_PhotonCounter.blacs_workers.NI_DAQmxPhotonCounterWorker',
            worker_initialisation_kwargs,
        )
        self.primary_worker = 'main_worker'