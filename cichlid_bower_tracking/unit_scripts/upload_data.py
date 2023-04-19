# Things to add

import argparse,sys
from cichlid_bower_tracking.helper_modules.file_manager import FileManager as FM

parser = argparse.ArgumentParser()
parser.add_argument('DataType', type = str, choices=['Prep','Depth','Cluster','ClusterClassification', 'TrackFish', 'Train3DResnet', 'ManualLabelVideos','Summary','All'], help = 'What type of analysis to perform')
parser.add_argument('AnalysisID', type = str, help = 'The ID of the analysis state this project belongs to')
parser.add_argument('ProjectID', type = str, help = 'Manually identify the projects you want to analyze. If All is specified, all non-prepped projects will be analyzed')
parser.add_argument('--VideoIndex', nargs = '+', help = 'Specify which video should be downloaded if Cluster analysis is to be performed')
parser.add_argument('--Delete', action = 'store_true', help = 'Delete data once it is uploaded')

args = parser.parse_args()

fm_obj = FM(args.AnalysisID, projectID = args.ProjectID)
fm_obj.uploadProjectData(args.DataType, args.VideoIndex, args.Delete)
