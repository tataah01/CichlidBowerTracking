import subprocess, argparse, pdb
import pandas as pd

from cichlid_bower_tracking.helper_modules.file_manager import FileManager as FM

parser = argparse.ArgumentParser(description='This script is used to determine analysis states for each project.')
parser.add_argument('--SummaryFile', type = str, help = 'Restrict analysis to projectIDs specified in csv file, which will be rewritten. ProjectIDs must be found in a column called projectID')

args = parser.parse_args()

fm_obj = FM() 

if args.SummaryFile is not None:
	summary_file = fm_obj.localAnalysisStatesDir + args.SummaryFile
	fm_obj.downloadData(summary_file)
	dt = pd.read_csv(summary_file, index_col=False)
	projectIDs = list(dt.projectID)
else:
	fm_obj.createDirectory(fm_obj.localAnalysisStatesDir)
	summary_file = fm_obj.localAnalysisStatesDir + 'AllProjects.csv'
	projectIDs = fm_obj.getAllProjectIDs()
	dt = pd.DataFrame(columns = ['projectID', 'tankID', 'StartingFiles', 'Prep', 'Depth', 'Cluster', 'ClusterClassification', 'LabeledVideos', 'LabeledFrames', 'Summary'])

columns = ['projectID', 'tankID', 'StartingFiles', 'Prep', 'Depth', 'Cluster', 'ClusterClassification', 'LabeledVideos', 'LabeledFrames', 'Summary']

for c in columns:
	if c not in dt.columns:
		dt[c] = False

for projectID in projectIDs:
	fm_obj.createProjectData(projectID)
	
	out_data = fm_obj.getProjectStates()

	for k, v in out_data.items():
		if k == 'projectID':
			continue
		dt.loc[dt.projectID == projectID, k] = v

	subprocess.run(['rm', '-rf', fm_obj.localProjectDir])

dt.to_csv(summary_file, index = False)
fm_obj.uploadData(summary_file)


