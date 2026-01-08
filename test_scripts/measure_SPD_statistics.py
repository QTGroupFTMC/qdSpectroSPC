"""
Measure SPD statistics: 
  create and perform DAQ counting task for a desired number of samples 
  save the results to a file
"""
import matplotlib.pyplot as plt
import numpy as np
import os
import pathlib
import sys

from collections import namedtuple
import math
from nidaqmx import Task
from nidaqmx.constants import Edge, AcquisitionType, TriggerType
import PBcontrol as PBctl
from spinapi import PULSE_PROGRAM, Inst, ms, us, ns  
from spinapi import (
	pb_start_programming, 
	pb_stop_programming,
	pb_inst_pbonly,
	pb_start,
	pb_close,
	pb_get_error,
	pb_set_debug,
	pb_init,
	pb_core_clock,
	)


INTERNAL_COUNTER = "Dev1/ctr0"
COUNT_INPUT_SRC = "/Dev1/PFI12"

MAX_SAMPLING_RATE = 1_250_000
SAMPLE_CLOCK_SRC = "PFI3"

START_TRIGGER_SRC = "PFI8"

T_COUNT_DURATION = 1*ms
SAMPLE_COUNT = 10_000
REPEAT_COUNT = 10
READ_TIMEOUT = 20 # [s]


#PulseBlaster clock frequency (in MHz):
PBclk = 500         # [MHz]
t_min = 1e3/PBclk   # [ns] 

PB_I = 0
PB_Q = 1
PB_STARTtrig = 2
PB_DAQ = 3
PB_AOM = 4
PB_MW = 5

I = 2**PB_I
Q = 2**PB_Q
STARTtrig = 2**PB_STARTtrig
DAQ = 2**PB_DAQ
AOM = 2**PB_AOM
uW = 2**PB_MW

params = { 
	"T_COUNT_DURATION": (T_COUNT_DURATION, 1000, 'us'), 
	"SAMPLE_COUNT": (SAMPLE_COUNT, None, ''), 
	"REPEAT_COUNT": (REPEAT_COUNT, None, ''), 
	"INTERNAL_COUNTER": (INTERNAL_COUNTER, None, ''), 
	"COUNT_INPUT_SRC": (COUNT_INPUT_SRC, None, ''), 
	"MAX_SAMPLING_RATE": (MAX_SAMPLING_RATE, 1e3, 'kHz'), 
	"SAMPLE_CLOCK_SRC": (SAMPLE_CLOCK_SRC, None, ''),
	"START_TRIGGER_SRC": (START_TRIGGER_SRC, None, ''), 
	}




PBchannels = {'AOM':AOM,'uW':uW,'DAQ':DAQ,'STARTtrig':STARTtrig}
PBchannel = namedtuple('PBchannel',['channelNumber','startTimes','pulseDurations']) 

def programPB(t_count_duration:float):
	channels=make_seq(t_count_duration)
	channelBitMasks = sequenceEventCataloguer(channels)
	instructionArray=programSequence(channelBitMasks)
	return instructionArray

def make_seq(t_count_duration:float)->list[PBchannel]:
    t_startTrig = t_min*round(300*ns/t_min)
    t_readout = t_min*round(300*ns/t_min)
    t_readoutDelay = 2.3*us
    start_delay = t_min*round(1*us/t_min) 

    # DAQ channel
    start_count = start_delay + t_readoutDelay
    end_count = start_count + t_count_duration
    start_times = [start_count, end_count]
    pulse_durations = [t_readout]*2		
    DAQchannel = PBchannel(DAQ, start_times, pulse_durations)

    # AOM channel
    t_AOM = t_readoutDelay + t_count_duration + t_readoutDelay
    AOMchannel = PBchannel(AOM,[start_delay],[t_AOM])

    # PB channel
    uWchannel = PBchannel(uW,[],[])

    # Arm start trigger channel
    STARTtrigchannel = PBchannel(STARTtrig,[0],[t_startTrig])
    channels = [AOMchannel, DAQchannel, uWchannel, STARTtrigchannel]
    return channels

