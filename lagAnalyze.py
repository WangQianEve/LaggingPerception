#!/usr/bin/python
import json
import os
import matplotlib  
import matplotlib.pyplot as plt  

filepath = "./data/"
output = 'pilot.csv'
DEBUG = False
DRAW = False

# constants
DOWNWARDS = 0
UPWARDS = 1
LEFTWARDS = 0
RIGHTWARDS = 1

SCROLL = 0
OPEN = 1
SWIPE = 2

JUMP = 1
DELAY = 0
DEBUG = True

TOUCH = 1
FLING = 2

# configs
list_item_heights = [427, 812, 430, 812, 354, 551, 342, 672, 266, 423, 417, 748, 466, 911, 252, 902, 349, 515]
list_item_ac_heights = [0, 427, 1239, 1669, 2481, 2835, 3386, 3728, 4400, 4666, 5089, 5506, 6254, 6720, 7631, 7883, 8785, 9134]
list_item_count = len(list_item_ac_heights)
list_item_total_heights = 9649

def deduplicate(org_display_times, org_display_values, org_display_firsts):
	display_times = [org_display_times[0]]
	display_values = [org_display_values[0]]
	display_firsts = [org_display_firsts[0]]
	for i in range(1,len(org_display_times)):
		if org_display_times[i] == org_display_times[i-1]:
			display_values[-1] = org_display_values[i]
			display_firsts[-1] = org_display_firsts[i]
		else:
			display_times.append(org_display_times[i])
			display_values.append(org_display_values[i])
			display_firsts.append(org_display_firsts[i])
	return (display_times, display_values, display_firsts)

# for scroll
# 7 not 8
def analyzeScroll(scroll_result) :
	global out, participant_age, participant_gender
	global image_count

	lag_positions = scroll_result['actual lag positions'] if scroll_result.has_key('actual lag positions') else []
	lag_times = scroll_result['actual lag times'] if scroll_result.has_key('actual lag times') else []
	scroll_states = scroll_result['scroll state']
	scroll_state_times = scroll_result['scroll state time']
	task_direction = scroll_result['task direction']
	display_times, display_values, display_firsts = deduplicate(scroll_result['display time'], scroll_result['display value'], scroll_result['display first item'])

	# write basic
	out.write(str(scroll_result['task id'])+',')
	out.write(str(participant_age)+',')
	out.write(str(participant_gender)+',')
	out.write('scroll,')
	out.write(str(task_direction)+',')
	out.write(str(scroll_result['feedback'])+',')
	out.write('\"'+str(lag_positions)+'\"'+',')
	out.write('\"'+str(lag_times)+'\"'+',')

	# no lag
	if len(lag_positions) == 0: 
		out.write('0,0,0,0,0,0,0,null,null')
		return

	total_time = sum(lag_times)
	longgest = max(lag_times)
	longgest_pos = lag_positions[lag_times.index(longgest)]
	out.write(str(total_time)+',')
	out.write(str(len(lag_times))+',')
	out.write(str(longgest_pos)+',')
	out.write(str(longgest)+',')

	target_start = lag_positions[0]
	target_end = lag_positions[-1] + lag_times[-1]

	# find state times
	start_time = [scroll_state_times[i] for i in range(len(scroll_states)) if (scroll_states[i] == TOUCH) and (scroll_state_times[i] <= target_start)][-1]
	end_time = [scroll_state_times[i] for i in range(len(scroll_states)) if (scroll_states[i] != FLING) and (scroll_state_times[i] >= target_end)][-1]

	# find display indexes
	display_start_index = len([i for i in display_times if i < start_time]) # start from time >= first lag
	display_end_index = len([i for i in display_times if i <= end_time]) # end at time <= last lag (default: open closure)

	action_time = display_times[display_start_index:display_end_index]
	action_value = [( (display_firsts[i] / list_item_count) * list_item_total_heights + list_item_ac_heights[(display_firsts[i] % list_item_count)] - display_values[i]) for i in range(display_start_index, display_end_index)]

	# get speed
	smooth_action_speed = [0]
	smooth_speed_w = 10
	l_action = len(action_time)
	for i in range(1, l_action):
		left = max(i-smooth_speed_w, 0)
		right = min(l_action-1, i+smooth_speed_w)
		smooth_action_speed.append( (1 if task_direction==DOWNWARDS else -1)* ( (action_value[right] - action_value[left])/(action_time[right] - action_time[left] + 0.0) ))

	action_max_speed = max(smooth_action_speed)
	# find lag speed
	# lag_speed = []
	# for lag_pos in lag_positions:
	# 	pos = len([i for i in action_time if i <= lag_pos]) - 1
	# 	lag_speed.append(action_speed[pos])

	lag_display_indexes = []
	lag_state_indexes = []
	longest_lag_display_index = 0
	longest_lag_state_index = 0
	for lag_pos in lag_positions:
		lag_display_indexes.append(len([i for i in display_times if i <= lag_pos]) - 1)
		lag_state_indexes.append(len([i for i in scroll_state_times if i <= lag_pos]) - 1)
		if longgest_pos == lag_pos:
			longest_lag_display_index = lag_display_indexes[-1]
			longest_lag_state_index = lag_state_indexes[-1]

	out.write(str(action_max_speed)+',')
	out.write(str(smooth_action_speed[lag_display_indexes[0] - display_start_index])+',')
	out.write(str(smooth_action_speed[longest_lag_display_index - display_start_index])+',')
	state = scroll_states[lag_state_indexes[0]]
	out.write(('touch' if state==TOUCH else ('fling' if state==FLING else 'idle'))+',')
	state = scroll_states[longest_lag_state_index]
	out.write(('touch' if state==TOUCH else ('fling' if state==FLING else 'idle'))+',')

	# draw pic
	if DRAW: 
		temp = action_time[0]
		action_time = [(i - temp) for i in action_time]
		plt.subplot(2,1,image_count)
		plt.scatter(action_time,action_value, s=1, c='g')  
		plt.subplot(2,1,image_count+1)	
		plt.scatter(action_time,smooth_action_speed, s=1, c='r')  
		# action_lag_start = [i - temp for i in lag_positions]
		# action_lag_end = [(lag_positions[i] + lag_times[i] - temp) for i in range(len(lag_positions))]
		# plt.scatter(action_lag_start,0,c = 'r')
		# plt.scatter(action_lag_end,0,c = 'g')

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
	global out, participant_age, participant_gender
	global image_count
	image_count = 1
	f_count = 0
	out = open(output,'w')
	out.write('id,age,gender,type,direction,ov_feedback,have lag,feedback,positions,times,total time,num of lags,longest position,longest time,fastest speed,lag first speed,lag longest speed,lag first state,lag longest state,\n')
	for files in os.walk(filepath):
		for filename in files[2]:
			if not filename.endswith('.json'): continue
			print filename
			file = open(files[0] + filename , 'r')
			file_json = json.loads(file.read())
			participant_age = file_json['participant-age']
			participant_gender = file_json['participant-gender']
			results = file_json['results']
			scroll_flag = True
			person_count = 0
			for result in results:
				task_type = result['task type']
				if task_type == 0: # scroll
					if scroll_flag:
						scroll_flag = False
						continue
					if DRAW:
						f1 = plt.figure(f_count)  
					analyzeScroll(result)
					out.write('\n')
					person_count += 1
					if DRAW:
						f_count += 1
						if f_count % 4 == 0:
							break
						f1 = plt.figure(f_count) 
					# break
				elif task_type == 1:# open
					continue
				else:
					continue
			# break
			print person_count
		break
	out.close()
	if DRAW: plt.show()

if __name__ == '__main__':
	main()

