# Rabiconfig.py
# Copyright 2018 Diana Prado Lopes Aude Craik

# Permission is hereby granted, free of charge, to any person 
# obtaining a copy of this software and associated documentation
# files (the "Software"), to deal in the Software without
# restriction, including without limitation the rights to use, copy,
# modify, merge, publish, distribute, sublicense, and/or sell copies
# of the Software, and to permit persons to whom the Software is 
# furnished to do so, subject to the following conditions:

# The above copyright notice and this permission notice shall be
# included in all copies or substantial portions of the Software.

# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
# NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS
# BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN
# ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN
# CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

"""
Repolarization experiment config
wait until the system depolarizes by itself, repolarizew it with green and measure repolarization kinetics


-- Contrast setting --
From signal and background counts, the script will calculate contrast based on one of two formulas, 
defined by the contrastMode variable. If contrastMode is set to 'ratio_SignalOverReference', contrast is 
defined as the ratio of signal to background. If contrastMode is set to 'ratio_DifferenceOverSum', contrast 
is defined as the ratio of the difference between signal and background to the sum of signal and background.
 The user may also select a 'signalOnly' contrast mode, where only the signal counts are plotted and the 
 background counts are ignored.

-- Averaging options --
By default, for each scan point, the script calculates the contrast as a function of the averaged signal counts (averaged over the Nsamples signal readings at a given scan point) and the averaged background counts - e.g. if the contastMode is set to ratio_SignalOverReference, the contrast is, by default, calculated by dividing the average of the Nsamples of signal by the average of the Nsamples of background. If you prefer to instead calculate contrast as a function of subsequent signal and background samples and then average across all samples, set the shotByShotNormalization option to True -e.g. if contrastMode is ratio_SignalOverReference and shotByShotNormalization is set to True, the contrast will be calculated by dividing each signal sample by the subsequent background sample taking the average of these ratios.

The first time the script scans over the microwave pulse durations, it does so in order from the shortest to the longest pulse duration. If Navg>1, the script then repeats the scan Navg times and averages the results. By default, the order of the scan points is randomized for all but the first scan. If you wish to turn off this randomization, set the randomize option below to False.

-- Plotting options --
Set livePlotUpdate to True to plot the data as it is acquired. Note that, after the first scan is completed, the plot will only update at the end of every subsequent scan. If livePlotUpdate is set to False, the data will only be plotted at the end of the experiment.

Set plotPulseSequence to True to plot the pulse sequence which has been programmed into the PulseBlaster. Note that the program will wait for the user to close this plot before continuing.

-- Saving options --
The user can choose how often the data is saved. For the first scan, there is an option to save at intervals of saveSpacing_inScanPts (i.e. if this variable is set to 2, the script will resave the data at every other scan point). For subsequent scans, the script will resave the data at the end of a scan, for averaging runs spaced by intervals of saveSpacing_inAverages (e.g. if this is set to 3, the data will be resaved after every 3 averages). Regardless of how the user sets these options, data will always be saved at the end of the first scan and at the end of the experiment (i.e. after the last averaging run).

To run this script:
 1) Edit connectionConfig.py to define the PulseBlaster, SRS and DAQ channel connections being used in your setup.
 2) Edit the user inputs section below.
 3) Run the script. From a windows command prompt, the script can be run by calling python mainControl.py Rabiconfig
 
 User inputs:
 *startPulseDuration: shortest pulse duration in scan, in nanoseconds. Note: this must be an integer multiple of t_min, the time resolution of your PulseBlaster card (i.e.t_min = 1/(clock frequency))
 *endPulseDuration:  longest pulse duration in scan, in nanoseconds. Note: this must be an integer multiple of t_min, the time resolution of your PulseBlaster card (i.e.t_min = 1/(clock frequency))
 *N_scanPts: number of points in the scan.
 *microwavePower: output power of the SRS signal generator, in dBm. CAUTION: this should not exceed the input power of any amplifiers connected to the SRS output.
 *microwaveFrequency: microwave frequency output by SRS signal generator (Hz)
 *t_AOM: duration of AOM pulse (ns).
 *t_readoutDelay: delay between start of AOM pulse and DAQ readout pulse (ns). The optimum delay can be found using optimReadoutDelay.py (see step 54 in our protocol paper)
 *Nsamples: number of fluorescence measurement samples to take at each scan point.
 *Navg: number of averaging runs (i.e. number of times the pulse length scan is repeated).
 *DAQtimeout: amount of time (in seconds) for which the DAQ will wait for the requested number of samples to become available (ie. to be acquired)
 *contrastMode: set this to one of 'ratio_SignalOverReference', 'ratio_DifferenceOverSum' or 'signalOnly', depending on which contrast mode you want to use (see 'Contrast setting' description above)
 *livePlotUpdate: set this to True to update the plot as data is acquired (see 'Plotting options' above)
 *plotPulseSequence: set this to True to plot the pulse sequence at the start of the experiment (see 'Plotting options' above)
 *plotXaxisUnits: sets x-axis units on the data plot. Select from ns, us or ms
 *xAxisLabel: sets x-axis label on the data plot
 *saveSpacing_inScanPts: interval, in number of frequency points, at which data is saved during the first scan.
 *saveSpacing_inAverages: interval, in number of averaging runs, at which data is saved after the first complete scan.
 *savePath: path to folder where data will be saved. By default, data is saved in a folder called Saved_Data in the directory where this script is saved
 *saveFileName: file name under which to save the data. This name will later be augmented by the date and time at which the script was run.
 *shotByShotNormalization: set this option to True to do shot by shot contrast normalization (see 'Averaging Options' above).
 *randomize: set this option to True to randomize the order of frequency points in all scans after the first one.
"""
#Imports
from spinapi import ns,us,ms
import os
import numpy as np
from time import localtime, strftime
from connectionConfig import *
# Define t_min, time resolution of the PulseBlaster, given by 1/(clock frequency):
t_min = 1e3/PBclk #in ns
#-------------------------  USER INPUT  ---------------------------------------#