def sequenceEventCataloguer(channels):
	#Catalogs sequence events in terms of consecutive rising edges on the channels provided. Returns a dictionary, channelBitMasks, whose keys are event (rising/falling edge) times and values are the channelBitMask which indicate which channels are on at that time.
	eventCatalog ={} #dictionary where the keys are rising/falling edge times and the values are the channel bit masks which turn on/off at that time
	for channel in channels:
		channelMask = channel.channelNumber
		endTimes = [startTime + pulseDuration for startTime, pulseDuration in zip(channel.startTimes,channel.pulseDurations)]
		for eventTime in channel.startTimes+endTimes:
			eventChannelMask = channelMask
			if eventTime in eventCatalog.keys():
				eventChannelMask = eventCatalog[eventTime]^channelMask 
				#I'm XORing instead of ORing here in case someone has a zero-length pulse in the sequence. In that case, the XOR ensures that the channel does not turn on at the pulse start/end time. If we did an OR here, it would turn on and only turn off at the next event (which would have been a rising edge), so this would have given unexpected behaviour.
			eventCatalog[eventTime]=eventChannelMask
	channelBitMasks = {}
	currentBitMask=0
	channelBitMasks[0]=currentBitMask
	for event in sorted(eventCatalog.keys()):
		channelBitMasks[event]=currentBitMask^eventCatalog[event]
		currentBitMask = channelBitMasks[event]
	return channelBitMasks

def programSequence(channelBitMasks):
	eventTimes = list(channelBitMasks.keys())
	numEvents = len(eventTimes)
	eventDurations =list(np.zeros(numEvents-1))
	numInstructions = numEvents-1
	for i in range(0,numInstructions):
		if i == numInstructions-1:
			eventDurations[i] = eventTimes[i+1]-eventTimes[i]
		else:
			eventDurations[i] = eventTimes[i+1]-eventTimes[i]
	instructionArray = []
	bitMasks = list(channelBitMasks.values())
	start = [0]
	for i in range(0,numEvents-1):
		if i==(numEvents-2):
			instructionArray.extend([[bitMasks[i], Inst.BRANCH, start[0], eventDurations[i]]])
		else:
			instructionArray.extend([[bitMasks[i], Inst.CONTINUE, 0, eventDurations[i]]])
	
	#Program Pulseblaster
	configurePB()
	status = pb_start_programming(PULSE_PROGRAM)
	errorCatcher(status)
	startDone = False
	for i in range(0, len(instructionArray)):
		if startDone:
			status = pb_inst_pbonly(instructionArray[i][0],instructionArray[i][1],instructionArray[i][2],instructionArray[i][3])
			errorCatcher(status)
		else:
			start[0]= pb_inst_pbonly(instructionArray[0][0],instructionArray[0][1],instructionArray[0][2],instructionArray[0][3])
			errorCatcher(start[0])
			startDone = True
	status = pb_stop_programming()
	errorCatcher(status)
	status = pb_start()
	errorCatcher(status)
	status = pb_close()
	errorCatcher(status)
	return instructionArray


def errorCatcher(statusVar):
	if statusVar<0:
		print ('Error: ', pb_get_error())
		sys.exit()
		
def configurePB():
	pb_set_debug(1)
	status = pb_init()
	errorCatcher(status)
	pb_core_clock(PBclk)
	return 0

def plotSequence(instructions,channelMasks):
	scalingFactor = 0.8
	t_ns = [0,0]
	pulses ={}
	tDone = False
	channelPulses=[]
	for channelMask in channelMasks.values():
		pulses[channelMask]=[0,channelMask&instructions[0][0]]
		for i in range(0, len(instructions)):
			currentPulseLength = instructions[i][3]
			if not tDone:
				previousEdgeTime = t_ns[-1]
				nextEdgeTime = previousEdgeTime + currentPulseLength
				t_ns.append(nextEdgeTime)
				t_ns.append(nextEdgeTime)
				if i == (len(instructions)-1):
					tDone = True
			if i==len(instructions)-1:
				pulses[channelMask].append(channelMask&instructions[i][0])
				pulses[channelMask].append(channelMask&instructions[i][0])
			else:
				pulses[channelMask].append(channelMask&instructions[i][0])
				pulses[channelMask].append(channelMask&instructions[i+1][0])
		t_us = np.divide(t_ns,1e3)
		channelPulses.append(list(np.add(math.log(channelMask,2),np.multiply(list(pulses[channelMask]),scalingFactor/channelMask))))
	yTicks = np.arange(math.log(min(channelMasks.values()),2), 1+math.log(max(channelMasks.values()),2),1)
	return [t_us,channelPulses,yTicks]

