#!/usr/bin/python
import json
import os
import matplotlib  
import matplotlib.pyplot as plt  
import numpy

filepath = "./data/pilot2-test/"
output = 'pilot-test.csv'

colNames = ['filename','device name','android version','age','gender','gesture','contact','screen size',
			'type','direction','speed','task id','lag type',
			'redos','total time','num of lags','longest time',
			'fastest speed','longest speed','longest state',
			'experience','have lag','rate',
			'positions','times','conf positions','conf times',
			]
line = [None for i in colNames]

DEBUG = False
DRAW = True

# constants
DOWNWARDS = 'Down/Right'
UPWARDS = 'Up/Left'

SCROLL = 'Scroll'
OPEN = 'Open App'
SWIPE = 'Desktop'

IDLE = 0
TOUCH = 1
FLING = 2

# configs
# list_item_heights = [427, 812, 430, 812, 354, 551, 342, 672, 266, 423, 417, 748, 466, 911, 252, 902, 349, 515]
# list_item_ac_heights = [0, 427, 1239, 1669, 2481, 2835, 3386, 3728, 4400, 4666, 5089, 5506, 6254, 6720, 7631, 7883, 8785, 9134]
# list_item_count = len(list_item_ac_heights)
# list_item_total_heights = 9649

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

def trim(display_times, display_values, state_times, state_values, target_start, target_end):
	# find state times
	states_before = [state_times[i] for i in range(len(state_values)) if (state_values[i] == TOUCH) and (state_times[i] <= target_start)]
	states_after = [state_times[i] for i in range(len(state_values)) if (state_values[i] != FLING) and (state_times[i] >= target_end)]
	start_time = states_before[-1]
	end_time = states_after[0]
	state_start_index = len(states_before) - 1
	state_end_index = len(state_values) - len(states_after) + 1
	action_state_times = state_times[state_start_index:state_end_index]
	action_state_values = state_values[state_start_index:state_end_index]

	# find display indexes
	display_start_index = len([i for i in display_times if i < start_time]) # start from time >= first lag
	display_end_index = len([i for i in display_times if i <= end_time]) # end at time <= last lag (default: open closure)

	action_time = display_times[display_start_index:display_end_index]
	action_value = display_values[display_start_index:display_end_index]

	return action_time, action_value, action_state_times, action_state_values

def analyzeSpeed(action_time, action_value, longest_pos, state_time, state_value):
	global task_direction, task_type, file_name, task_id
	action_value_acc = []
	if task_type == SWIPE and task_direction == DOWNWARDS:
		action_value_acc = [-i for i in action_value]
	# elif task_type == SCROLL:
	# 	t = 0
	# 	for i in range(len(action_value)):
	# 		t += action_value[i]
	# 		action_value_acc.append(t)
	else:
		action_value_acc = action_value

	# get speed
	alpha = 0.8
	action_speed = [(action_value_acc[i] - action_value_acc[i-1]) / (action_time[i] - action_time[i-1] + 0.0) for i in range(1, len(action_time))]
	action_speed.insert(0,action_speed[0])
	average = numpy.mean(action_speed)
	std = numpy.std(action_speed)
	smooth_action_speed = [action_speed[0] if abs(action_speed[0] - average) <= 2*std else average]
	for i in range(1, len(action_speed)): 
		speed = action_speed[i]
		if abs(speed - average) > 2*std:
			smooth_action_speed.append(smooth_action_speed[-1])
		else:
			smooth_action_speed.append(alpha * smooth_action_speed[-1] + (1-alpha) * speed)

	max_speed = max(smooth_action_speed)

	if longest_pos == 0:
		return max_speed, 'No Lag', 'No Lag', 'No Lag'

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
		plt.scatter(action_time,smooth_action_speed, s=1, c='r')
		# plt.scatter(action_time,action_speed, s=1, c='b')
		# plt.subplot(2,1,3)
		# action_lag_start = [i - temp for i in lag_positions]
		# action_lag_end = [(lag_positions[i] + lag_times[i] - temp) for i in range(len(lag_positions))]
		# plt.scatter(action_lag_start,0,c = 'r')
		# plt.scatter(action_lag_end,0,c = 'g')

	return max_speed, longest_speed, longest_state, longest_value

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

