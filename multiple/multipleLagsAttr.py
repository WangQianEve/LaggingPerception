#!/usr/bin/python
import json
import os
import numpy

filepath = "../data/"
# debugFilepath = './data/debug/'

output = 'multipleLagsAttr.csv'

MAX_LAG = 6
SCROLL = 'Scroll'
OPEN = 'Open App'
SWIPE = 'Desktop'

DELAY = 0
JUMP = 2
LTYPE_ = 1

nolag = [0, LTYPE_, -1, -1, -1, -1]

features = ['time','ltype','state','speed','gap','instype']
targets = ['exp','hlag','rate']
colNames = ['filename','type', 'num_of_lags'] + targets
for i in range(MAX_LAG):
	colNames += [feature+str(i) for feature in features]

line = [None for i in colNames]


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

def getSpeedsAndStates(display_times, display_values, state_times, state_values, lag_positions, lag_times, task_type, ratio):
	org_speeds = []
	smooth_speeds = []
	if task_type == SCROLL or task_type == SWIPE:
		for i in range(1, len(display_values)):
			s = (display_values[i] - display_values[i-1]) / (display_times[i] - display_times[i-1] + 0.0)
			if s < 0: s = 0
			org_speeds.append(s)
		org_speeds.insert(0, 0)

		# correct anomaly
		average = numpy.mean(org_speeds)
		std = numpy.std(org_speeds)
		for i in range(len(org_speeds)): 
			s = org_speeds[i]
			if abs(s - average) > 2*std :
				org_speeds[i] = org_speeds[i-1] if i > 0 else 0
		# smooth
		width = 2
		smooth_speeds = [numpy.mean(org_speeds[max(0,i - width):min(len(org_speeds), i+width+1)]) for i in range(len(org_speeds))]

	speeds, states, gaps = [], [], [-2]
	for i in range(len(lag_positions)):
		pos = lag_positions[i]
		time = lag_times[i]
		if i > 0:
			gaps.append(pos - lag_positions[i-1] - lag_times[i - 1])
		# states
		if task_type == OPEN:
			states.append(-2)
		else:
			states.append(state_values[len([1 for t in state_times if t <= pos]) - 1])
		# speeds
		if task_type == OPEN:
			di = len([1 for t in display_times if t <= pos]) - 1
			if di > 0:
				speeds.append((display_values[di] - display_values[di - 1]) / (display_times[di] - display_times[di - 1] + 0.0) * ratio)
			else:
				speeds.append(0)
		else:
			speeds.append(smooth_speeds[max(0,len( [1 for t in display_times if t <= pos] ) - 1)] * ratio)
	return speeds, states, gaps

def average(l):
	if len(l) == 0:
		return 0
	return sum(l)/(len(l)+0.0)

def loadSize():
	from pandas import read_csv
	ssize_data = read_csv('ssize.csv')
	ssize_table = {}
	for i in range(ssize_data.shape[0]):
		item = ssize_data.loc[i]
		ssize_table[item['file_name']] = item['ssize']
	return ssize_table

def readJson(filename):
	file = open(filename , 'r')
	file_json = json.loads(file.read())
	file.close()
	return file_json

def getRates(feedback):
	experience,havelagStr,rate = feedback.split(',')
	return int(float(experience)), 0 if havelagStr=='true' else 1, int(float(rate))

def trimLags(p, t):
	positions = p
	times = t
	n = len(times) - MAX_LAG
	if n <= 0 :
		return positions, times
	fp, ft = positions[0], times[0]
	rt = False
	for i in range(n):
		target = times.index(min(times))
		del positions[target]
		del times[target]
		if target == 0:
			rt = True
	# insert first
	if rt:
		target = times.index(min(times))
		del positions[target]
		del times[target]
	positions.insert(0,fp)
	times.insert(0,ft)
	return positions, times

def instypeOf(positions):
	if len(positions) == 0:
		return -1
	return 0 if positions[0] == 0 else 1

