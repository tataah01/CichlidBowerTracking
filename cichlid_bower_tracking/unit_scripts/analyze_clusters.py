import argparse, pdb, sys
from cichlid_bower_tracking.data_preparers.project_preparer import ProjectPreparer as PP

parser = argparse.ArgumentParser(usage = 'This script will analyze HD videos to determine sand manipulation events')
parser.add_argument('ProjectID', type = str, help = 'Which projectID you want to identify')
parser.add_argument('AnalysisID', type = str, help = 'Which analysis state this project belongs to')
parser.add_argument('--VideoIndex', type = int, help = 'Index of video that should be analyzed')
parser.add_argument('--Workers', type = int, help = 'Number of threads to run this analysis in parallel')
args = parser.parse_args()

print('Analyzing cluster data for ' + args.ProjectID, file = sys.stderr)

pp_obj = PP(projectID = args.ProjectID, analysisID = args.AnalysisID, workers = args.Workers)

pp_obj.runClusterAnalysis(args.VideoIndex)

