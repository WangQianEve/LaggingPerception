from files_io import load_csv

# import mord
from sklearn.externals import joblib

def main():
	modelpath = './models6/'
	task_type = 'Desktop'
	target = 'exp'
	model = joblib.load('%s%s.%s.m' % (modelpath, task_type, target))

	filename = 'test_data.csv'
	data = load_csv(filename)

	results = model.predict_proba(data)
	print results

if __name__ == '__main__':
	main()
