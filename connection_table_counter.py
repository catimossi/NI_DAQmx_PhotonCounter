
from labscript import *
from labscript import AnalogOut
from labscript_devices.DummyPseudoclock.labscript_devices import DummyPseudoclock
from labscript_devices.DummyIntermediateDevice import DummyIntermediateDevice
from labscript_devices.NI_DAQmx.models.NI_PXIe_6738 import NI_PXIe_6738
from labscript_devices.NI_DAQmx.models.NI_PXIe_6363 import NI_PXIe_6363
from labscript_devices.IMAQdxCamera.labscript_devices import IMAQdxCamera
from labscript_devices.PrawnBlaster.labscript_devices import PrawnBlaster

from user_devices.IDS_PeakCamera.labscript_devices import IDS_PeakCamera

from user_devices.NI_DAQmx_PhotonCounter.labscript_devices import NI_DAQmxPhotonCounter

# Import the devices.
from user_devices.BBD301.labscript_devices import BBD301

def ct():
    SLOT_6738 = "PXI1Slot3"   # EXACT name from NI-MAX
    SLOT_6363 = "PXI1Slot2"   # EXACT name from NI-MAX

    # #### JL addition of pulseblaster 
    prawn = PrawnBlaster(
        name                = 'prawn', 
        com_port            = 'COM11', 
        num_pseudoclocks    = 1,
        pico_board          = 'pico2'
    )
    clk = prawn.clocklines[0]


     #intermediatedevice = DummyIntermediateDevice('intermediatedevice', parent_device=clk)
    #camera_trigger = Trigger('camera_trigger', parent_device=intermediatedevice, connection='trigger')

    # Key: provide clock_terminal but make it 'internal' by leaving it empty
    # ni6738 = NI_PXIe_6738(
    #     'ni6738',
    #     clk,
    #     MAX_name=SLOT_6738,
    #     clock_terminal='' ,         # <-- empty string means "use internal/Onboard clock"
    #     max_AO_sample_rate=100000.00000000001,
    # )

    ni6363 = NI_PXIe_6363(
        'ni6363',
        clk,
        MAX_name=SLOT_6363,
        clock_terminal=f'/{SLOT_6363}/PFI12',          # <-- empty string means "use internal/Onboard clock"
        acquisition_rate=100.0,
        #max_AI_multi_chan_rate=1000.0,
        #max_DO_sample_rate=1000.0
    )

    # # Define digital outs on 6363
    # #make sure to define an even number of channels for Labscript to be happy
    # DigitalOut(name='do6363_0', parent_device=ni6363, connection='port0/line0')
    # DigitalOut(name='do6363_1', parent_device=ni6363, connection='port0/line1')
    # DigitalOut(name='do6363_2', parent_device=ni6363, connection='port0/line2')
    # DigitalOut(name='do6363_3', parent_device=ni6363, connection='port0/line3')
    # DigitalOut(name='MRR_TRIG_do', parent_device=ni6363, connection='port0/line4')
    # DigitalOut(name='MOT_SHUTTER_do', parent_device=ni6363, connection='port0/line5')
    # DigitalOut(name='MRR_SHUTTER_do', parent_device=ni6363, connection='port0/line6')
    # DigitalOut(name='LCR_do', parent_device=ni6363, connection='port0/line7')

    # ADD the counter as a separate device:
    photon_counter = NI_DAQmxPhotonCounter(
        name='photon_counter',
        parent_device=clk,
        #connection='internal',
        MAX_name=SLOT_6363,
        counter_channel='ctr3',
        photon_input_terminal=f'/{SLOT_6363}/PFI5',  # wire your photon source here
        sample_clock_terminal='',  # None = internal clock (matches DummyPseudoclock)
        counter_sample_rate=100000,
        start_trigger_terminal=f'/{SLOT_6363}/PFI12'
    )

    # bbd = BBD301(
    #     name='bbd301',
    #     parent_device=clk,
    #     serial_number='103512594',  # your actual serial number
    #     num_channels=1,
    # )

    # Make sure to define an even number of channels for Labscript to be happy
    # ao0 = AnalogOut('ao0',     ni6738, 'ao0')
    # ao1 = AnalogOut('ao1', ni6738, 'ao1')
    # ao2 = AnalogOut('ao2',     ni6738, 'ao2')
    # ao3 = AnalogOut('ao3', ni6738, 'ao3')
    # ao4 = AnalogOut('ao4',     ni6738, 'ao4')
    # ao5 = AnalogOut('ao5', ni6738, 'ao5')
    # ao6 = AnalogOut('ao6',     ni6738, 'ao6')
    # ao7 = AnalogOut('ao7', ni6738, 'ao7')

    # cam_trig = NIDigitalTrigger('cam_trig', clk, ni6738, 'port0/line1') # the real trigger line

    # This line is purely to satisfy the NI-DAQmx driver's requirement for an
    # even number of digital channels in a task. It does not need to be
    # connected to anything physically.
    # dummy_do_for_even_samples = DigitalOut(
    #     'dummy_do_for_even_samples',
    #     parent_device=ni6738,
    #     connection='port0/line0' # Use any other unused line on the same port
    # )

    # cam_serial_number = '4108596607' #sn yellow 4103389953 blue 4108596607 red 4108596608

    # cam = IDS_PeakCamera(
    #     name=f'camera_{cam_serial_number}',
    #     parent_device=ni6738, 
    #     connection='port0/line0', #cheat: fake connection to make labscript happy
    #     serial_number=cam_serial_number, 
    #     minimum_recovery_time=0.005, # Override the default
    #     trigger_edge_type='rising', 
    #     trigger_duration=100*ms,
    #     camera_attributes={
    #         'trigger': 'On', # On/Off
    #         'format': 'Mono8', # Mono8/Mono12
    #         'exposure': 9.0, # 9 ms, using the wrapper property
    #         'fps': 5.0,   # required by base class (will be skipped at runtime)
    #         'gain': 1.0
    #     },
    #     manual_mode_camera_attributes={ # BLACS preview mode
    #         "trigger": "Off",
    #         "format": "Mono8",
    #         "exposure": 10.0,
    #         "fps": 5.0,               # shown in BLACS, not applied to hardware
    #         "gain": 1.0,
    #     },
    # )
    # cam.trigger_device = cam_trig  

if __name__ == '__main__':
     ct()
     start()
     stop(0.001)