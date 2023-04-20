from cichlid_bower_tracking.helper_modules.file_manager import FileManager as FM
import argparse, GPUtil, os, sys, subprocess, yaml, pdb

# This code ensures that modules can be found in their relative directories
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)

# Create arguments for the script
parser = argparse.ArgumentParser(description='This script is used to manually prepared projects for downstream analysis')
parser.add_argument('AnalysisType', type=str, choices=['FishDetection','SexDetermination','SandManipulationClassification'], help='Type of analysis to run')
parser.add_argument('AnalysisID', type = str, help = 'ID of analysis state name')
args = parser.parse_args()



# Identify projects to run analysis on
fm_obj = FM(args.AnalysisID)
fm_obj.downloadData(fm_obj.localSummaryFile)
if not fm_obj.checkFileExists(fm_obj.localSummaryFile):
    print('Cant find ' + fm_obj.localSummaryFile)
    sys.exit()

if args.AnalysisType == 'FishDetection':
	
	fm_obj.downloadData(fm_obj.localYolov5AnnotationsDir, tarred = True)
	with open(fm_obj.localYolov5AnnotationsDir + 'dataset.yaml', 'r') as file:
		dataset = yaml.safe_load(file)
	pdb.set_trace()

	fm_obj.downloadData(fm_obj.localObjectDetectionDir + 'hyp.yaml')

	gpu = GPUtil.getAvailable(order = 'first', maxMemory = 0.2, limit = 8)[0]

	command = ['python3', 'train.py']
	command.extend(['--device', str(gpu)])
	command.extend(['--epochs', '300'])
	command.extend(['--batch-size','-1'])
	command.extend(['--optimizer','AdamW'])
	command.extend(['--hyp',fm_obj.localObjectDetectionDir + 'hyp.yaml'])
	command.extend(['--data',fm_obj.localYolov5AnnotationsDir + 'dataset.yaml'])

	command = "source " + os.getenv('HOME') + "/anaconda3/etc/profile.d/conda.sh; conda activate yolov5; " + ' '.join(command)

	os.chdir(os.getenv('HOME') + '/yolov5')
	print('bash -c \"' + command + '\"')
	output = subprocess.Popen('bash -c \"' + command + '\"', shell = True, stderr = open(os.getenv('HOME') + '/' + 'training_errors.txt', 'w'), stdout=subprocess.DEVNULL)
