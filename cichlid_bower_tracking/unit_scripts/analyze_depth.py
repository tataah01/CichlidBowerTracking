import argparse, pdb, sys
from cichlid_bower_tracking.data_preparers.project_preparer import ProjectPreparer as PP

parser = argparse.ArgumentParser(usage = 'This script will use a previously trained 3D Resnet model to classify videos')
parser.add_argument('ProjectID', type = str, help = 'Which projectID you want to identify')
parser.add_argument('AnalysisID', type = str, help = 'Which analysis state this project belongs to')

args = parser.parse_args()

print('Analyzing depth data for ' + args.ProjectID, file = sys.stderr)

pp_obj = PP(args.ProjectID, args.AnalysisID)
pp_obj.runDepthAnalysis()