# Detector choice: use single photon counters instead of analog input (instead of diode, for example)
use_SPC = True
t_count_duration = 1*us # photon counting interval at each measurement half-cycle
# Readout_delay scan parameters:----------------------------------------------------
# Start delay (in nanoseconds):
start_delay = 0
end_delay = 3000

# Number of pulse length steps:
N_scanPts = 75
# Microwave power output from SRS(dBm) - DO NOT EXCEED YOUR AMPLIFIER'S MAXIMUM INPUT POWER:
microwavePower = -20
# Microwave frequency (Hz):
microwaveFrequency = 2.729e9 
# Pulse sequence parameters:----------------------------------------------------
 
# AOM pulse duration (ns)
t_dark = 100*us
t_AOM = 50*us
# Readout delay (ns)
t_readoutDelay = 2.3*us
# Number of fluorescence measurement samples to take at each pulse length point:
Nsamples = 40_000			# only one to minimize duration; each sample adds 0.8us

# Number of averaging runs to do:
Navg = 1
#DAQ timeout, in seconds:
DAQtimeout = 10
# Plotting options--------------------------------------------------------------
# Contrast mode
contrastMode ='ratio_SignalOverReference'
# Live plot update option
livePlotUpdate = True
# Plot pulse sequence option  - set to true to plot the pulse sequence
plotPulseSequence = True
# Plot x axis unit multiplier (ns, us or ms)
plotXaxisUnits = ns
# Plot x axis label
xAxisLabel = 'Microwave pulse length (ns)'
# Save options------------------------------------------------------------------
# Save interval for first scan through all pulse length points:
saveSpacing_inScanPts = 1
# Save interval in averaging runs:
saveSpacing_inAverages = 3
# Path to folder where data will be saved:
savePath = os.getcwd()+"\\Saved_Data\\"
# File name for data file
saveFileName = "RepolarizationSlow_"
# Averaging options:------------------------------------------------------------
# Option to do shot by shot contrast normalization:
shotByShotNormalization = False
# Option to randomize order of scan points
randomize = True
#------------------------- END OF USER INPUT ----------------------------------#

scannedParam = np.linspace(start_delay, end_delay, N_scanPts, endpoint=True) 
#Sequence string:
sequence = 'RepolSeqSlow'
#Scan start Name
scanStartName = 'start_delay'
#Scan end Name
scanEndName = 'end_delay'
#PB channels
PBchannels = {'AOM':AOM,'uW':uW,'DAQ':DAQ,'STARTtrig':STARTtrig}
#Sequence args
sequenceArgs = [t_AOM, t_dark, t_readoutDelay, t_count_duration]
#Make save file path
dateTimeStr = strftime("%Y-%m-%d_%Hh%Mm%Ss", localtime())
dataFileName = savePath + saveFileName+ dateTimeStr +".txt"
#Make param file path
paramFileName = savePath + saveFileName+dateTimeStr+'_PARAMS'+".txt"
#Param file save settings
formattingSaveString = "%s\t%d\n%s\t%d\n%s\t%d\n%s\t%d\n%s\t%f\n%s\t%f\n%s\t%f\n%s\t%f\n%s\t%f\n%s\t%f\n%s\t%r\n%s\t%r\n%s\t%r\n%s\t%d\n%s\t%d\n%s\t%s\n"
expParamList = ['N_timePts:',N_scanPts,
				'Navg:',Navg,
				't_count_duration', t_count_duration,
				'Nsamples:',Nsamples,
				'startPulseDuration:',scannedParam[0],
				'endPulseDuration:',scannedParam[-1],
				'microwavePower:',microwavePower,
				'microwaveFrequency',microwaveFrequency,
				't_AOM:',t_AOM, 
				't_dark:',t_dark, 
				't_readoutDelay:',t_readoutDelay,
				'shotByShotNormalization:',shotByShotNormalization,
				'randomize:',randomize,
				'plotPulseSequence:',plotPulseSequence,
				'saveSpacing_inScanPts:',saveSpacing_inScanPts,
				'saveSpacing_inAverages:',saveSpacing_inAverages,
				'dataFileName:',dataFileName]

def updateSequenceArgs():
	sequenceArgs = [t_AOM, t_dark, t_readoutDelay, t_count_duration]
	return sequenceArgs
	
def updateExpParamList():
	expParamList = ['N_timePts:',N_scanPts,
				 	'Navg:',Navg,
					't_count_duration', t_count_duration,
					'Nsamples:',Nsamples,
					'startPulseDuration:',scannedParam[0],
					'endPulseDuration:',scannedParam[-1],
					'microwavePower:',microwavePower,
					'microwaveFrequency',microwaveFrequency,
					't_AOM:',t_AOM, 
					't_dark:',t_dark, 
					't_readoutDelay:',t_readoutDelay,
					'shotByShotNormalization:',shotByShotNormalization,
					'randomize:',randomize,
					'plotPulseSequence:',plotPulseSequence,
					'saveSpacing_inScanPts:',saveSpacing_inScanPts,
					'saveSpacing_inAverages:',saveSpacing_inAverages,
					'dataFileName:',dataFileName]
	return expParamList