def configure_SPD_read_task(readTask:Task):
    """ 
    Configure finite acquisition task
    Set the number of samples, 
        counter input, 
        arm trigger, 
        external sample clock, 
        signal filtering to avoid afterpulses 
    """
    ci_channel = readTask.ci_channels.add_ci_count_edges_chan(INTERNAL_COUNTER, edge=Edge.RISING)  
    ci_channel.ci_count_edges_term = COUNT_INPUT_SRC

    samples = SAMPLE_COUNT*2

    #Configure sample clock
    readTask.timing.cfg_samp_clk_timing(
        MAX_SAMPLING_RATE,
        SAMPLE_CLOCK_SRC,
        Edge.RISING,
        AcquisitionType.FINITE, 
        samples,
    )

    # Add a digital filter to the Sample Clock channel
    readTask.timing.samp_clk_dig_fltr_enable = True
    readTask.timing.samp_clk_dig_fltr_min_pulse_width = 100e-9  # 100 ns		

    #Configure start trigger
    readArmStartTrig = readTask.triggers.arm_start_trigger
    readArmStartTrig.trig_type = TriggerType.DIGITAL_EDGE
    readArmStartTrig.dig_edge_edge = Edge.RISING
    readArmStartTrig.dig_edge_src = START_TRIGGER_SRC


if __name__ == '__main__':
    

    # Actions
    PLOT_SEQUENCE = True
    MEASURE_BG = True

    SAVE_RESULTS = True
    SAVE_FOLDER = r'C:\Users\User\Desktop\Julius\Fast stepper scan\SPC_test_data\2025-12-29 SPD statistics'
    SAVE_FILE = 'fl_10_laser_OD2_25kcps_1ms.txt'
    SAVE_PATH = os.path.join(SAVE_FOLDER, SAVE_FILE)

    p = pathlib.Path(SAVE_PATH) 
    PAR_SAVE_PATH = p.with_name(p.stem + "_PARS" + p.suffix)

    # Configure pulse blaster
    instructionArray=programPB(T_COUNT_DURATION)

    if PLOT_SEQUENCE:
        plt.figure(0)
        [t_us,channelPulses,yTicks]=plotSequence(instructionArray,PBchannels)
        for channel in channelPulses:
            plt.plot(t_us, list(channel))
            plt.yticks(yTicks)
            plt.xlabel('time (us)')
            plt.ylabel('channel')
        plt.show()

    if MEASURE_BG:
        # read DAQ data
        for repeat in range(REPEAT_COUNT):
            readTask = Task()
            with readTask:
                configure_SPD_read_task(readTask)
                samples = 2*SAMPLE_COUNT
                cts = readTask.read(samples, READ_TIMEOUT)
                
                cts = np.array(cts)
                start_cts = cts[0::2]
                end_cts = cts[1::2]
                delta_cts = end_cts - start_cts
                print(sum(delta_cts))
            if SAVE_RESULTS:
                with open(SAVE_PATH, "a") as f:
                    np.savetxt(f, delta_cts.reshape(-1, 1), fmt="%.1f")
        if SAVE_RESULTS:
			# save paramters
			with open(PAR_SAVE_PATH, "w") as f: 
				for key, value in params.items(): 
					val, scaling_factor, unit = value
					if scaling_factor is not None:
						val = val/scaling_factor
					f.write(f"{key} = {val} {unit}\n")
    a = 1
