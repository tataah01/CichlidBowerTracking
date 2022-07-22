import subprocess, argparse, pdb
import pandas as pd

from cichlid_bower_tracking.helper_modules.file_manager import FileManager as FM

parser = argparse.ArgumentParser(description='This script is used to determine analysis states for each project.')
parser.add_argument('AnalysisID', type = str, help = 'AnalysisID of the set of projects that you want to analyze. There must be a csv file already created in __AnalysisStates directory')

args = parser.parse_args()

fm_obj = FM(analysisID = args.AnalysisID) 

	summary_file = fm_obj.localSummaryFile
	fm_obj.downloadData(summary_file)
	dt = pd.read_csv(summary_file, index_col=False)
	projectIDs = list(dt.projectID)

columns = ['projectID', 'Notes', 'tankID', 'RunAnalysis', 'StartingFiles', 'Prep', 'Depth', 'Cluster', 'ClusterClassification', 'LabeledVideos', 'LabeledFrames', 'Summary']

for c in columns:
	if c not in dt.columns:
		dt[c] = 'FALSE'

for projectID in projectIDs:
	fm_obj.createProjectData(projectID)
	
	out_data = fm_obj.getProjectStates()

	for k, v in out_data.items():
		if k == 'projectID':
			continue
		dt.loc[dt.projectID == projectID, k] = str(v).upper()

	subprocess.run(['rm', '-rf', fm_obj.localProjectDir])

dt.to_csv(summary_file, index = False)
fm_obj.uploadData(summary_file)


