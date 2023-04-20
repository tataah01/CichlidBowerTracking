import pandas as pd
import pdb, json, os
import fiftyone as fo
import fiftyone.zoo as foz
import fiftyone.utils.random as four

from helper_modules.file_manager import FileManager as FM

fm_obj = FM('PatrickTesting')

task_folder = fm_obj.localObjectDetectionDir + '1_task_data/'
fm_obj.downloadData(task_folder)

for batch in [x for x in os.listdir(task_folder) if x[0] != '.']:
	with open(task_folder + batch + '/' + 'annotations.json') as json_data:
		data = json.load(json_data)
		temp_dt = pd.DataFrame(data[0]['shapes'])
		annotator = batch.split('_')[1]

		temp_dt['annotator'] = annotator

	with open(task_folder + batch + '/data/manifest.jsonl') as f:
		f.readlines(2)
		f.readlines(2)
		frames = pd.read_json(f, lines = True)
		frames.reset_index(inplace = True)
		frames['name'] = frames['name'] + '.jpg'
	with open(task_folder + batch + '/task.json') as f:
		task = json.load(f)
	print(batch.split('_')[1])
	print(task['data']['start_frame'])
	print(task['data']['stop_frame'])

	temp_dt['frame'] = temp_dt['frame'] + task['data']['start_frame']
	if annotator == 'bree':
		temp_dt = temp_dt[temp_dt.frame >= 750]
	elif annotator == 'mcgrath':
		temp_dt = temp_dt[temp_dt.frame < 250]
	elif annotator == 'chinar':
		temp_dt = temp_dt[(temp_dt.frame > 550) & (temp_dt.frame < 750)]

	temp_dt = pd.merge(temp_dt, frames, left_on = 'frame', right_on = 'index')[['type','points','frame','attributes','label','annotator','name']]

	try:
		dt = pd.concat([dt, temp_dt]).sort_values('frame')
	except NameError:
		dt = temp_dt

dt['frame_number'] = dt.name.str.split('/', expand = True)[1].str.split('_', expand = True)[7].str.replace('.jpg', '')
dt['projectID'] = dt.name.str.split('/', expand = True)[1].str.split('vid', expand = True)[0].str[0:-6]
dt['video_id'] = dt.name.str.split('/', expand = True)[1].str.split('_', expand = True)[5] + '_vid'
dt['file_path'] = task_folder + batch + '/data/' + dt.name

width = frames.width[0]
height = frames.height[0]

samples = []
for frame in set(dt.file_path):
	f_dt = dt[dt.file_path == frame]
	sample = fo.Sample(filepath=frame)
	detections = []
	for i,annotation in f_dt.iterrows():
		bounding_box = annotation.points
		bounding_box = [bounding_box[0]/width, bounding_box[1]/height, (bounding_box[2] - bounding_box[0])/width, (bounding_box[3] - bounding_box[1])/height]
		if annotation.label == 'Reflection':
			detections.append(fo.Detection(label = 'Reflection', bounding_box = bounding_box))
		else:
			detections.append(fo.Detection(label = 'Fish', bounding_box = bounding_box))
	sample['ground_truth'] = fo.Detections(detections=detections)
	sample['projectID'] = annotation.projectID
	sample['videoID'] = annotation.video_id
	sample['frame_name'] = annotation.name
	samples.append(sample)

dataset = fo.Dataset("my-detection-dataset")
dataset.add_samples(samples)
four.random_split(dataset, {'train': 0.9, 'val': 0.1})

for split in ['train','val']:
	split_view = dataset.match_tags('val')
	split_view.export(export_dir=fm_obj.localYolov5AnnotationsDir, dataset_type=fo.types.YOLOv5Dataset,label_field="ground_truth", split = split, classes=['Fish','Reflection'])

fm_obj.uploadData(fm_obj.localYolov5AnnotationsDir, tarred = True)
#1 Check coordinate points top left top right
#2 Add tank add annotator information to sample
#3 Split into training/validation
#4 Save fiftyone object
#5 Export yolov5 object


# Next train yolov5 network (see Tucker doc LabProtocols/AutomatedAnalysisProtocols for help)

# Next upload predictions into fifty one object