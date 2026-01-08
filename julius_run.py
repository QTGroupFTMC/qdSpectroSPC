import mainControl
from enum import Enum
from importlib import import_module
import matplotlib.pyplot as plt

import connectionConfig as conCfg
import PBcontrol as PBctl
import sequenceControl as seqCtl

# Define t_min, time resolution of the PulseBlaster, given by 1/(clock frequency):
t_min = 1e3/conCfg.PBclk #in ns


MAPPING_CHANNEL_NUMBER = {
	'PB_I': 0, 
	'PB_Q': 1, 
	'PB_STARTtrig': 2, 
	'PB_DAQ': 3, 
	'PB_AOM': 4, 
	'PB_MW': 5
	}
MAPPING_NUMBER_CHANNEL = {v:k for k,v in MAPPING_CHANNEL_NUMBER.items()}

class MeasurementConfig(Enum):
	""" Contains all possible measurements """
	
	COR_SPECT:str = 'correlSpecconfig'
	ESR: str = 'ESRconfig'
	OPT_READ_DELAY: str = 'optimReadoutDelay'    # neplotina impulsu sekos, paziureti
	REPOL_SLOW:str = 'repolarizationConfig_slow'
	RABI:str = 'Rabiconfig'
	T1:str = 'T1config'
	T2:str = 'T2config'
	XY8:str = 'XY8config'

SPC_mode_implemented = {
	MeasurementConfig.COR_SPECT:False,
	MeasurementConfig.ESR: True,
	MeasurementConfig.OPT_READ_DELAY: False, 
	MeasurementConfig.RABI: True,
	MeasurementConfig.T1: False,
	MeasurementConfig.T2: False,
	MeasurementConfig.XY8: False,
	}

PLOT_PULSE_SEQUENCE = True
RUN_EXPERIMENT = False



if __name__ == "__main__":
	#expConfigFile = 'ESRconfig'

	expConfigFile_enum=MeasurementConfig.REPOL_SLOW
	
	expConfigFile = expConfigFile_enum.value
	expCfg = import_module(expConfigFile)	

	sequence = expCfg.sequence
	plot_pulse_seq = expCfg.plotPulseSequence
	sequenceArgs = expCfg.updateSequenceArgs()  # duration for ESR
	expParamList = expCfg.updateExpParamList()
	pb_channels = expCfg.PBchannels
	
	seq_arg_list = [expCfg.scannedParam[-1]]
	seq_arg_list.extend(sequenceArgs)

	# Pulse Blaster must be on for this to work
	if sequence == 'ESRseq':
		instructionArray=PBctl.programPB(sequence,sequenceArgs,use_SPC=True)
	else:
		instructionArray=PBctl.programPB(sequence,seq_arg_list,use_SPC=True)		


	if PLOT_PULSE_SEQUENCE:
		plt.figure(0)
		[t_us,channelPulses,yTicks]=seqCtl.plotSequence(instructionArray,pb_channels)
		for channel in channelPulses:
			plt.plot(t_us, list(channel))
			plt.yticks(yTicks)
			plt.xlabel('time (us)')
			plt.ylabel('channel')
			# If we are plotting a Rabi with pulse length <5*t_min, warn the user in the sequence plot title that the instructions sent to the PulseBlaster microwave channel are for a 5*t_min pulse, but that the short pulse flags are simultaneously pulsed to produce the desired pulse length
			if sequence == 'RabiSeq' and (seq_arg_list[0]<(5*t_min)):
				plt.title('Pulse Sequence plot (at last scan point). Close to proceed with experiment...\n(note: we plot the instructions sent to the PulseBlaster (PB) for each channel. For microwave pulses<',5*t_min,'ns, the microwave\nchannel (PB_MW) is instructed to pulse for',5*t_min,'ns, but the short-pulse flags of the PB are pulsed simultaneously (not shown) to\nproduce the desired output pulse length at PB_MW. This can be verified on an oscilloscope.)', fontsize=7)
			else:
				plt.title(f'Pulse Sequence: {sequence}')
		plt.show()		


	if RUN_EXPERIMENT:
		mainControl.runExperiment(expConfigFile)