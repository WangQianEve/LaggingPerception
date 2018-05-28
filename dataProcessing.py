#!/usr/bin/python
import json
import os
import matplotlib  
import matplotlib.pyplot as plt  
import numpy

filepath = "./data/"
debugFilepath = './data/debug/'
output = 'all.csv'
null = ''

colNames = ['filename','device name','android version','age','gender','gesture','screen size',
			'type','direction','task speed','lag type','lag distribution',
			'redos','total time','num of lags','longest time','small lag time',
			'speed','speed mm','state',
			'experience','have lag','rate',
			'positions','times','conf positions','conf times',
			]

line = [None for i in colNames]

DEBUG = False
DRAW = False

# constants
DOWNWARDS = 'Down/Right'
UPWARDS = 'Up/Left'

SCROLL = 'Scroll'
OPEN = 'Open App'
SWIPE = 'Desktop'
TYPES = [OPEN,SCROLL,SWIPE]

IDLE = 0
TOUCH = 1
FLING = 2

def deduplicate(org_display_times, org_display_values):
	display_times = [org_display_times[0]]
	display_values = [org_display_values[0]]
	for i in range(1,len(org_display_times)):
		if org_display_times[i] == org_display_times[i-1]:
			display_values[-1] = org_display_values[i]
		else:
			display_times.append(org_display_times[i])
			display_values.append(org_display_values[i])
	return (display_times, display_values)

def trimDisplay(display_times, display_values, state_time, end_time):
	# find display indexes
	action_time = [time for time in display_times if time >= state_time and time <= end_time ]
	display_start_index = display_times.index(action_time[0])
	display_end_index = display_times.index(action_time[-1])
	action_value = display_values[display_start_index:display_end_index+1]
	return action_time, action_value

def smooth(y, box_pts):
    box = numpy.ones(box_pts)/box_pts
    y_smooth = numpy.convolve(y, box, mode='same')
    return y_smooth

def analyzeSpeed(action_time, action_value, longest_pos, state_time, state_value):
	global task_direction, task_type, file_name, task_id
	action_value_acc = []
	if task_type == SWIPE and task_direction == 1:
		action_value_acc = [-i for i in action_value]
	# elif task_type == SCROLL:
	# 	t = 0
	# 	for i in range(len(action_value)):
	# 		t += action_value[i]
	# 		action_value_acc.append(t)
	else:
		action_value_acc = action_value

	# get speed
	width = 2
	l = len(action_time)
	action_speed = [(action_value_acc[i] - action_value_acc[i-1]) / (action_time[i] - action_time[i-1] + 0.0) for i in range(1, l)]
	action_speed.insert(0,action_speed[0])
	action_speed = [ 0 if speed < 0 else speed for speed in action_speed]

	average = numpy.mean(action_speed)
	std = numpy.std(action_speed)
	smooth_action_speed = list(action_speed)
	for i in range(l): 
		speed = action_speed[i]
		if abs(speed - average) > 2*std:
			smooth_action_speed[i] = smooth_action_speed[i-1] if i>0 else 0
	smooth_action_speed = [numpy.mean(smooth_action_speed[max(0,i - width):min(l, i+width+1)]) for i in range(l)]

	if longest_pos == 0:
		return null, null, null

	longest_speed = smooth_action_speed[len([i for i in action_time if i <= longest_pos]) - 1]
	state = state_value[len([i for i in state_time if i <= longest_pos]) - 1]
	longest_state = ('touch' if state==TOUCH else ('fling' if state==FLING else 'idle'))
	longest_value = action_value[len([i for i in action_time if i <= longest_pos]) - 1]

	# draw pic
	if DRAW: 
		f1 = plt.figure(file_name[-12:-5] + ' : ' + str(task_id))
		plt.subplot(2,1,1)
		plt.scatter(action_time,action_value_acc, s=1, c='g')
		plt.subplot(2,1,2)
		plt.scatter(action_time,smooth_action_speed, s=1, c='g')

	return longest_speed, longest_state, longest_value

def analyzeOpen(scroll_result):
	lag_positions = scroll_result['actual lag positions']
	if DEBUG: print lag_positions
	lag_times = scroll_result['actual lag times']
	display_times = scroll_result['display time']
	display_values = scroll_result['display value']

	if len(lag_positions) == 0:
		# no lag
		print "no lag"
		return
	f2 = plt.figure(2)  
	plt.subplot(211)  
	plt.scatter(display_times,display_values)  
	plt.scatter(lag_positions, [0 for i in range(len(lag_positions))], c = 'r')
	lag_positions_end = [(lag_positions[i] + lag_times[i]) for i in range(len(lag_positions))]
	plt.scatter(lag_positions_end, [0 for i in range(len(lag_positions))], c = 'g')
	plt.show()