def main():
	global line, file_name, task_id
	global task_direction, task_type
	out = open(output,'w')
	out.write(','.join(colNames) + '\n')

	for files in os.walk(filepath):
		for filename in files[2]:
			if not filename.endswith('.json'): continue
			print filename
			file_name = filename
			line[colNames.index('filename')] = filename
			# read file
			file = open(files[0] + filename , 'r')
			file_json = json.loads(file.read())
			line[colNames.index('age')] = file_json['participant-age']
			line[colNames.index('gender')] = file_json['participant-gender']
			line[colNames.index('contact')] = file_json['participant-contact']
			line[colNames.index('screen size')] = file_json['screen-size-inches']
			line[colNames.index('android version')] = file_json['device-release']
			line[colNames.index('device name')] = file_json['device-name']
			line[colNames.index('gesture')] = file_json['participant-gesture']
			results = file_json['results']
			for result in results:
				task_type = result['task type']
				line[colNames.index('type')] = task_type
				line[colNames.index('task id')] = result['task id']
				task_id = result['task id']
				task_direction = result['task direction'] if task_type != OPEN else DOWNWARDS
				line[colNames.index('direction')] = task_direction
				line[colNames.index('speed')] = result['task speed']
				line[colNames.index('lag type')] = result['lag type']
				experience,havelag,rate = result['feedback'].split(',')
				line[colNames.index('experience')] = experience
				line[colNames.index('have lag')] = havelag
				line[colNames.index('rate')] = rate
				lag_positions = result['actual lag positions']
				lag_times = result['actual lag times']
				line[colNames.index('positions')] = '\"%s\"' % str(lag_positions)
				line[colNames.index('times')] = '\"%s\"' % str(lag_times)
				conf_lag_positions = result['config lag pos'] if result.has_key('config lag pos') else []
				conf_lag_times = result['config lags'] if result.has_key('config lags') else []
				line[colNames.index('conf positions')] = '\"%s\"' % str(conf_lag_positions)
				line[colNames.index('conf times')] = '\"%s\"' % str(conf_lag_times)
				line[colNames.index('redos')] = result['num_of_redos']
				line[colNames.index('total time')] = sum(lag_times)

				num_of_lags = len(lag_times)
				line[colNames.index('num of lags')] = num_of_lags
				longest_time = max(lag_times) if num_of_lags > 0 else 0
				line[colNames.index('longest time')] = longest_time
				longest_pos = lag_positions[lag_times.index(longest_time)] if num_of_lags > 0 else 0
				display_times, display_values = deduplicate(result['display time'], result['display value'])
				state_values = result['scroll state']
				state_times = result['scroll state time']

				if task_type == SWIPE:
					last_touch_index = [i for i in range(len(state_values)) if state_values[i] == TOUCH][-1]
					target_start = state_times[last_touch_index]
					first_idle_after_touch = [i for i in range(last_touch_index,len(state_values)) if state_values[i] == IDLE][0]
					target_end = state_times[first_idle_after_touch]
					display_times, display_values, state_times, state_values = trim(display_times, display_values, state_times, state_values, target_start, target_end) 
				elif task_type == SCROLL and num_of_lags > 0:
					target_start = lag_positions[0]
					target_end = lag_positions[-1] + lag_times[-1]
					display_times, display_values, state_times, state_values = trim(display_times, display_values, state_times, state_values, target_start, target_end) 						

				print task_type + ',' + task_direction + ' : ' + str(display_times[-1] - display_times[0])
				fastestSpeed, longestSpeed, longestState, longestValue = analyzeSpeed(display_times, display_values, longest_pos, state_times, state_values) if task_type != 'Open App' else ('Open App','Open App','Open App',len([i for i in display_times if i <= longest_pos])/19.0)
				line[colNames.index('fastest speed')] = fastestSpeed
				line[colNames.index('longest speed')] = longestSpeed
				line[colNames.index('longest state')] = longestState
				line = [str(i) for i in line]
				out.write(','.join(line) + '\n')
				# if task_type == SCROLL:
				# 	break
			# break
		break
	out.close()
	if DRAW: plt.show()

if __name__ == '__main__':
	main()

