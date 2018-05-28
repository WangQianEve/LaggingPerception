from os.path import dirname, join

import mord

from sklearn import linear_model, metrics, preprocessing 
from sklearn.naive_bayes import GaussianNB
from sklearn.externals import joblib
from sklearn.datasets.base import Bunch

from collections import Counter
from matplotlib import pyplot as plt
import numpy as np

def load_csv(filepath):
    from pandas import read_csv
    module_path = dirname(__file__)
    data_file_name = join(module_path, filepath)
    return read_csv(data_file_name)

def genData(data, features, targets):
	feature_data = data.loc[:,features]
	# feature_data['ltype'].replace(np.nan, 0.5, inplace = True) # features['lag type'].fillna(0.5, inplace = True)
	target_data = {}
	for target_name in targets:
		le = preprocessing.LabelEncoder()
		target = data.loc[:,target_name]
		le.fit(target)
		target_data[target_name] = le.transform(target)

	return feature_data, target_data

def genModels(X, Y):
	import time
	file_models = {}
	for target in Y:
		models = {} 
		models['OLR_AT'] = mord.LogisticAT(alpha=1.);
		models['OLR_SE'] = mord.LogisticSE(alpha=1.);
		# models['LR'] = linear_model.LogisticRegression(solver='lbfgs', multi_class='multinomial');
		# models['OLR_IT'] = mord.LogisticIT(alpha=1.);
		# models['OR'] = mord.OrdinalRidge();
		# models['LAD'] = mord.LAD();
		# models['NB'] = GaussianNB();
			
		for model_name in models:
			model = models[model_name]
			print ' *** '.join((target, model_name, time.asctime( time.localtime(time.time()) )))
			model.fit(X,Y[target])
		
		print time.asctime( time.localtime(time.time()) )
		
		file_models[target] = models		
	return file_models

def scores(models, X, Y, draw, distr = True, title = ''):
	if draw:
		target_n = len(models)
		model_n = len(models.values()[0]) + 1
		plt.figure()
		plot_i = -1
	res = {}
	for target in models:
		# print target
		y = Y[target]
		cy = Counter(y)
		xs = range(len(cy))
		cy = cy.values()
		if draw:
			# draw org
			plot_i += 1
			plot_j = 1
			plt.subplot(target_n, model_n, plot_i * model_n + plot_j)
			plt.subplots_adjust(hspace = 0.5, wspace = 0.5)
			drawBars(xs, cy, '#ff000080', 0.8, 'actual')
		model_scores = {}
		for model_name in models[target]:
			# print model_name
			score_board = {}
			model = models[target][model_name]
			predict = model.predict(X)
			score_board['accuracy'] = metrics.accuracy_score(predict, y)
			score_board['mean_abs'] = metrics.mean_absolute_error(predict, y)
			proba = model.predict_proba(X)
			score_board['proba_mean'] = proba_mean(y, proba)
			if distr:
				cp = np.sum(proba, axis = 0)
			else:
				cp = Counter(predict)
				cp = [cp[i] if cp.has_key(i) else 0 for i in xs]
			if draw:
				plot_j += 1
				plt.subplot(target_n, model_n, plot_i * model_n + plot_j)
			score_board['overlaps'] = overlap(cp, cy, draw, model_name)
			model_scores[model_name] = score_board
		res[target] = model_scores
	if draw:
		plt.suptitle(title)
		plt.savefig('images/'+title+'.png')
		plt.show(block=False)
	return res

def dumpModels(models, overwrite = True):
	import os.path
	for filename in models:
		file_models = models[filename]
		for target in file_models:
			target_models = file_models[target]
			for model_name in target_models:
				dumpModelPath = 'models/'+'.'.join([filename[:4], target, model_name, 'm'])
				if not overwrite and os.path.isfile(dumpModelPath):
					continue
				model = target_models[model_name]
				joblib.dump(model, dumpModelPath)	

def loadModels():
	import os
	res = {}
	for files in os.walk('models/'):
		for filename in files[2]:
			tags = filename.split('.')
			# print filename, tags
			if tags[-1] != 'm' or len(tags) != 4:
				print 'skip: %s' % filename
				continue
			if not res.has_key(tags[0]):
				res[tags[0]] = {}
			if not res[tags[0]].has_key(tags[1]):
				res[tags[0]][tags[1]] = {}
			res[tags[0]][tags[1]][tags[2]] = joblib.load('models/'+filename)
		break
	return res

def proba_mean(y, proba):
	score = 0
	for i in range(len(y)):
		for j in range(len(proba[i])):
			score += proba[i][j] * abs(y[i] - j)
	return score/len(y)

def printScore(score, csv, func, distr):
	f = None
	h = [func, 'proba' if distr else 'predict']
	if csv:
		fcsv = open('modelsEvaluation.csv','a')
	for filename in score:
		file_scores = score[filename]
		for target in file_scores:
			target_scores = file_scores[target]
			for model_name in target_scores:
				model_scores = target_scores[model_name]
				s = [filename[:4], target, model_name]
				for metric in model_scores:
					ss = metric[:4]+" "+str(int(model_scores[metric] * 1000) / 1000.0)
					s.append(ss)
				s = h + s
				printstr = ''.join(['{0:<16}'.format(ss) for ss in s])
				print printstr
				if csv:
					fcsv.write(','.join(s) + '\n')
	if csv:
		fcsv.close()

