#DAQ control
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
import nidaqmx
from  nidaqmx.constants import *
from connectionConfig import *
import sys

def configureDAQ(Nsamples):
	try:
		#Create and configure an analog input voltage task
		NsampsPerDAQread=2*Nsamples
		readTask = nidaqmx.Task()
		channel = readTask.ai_channels.add_ai_voltage_chan(DAQ_APDInput,"",TerminalConfiguration.RSE,minVoltage,maxVoltage,VoltageUnits.VOLTS)
		#Configure sample clock
		readTask.timing.cfg_samp_clk_timing(DAQ_MaxSamplingRate,DAQ_SampleClk,Edge.RISING,AcquisitionType.FINITE, NsampsPerDAQread)
		#Configure convert clock
		readTask.timing.ai_conv_src = DAQ_SampleClk
		readTask.timing.ai_conv_active_edge = Edge.RISING



		#Configure start trigger
		readStartTrig = readTask.triggers.start_trigger
		readStartTrig.cfg_dig_edge_start_trig(DAQ_StartTrig,Edge.RISING)

		


	except Exception as excpt:
		print('Error configuring DAQ. Please check your DAQ is connected and powered. Exception details:', type(excpt).__name__,'.',excpt)
		closeDAQTask(readTask)
		sys.exit()
	return readTask

def configureDAQ_SPC(Nsamples):

	try:
		Nsamples = Nsamples + 1
		#Create and configure an analog input voltage task
		NsampsPerDAQread=2*Nsamples
		readTask = nidaqmx.Task()
		#channel = readTask.ai_channels.add_ai_voltage_chan(DAQ_APDInput,"",TerminalConfiguration.RSE,minVoltage,maxVoltage,VoltageUnits.VOLTS)
		
		ci_channel = readTask.ci_channels.add_ci_count_edges_chan("Dev1/ctr0", edge=Edge.RISING)  
		ci_channel.ci_count_edges_term = "/Dev1/PFI12" 				#"/Dev1/PFI12" yra DAQ_APDInput analogas

		#Configure sample clock
		readTask.timing.cfg_samp_clk_timing(DAQ_MaxSamplingRate,DAQ_SampleClk,Edge.RISING,AcquisitionType.FINITE, NsampsPerDAQread)

		# Add a digital filter to the Sample Clock channel
		readTask.timing.samp_clk_dig_fltr_enable = True
		readTask.timing.samp_clk_dig_fltr_min_pulse_width = 100e-9  # 100 ns		


		#Configure start trigger
		readArmStartTrig = readTask.triggers.arm_start_trigger
		readArmStartTrig.trig_type = TriggerType.DIGITAL_EDGE
		readArmStartTrig.dig_edge_edge = Edge.RISING
		readArmStartTrig.dig_edge_src = DAQ_StartTrig
	except Exception as excpt:
		print('Error configuring DAQ. Please check your DAQ is connected and powered. Exception details:', type(excpt).__name__,'.',excpt)
		closeDAQTask(readTask)
		sys.exit()
	return readTask

def readDAQ(task,N,timeout):
	try:
		counts = task.read(N,timeout)
	except Exception as excpt:
		print('Error: could not read DAQ. Please check your DAQ\'s connections. Exception details:', type(excpt).__name__,'.',excpt)
		sys.exit()
	return counts
	
def closeDAQTask(task):
	task.close()