def analyzeSwipe(scroll_result):
	lag_positions = scroll_result['actual lag positions']
	if DEBUG: print lag_positions
	lag_times = scroll_result['actual lag times']
	display_times = scroll_result['display time']
	display_values = scroll_result['display value']

	if len(lag_positions) == 0:
		# no lag
		print "no lag"
		return
	f2 = plt.figure(2)  
	plt.subplot(211)  
	plt.scatter(display_times,display_values)  
	plt.scatter(lag_positions, [0 for i in range(len(lag_positions))], c = 'r')
	lag_positions_end = [(lag_positions[i] + lag_times[i]) for i in range(len(lag_positions))]
	plt.scatter(lag_positions_end, [0 for i in range(len(lag_positions))], c = 'g')
	plt.show()

def getDistributionInfo(times, conf_times):
	if len(times) == 0:
		return 'none',0
	elif len(times) == 1:
		if len(conf_times) == 1:
			return 'B',0
		else:
			return 'BB',0
	elif sum(times)/len(times) == times[0]:
		return 'BBB',times[0]
	else:
		return 'Bss',min(times[0],times[1])

def average(l):
	if len(l) == 0:
		return 0
	return sum(l)/(len(l)+0.0)

def printAveRate(AveRatePath):
	out = open(AveRatePath,'w')
	out.write('filename,type,experience,havelag,rate,count\n')
	for files in os.walk(filepath):
		for filename in files[2]:
			if not filename.endswith('.json'): continue
			line = [None for i in range(6)]
			lines = [None for i in range(3)]
			line[0] = filename
			# read file
			file = open(files[0] + filename , 'r')
			file_json = json.loads(file.read())
			results = file_json['results']
			exps = {OPEN:[],SCROLL:[],SWIPE:[]}
			havelags = {OPEN:[],SCROLL:[],SWIPE:[]}
			rates = {OPEN:[],SCROLL:[],SWIPE:[]}
			for result in results:
				task_id = result['task id']
				task_type = result['task type']

				state_values = result['scroll state']
				state_times = result['scroll state time']
				if len(state_values) < 2 and task_type != OPEN:
					continue
				if len(result['display time']) < 2:
					print "display too short:"+filename+','+str(task_id)
					continue

				experience,havelagStr,rate = result['feedback'].split(',')
				havelag = 0 if havelagStr=='true' else 1
				exps[task_type].append(float(experience))
				havelags[task_type].append(havelag)
				rates[task_type].append(float(rate))
			line[1] = OPEN
			line[2] = average(exps[OPEN])
			line[3] = average(havelags[OPEN])
			line[4] = average(rates[OPEN])
			line[5] = len(exps[OPEN])
			lines[0] = line
			line = [str(i) for i in line]
			out.write(','.join(line) + '\n')
			line[1] = SWIPE
			line[2] = average(exps[SWIPE])
			line[3] = average(havelags[SWIPE])
			line[4] = average(rates[SWIPE])
			line[5] = len(exps[SWIPE])
			lines[1] = line
			line = [str(i) for i in line]
			out.write(','.join(line) + '\n')
			line[1] = SCROLL
			line[2] = average(exps[SCROLL])
			line[3] = average(havelags[SCROLL])
			line[4] = average(rates[SCROLL])
			line[5] = len(exps[SCROLL])
			lines[2] = line
			line = [str(i) for i in line]
			out.write(','.join(line) + '\n')
			line[1] = 'all'
			line[2] = average([tl[2] for tl in lines])
			line[3] = average([tl[3] for tl in lines])
			line[4] = average([tl[4] for tl in lines])
			line[5] = sum(tl[5] for tl in lines)
			line = [str(i) for i in line]
			out.write(','.join(line) + '\n')
		break
	out.close()	