def run(X, Y, filename):
	models = {}
	models[filename] = genModels(X,Y)
	dumpModels(models, True)
	# models = loadModels()
	score = scores(models, X, Y)
	printScore(score, csv = False, txt = False)
	return models

def drawBars(x, y1, y1_c, w, label_name):
	plt.bar(x, y1, fc = y1_c, width = w, label = label_name)
	# plt.legend()  
	for a,b in zip(x, y1):
	    plt.text(a, b+0.05, '%.0f' % b, ha='center', va= 'bottom',fontsize=7)

def overlap(y1, y2, draw = False, name = '', ratio = False):
	length = len(y1)
	if length != len(y2):
		print '[showBarChart params ERROR]: label count does not match'
		return -1
	count = sum(y2)
	if abs(sum(y1) - sum(y2)) > 1:
		print '[showBarChart params ERROR]: total count does not match'
		return -2

	overlaps = [min(y1[i], y2[i]) for i in range(length)]
	overlap_ratio = 100 * sum(overlaps) / (0.0 + count)

	if not draw:
		return overlap_ratio

	y1_c = '#00ff00' # green
	y2_c = '#ff0000' # red
	alpha = '80'
	# n = 2
	w = 0.8 # /n
	drawBars(range(length), y1, y1_c+alpha, w, 'predict')
	drawBars(range(length), overlaps, '#00000060', w, 'overlaps')
	if ratio:
		# drawBars([l+w for l in range(length)], y2, y2_c, w, 'actual')
		for a,b in zip(range(length), [ 100 * overlaps[i] / (max(y1[i], y2[i]) + 0.0) for i in range(length)]):
		    plt.text(a, 10, '%.0f%%' % b, ha='center', va= 'bottom', fontsize=10)
	l,h = plt.ylim()
	plt.ylim(l, h + 20)
	plt.title('%s (ovl: %.0f%%)' % (name,overlap_ratio), fontsize=10)

	return overlap_ratio

def getFTs():
	MAX_LAG = 6
	features_prototype = ['time','ltype','speed','gap','instype','state']
	# features_prototype = ['time','ltype','speed','gap','instype']
	# features_prototype = ['time','ltype','instype']
	targets = ['exp','hlag','rate']
	features = []
	for i in range(MAX_LAG):
		features += [f + str(i) for f in features_prototype]
	return features, targets

def main():
	FUNCTION = 'all'
	FUNCTION = '0 lag'
	FUNCTION = '1 lag overall'
	FUNCTION = '1 lag'
 
	LOAD = True
	# filenames = [(anim + '-Multiple') for anim in ['Desktop','Scroll','Open']]	
	filename = 'multipleLagsAttr.csv'
	raw_data = load_csv(filename)
	features, targets = getFTs()

	task_types = ['Open App', 'Scroll', 'Desktop']
	# task_types = ['Desktop']

	time_tags = ['time'+str(i) for i in range(6)]

	if LOAD: 
		models = loadModels()
	else:
		models = {}

	score = {}
	draw = True
	distr = False
	distr = True
	distrStr = 'prob' if distr else 'pred'

	# 1 lag
	if FUNCTION == '1 lag':
		for task_type in task_types:
			data = raw_data[(raw_data['type'] == task_type) &  (raw_data['num_of_lags'] == 1)]
			frames = data.time0.values
			for i in range(len(frames)):
				frames[i] = int((frames[i] + 5) / 16.6)
			cframes = Counter(frames)
			print cframes
			for i in cframes:
				if cframes[i] < 30:
					continue
				tdata = data[data['time0'] == i]
				X, Y = genData(tdata, features, targets)
				score[task_type] = scores(models[task_type[:4]], X, Y, draw, distr, title = '%s(%s)%s-(%d frames)' % (task_type, FUNCTION, distrStr, i))
		return

	# print scores
	if FUNCTION == 'all':
		for task_type in task_types:
			data = raw_data[raw_data['type'] == task_type]
			X, Y = genData(data, features, targets)
			if not LOAD:
				models[task_type] = genModels(X,Y)
				dumpModels(models, True)
			score[task_type] = scores(models[task_type[:4]], X, Y, draw, distr, '%s(%s)%s' % (task_type, FUNCTION, distrStr))

	# no lags
	if FUNCTION == '0 lag':
		for task_type in task_types:
			data = raw_data[(raw_data['type'] == task_type) &  (raw_data['num_of_lags'] == 0)]
			X, Y = genData(data, features, targets)
			score[task_type] = scores(models[task_type[:4]], X, Y, draw, distr, '%s(%s)%s' % (task_type, FUNCTION, distrStr))

	# 1 lag overall
	if FUNCTION == '1 lag overall':
		for task_type in task_types:
			data = raw_data[(raw_data['type'] == task_type) &  (raw_data['num_of_lags'] == 1)]
			X, Y = genData(data, features, targets)
			score[task_type] = scores(models[task_type[:4]], X, Y, draw, distr, '%s(%s)%s' % (task_type, FUNCTION, distrStr))

	printScore(score, True, FUNCTION, distr)


if __name__ == '__main__':
	# print 'hello'
	main()