def checkRate(results):
	rates = {OPEN:[],SCROLL:[],SWIPE:[]}
	exps = {OPEN:[],SCROLL:[],SWIPE:[]}
	for result in results:
		task_type = result['task type']
		experience,havelag,rate = getRates(result['feedback'])
		rates[task_type].append(rate)
		exps[task_type].append(experience)
	badUsers = {}
	for task_type in rates.keys():
		badUsers[task_type] = average(exps[task_type]) == min(exps[task_type]) or average(rates[task_type]) == min(rates[task_type])
	return badUsers

def genSizeTable():
	ssize_table = loadSize()
	f = open('size_table','w')
	f.write(json.dumps(ssize_table))
	f.close()

def main():
	global line
	ssize_table = readJson('size_table')

	out = open(output,'w')
	out.write(','.join(colNames) + '\n')

	for files in os.walk(filepath):
		for filename in files[2]:
			if not filename.endswith('.json'): continue
			if not ssize_table.has_key(filename): continue

			print filename

			actual_ssize = ssize_table[filename]

			# file_name = filename
			line[colNames.index('filename')] = filename

			file_json = readJson(files[0] + filename)
			results = file_json['results']
			screen_size = file_json['screen-size-inches']
			
			speed_ratios = { SCROLL: 0, 
							 OPEN: actual_ssize*25.4*0.6/14.8,
							 SWIPE: actual_ssize*25.4*0.6/14.8} # 1 inch == 25.4 mm
			
			badUsers = checkRate(results)

			for result in results:
				task_type = result['task type']
				line[colNames.index('type')] = task_type

				if badUsers[task_type]: continue
				state_values = result['scroll state']
				state_times = result['scroll state time']
				if len(state_values) < 2 and task_type != OPEN:
					continue
				if len(result['display time']) < 3:
					continue
				
				if task_type == SCROLL and speed_ratios[task_type] == 0:
					speed_ratios[task_type] = (result['display value mm'][1] - result['display value mm'][0]) / (result['display value'][1] - result['display value'][0]) / screen_size * actual_ssize / 14.8
				
				task_direction = result['task direction'] if task_type != OPEN else -1

				# display
				display_times, display_values = deduplicate(result['display time'], result['display value'])

				# rates
				experience,havelag,rate = getRates(result['feedback'])
				line[colNames.index('exp')] = experience
				line[colNames.index('hlag')] = havelag
				line[colNames.index('rate')] = rate
				
				lag_positions, lag_times = trimLags(p = result['actual lag positions'], t = result['actual lag times'])
				num_of_lags = len(lag_times)
				line[colNames.index('num_of_lags')] = num_of_lags

				ltype = DELAY if result['lag type']=='Delay' else JUMP
				ltypes = [ltype for i in range(num_of_lags)]
				
				instype = instypeOf(result['config lag pos']) if result.has_key('config lag pos') else -5
				instypes = [instype for i in range(num_of_lags)]

				if (task_direction == 1 and task_type == SWIPE):
					display_values = [-v for v in display_values]
				speeds, states, gaps = getSpeedsAndStates(  display_times, display_values, 
															state_times, state_values,
															lag_positions, lag_times,
															task_type, speed_ratios[task_type])

				for i in range(MAX_LAG):
					if i >= num_of_lags:
						for j in range(len(features)):
							line[colNames.index(features[j]+str(i))] = nolag[j]
					else:
						line[colNames.index('time'+str(i))] = lag_times[i]
						line[colNames.index('ltype'+str(i))] = ltypes[i]
						line[colNames.index('state'+str(i))] = states[i]
						line[colNames.index('speed'+str(i))] = speeds[i]
						line[colNames.index('gap'+str(i))] = gaps[i]
						line[colNames.index('instype'+str(i))] = instypes[i]

				line = [str(v) for v in line]
				out.write(','.join(line) + '\n')

			# break # one user
		break
	out.close()

if __name__ == '__main__':
	main()
	# genSizeTable()