def main():
	global line, file_name, task_id
	global task_direction, task_type
	out = open(output,'w')
	out.write(','.join(colNames) + '\n')

	for files in os.walk(filepath):
		for filename in files[2]:
			if not filename.endswith('.json'): continue
			file_name = filename
			line[colNames.index('filename')] = filename

			# read file
			file = open(files[0] + filename , 'r')
			file_json = json.loads(file.read())

			# demographics
			line[colNames.index('age')] = file_json['participant-age']
			line[colNames.index('gender')] = file_json['participant-gender']
			# line[colNames.index('contact')] = file_json['participant-contact'].encode('utf-8')
			screen_size = file_json['screen-size-inches']
			line[colNames.index('screen size')] = file_json['screen-size-inches']
			line[colNames.index('android version')] = file_json['device-release']
			line[colNames.index('device name')] = file_json['device-name']
			gesture = file_json['participant-gesture']
			line[colNames.index('gesture')] = 0 if gesture == "thumb" else 1
			
			lines = {OPEN:[],SCROLL:[],SWIPE:[]}
			rates = {OPEN:[],SCROLL:[],SWIPE:[]}
			exps = {OPEN:[],SCROLL:[],SWIPE:[]}
			speed_ratio = 1
			results = file_json['results']
			for result in results:
				# task type
				task_type = result['task type']
				line[colNames.index('type')] = task_type

				# remove invalid
				state_values = result['scroll state']
				state_times = result['scroll state time']
				if len(state_values) < 2 and task_type != OPEN:
					# print 'discard 1'
					continue
				if len(result['display time']) < 2:
					# print 'discard 2'
					continue
				
				# display
				display_times, display_values = deduplicate(result['display time'], result['display value'])
				task_id = result['task id']
				if (task_type == SCROLL):
					speed_ratio = (result['display value mm'][1] - result['display value mm'][0]) / (result['display value'][1] - result['display value'][0])
				elif task_type == SWIPE:
					speed_ratio = screen_size*141.11

				# direction
				task_direction = result['task direction'] if task_type != OPEN else null
				if task_direction == 'Up/Left':
					task_direction = 0
				if task_direction == 'Down/Right':
					task_direction = 1
				line[colNames.index('direction')] = task_direction
				
				# required speed and feedback
				line[colNames.index('task speed')] = result['task speed'] if task_type == SCROLL else null
				experience,havelagStr,rate = result['feedback'].split(',')
				line[colNames.index('experience')] = experience
				havelag = 0 if havelagStr=='true' else 1
				line[colNames.index('have lag')] = havelag
				line[colNames.index('rate')] = rate
				
				lag_positions = result['actual lag positions']
				lag_times = result['actual lag times']

				# lag type
				line[colNames.index('lag type')] = 0 if result['lag type']=='Delay' else 1
				if len(lag_positions)==0:
					line[colNames.index('lag type')] = null
				
				# just a log
				line[colNames.index('positions')] = '\"%s\"' % str(lag_positions)
				line[colNames.index('times')] = '\"%s\"' % str(lag_times)
				conf_lag_positions = result['config lag pos'] if result.has_key('config lag pos') else []
				conf_lag_times = result['config lags'] if result.has_key('config lags') else []
				line[colNames.index('conf positions')] = '\"%s\"' % str(conf_lag_positions)
				line[colNames.index('conf times')] = '\"%s\"' % str(conf_lag_times)
				
				# lag distribution & small lag time
				(line[colNames.index('lag distribution')],line[colNames.index('small lag time')]) = getDistributionInfo(lag_times, conf_lag_times);

				# just a log
				line[colNames.index('redos')] = result['num_of_redos']

				# time related
				line[colNames.index('total time')] = sum(lag_times)
				num_of_lags = len(lag_times)
				line[colNames.index('num of lags')] = num_of_lags
				longest_time = max(lag_times) if num_of_lags > 0 else 0
				line[colNames.index('longest time')] = longest_time

				# longest attrs
				longest_pos = lag_positions[lag_times.index(longest_time)] if num_of_lags > 0 else 0
				longestSpeed, longestState, longestValue = analyzeSpeed(display_times, display_values, longest_pos, state_times, state_values) if task_type != 'Open App' else (null,null,null) # len([i for i in display_times if i <= longest_pos])/19.0)
				line[colNames.index('speed')] = longestSpeed/3 if longestSpeed!= null else null
				line[colNames.index('speed mm')] = longestSpeed*speed_ratio/14.8 if longestSpeed!= null else null
				if longestState == 'idle':
					longestState = 0
				elif longestState == 'touch':
					longestState = 1
				elif longestState == 'fling':
					longestState = 2
				line[colNames.index('state')] = longestState

				# DATA cleansing
				rates[task_type].append(float(rate))
				exps[task_type].append(float(experience))
				lines[task_type].append(line[:])

			for tt in TYPES:
				tave = average(rates[tt])
				tmin = min(rates[tt])
				eave = average(exps[tt])
				emin = min(exps[tt])
				if tave != tmin:
					if eave!=emin:
						for tline in lines[tt]:
							tline = [str(i) for i in tline]
							out.write(','.join(tline) + '\n')
					else:
						print "exp",eave
				else:
					print tave
			# break # one user
		break
	out.close()
	if DRAW: plt.show()

if __name__ == '__main__':
	main()
	# printAveRate('aveRate.csv')

