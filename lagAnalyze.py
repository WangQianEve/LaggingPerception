#!/usr/bin/python
import json
import os
import matplotlib  
import matplotlib.pyplot as plt  

filepath = "./data/"
DEBUG = True
list_item_heights = [427, 812, 430, 812, 354, 551, 342, 672, 266, 423, 417, 748, 466, 911, 252, 902, 349, 515]
list_item_ac_heights = [0, 427, 1239, 1669, 2481, 2835, 3386, 3728, 4400, 4666, 5089, 5506, 6254, 6720, 7631, 7883, 8785, 9134]
list_item_count = len(list_item_ac_heights)
list_item_total_heights = 9649

def analyzeScroll(scroll_result) :
	lag_positions = scroll_result['actual lag positions']
	lag_times = scroll_result['actual lag times']
	scroll_state_times = scroll_result['scroll state time']
	display_times = scroll_result['display time']
	display_values = scroll_result['display value']
	display_firsts = scroll_result['display first item']

	if len(lag_positions) == 0:
		# no lag
		print "no lag"
		return

	target_start = lag_positions[0]
	target_end = lag_positions[-1] + lag_times[-1]

	# find state indexes
	start_time = 0
	end_time = display_times[-1]
	state_index = -1
	for state in scroll_result['scroll state']:
		state_index += 1
		time = scroll_state_times[state_index]
		if (time <= target_start):
			if (state == 1):
				start_time = time
		elif (time >= target_end):
			if (state != 2):
				end_time = time
				break
	if DEBUG : print str(start_time) + ',' + str(end_time)

	# find display indexes
	display_start = len([i for i in display_times if i < start_time])
	display_end = len([i for i in display_times if i <= end_time])
	action_time = display_times[display_start:display_end]
	if (len(action_time) == 0):
		# exception
		return
	temp = action_time[0]
	action_time = [(i - temp) for i in action_time]
	print len(display_firsts)
	print len(display_values)
	print str(display_start) + ',' + str(display_end)
	action_value = [( (display_firsts[i] / list_item_count) * list_item_total_heights + list_item_ac_heights[(display_firsts[i] % list_item_count)] - display_values[i]) for i in range(display_start, display_end)]
	if DEBUG : print action_value
	f1 = plt.figure(1)  
	plt.subplot(211)  
	plt.scatter(action_time,action_value)  
	action_lag_start = [i - temp for i in lag_positions]
	action_lag_end = [(lag_positions[i] + lag_times[i] - temp) for i in range(len(lag_positions))]
	plt.scatter(action_lag_start,0,c = 'r')
	plt.scatter(action_lag_end,0,c = 'g')
	plt.show()

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
	for files in os.walk(filepath):
		for filename in files[2]:
			if not filename.endswith('.json'): continue
			file = open(files[0] + filename , 'r')
			file_json = json.loads(file.read())
			results = file_json['results']
			# scroll
			for scroll_result in results:
				task_type = scroll_result['task type']
				if task_type == 0: # scroll
					analyzeScroll(scroll_result)
					break
				elif task_type == 1:# open
					continue
				else:
					continue
			break

if __name__ == '__main__':
	main()

