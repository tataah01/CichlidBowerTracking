import argparse, sys
from cichlid_bower_tracking.data_preparers.project_preparer import ProjectPreparer as PP

parser = argparse.ArgumentParser()
parser.add_argument('DataType', type = str, choices=['Prep','Depth','Cluster','ClusterClassification','Train3DResnet','TrainRCNN','ManualAnnotation','ManualLabelVideos','ManualLabelFrames', 'Summary','All'], help = 'What type of analysis to perform')
parser.add_argument('--ProjectID', type = str, help = 'Manually identify the projects you want to analyze. If All is specified, all non-prepped projects will be analyzed')
parser.add_argument('--VideoIndex', type = int, help = 'Specify which video should be downloaded if Cluster analysis is to be performed')
parser.add_argument('--ModelID', type = str, help = 'Specify a ModelID to download')
parser.add_argument('--SummaryFile', type = str, help = 'Name of csv file that specifies projects to analyze', default=None)

args = parser.parse_args()

#print('Downloading data for ' + args.ProjectID, file = sys.stderr)


pp_obj = PP(args.ProjectID, args.ModelID, summaryFile=args.SummaryFile)
pp_obj.downloadData(args.DataType, videoIndex = args.VideoIndex)

