import argparse, sys
from cichlid_bower_tracking.data_preparers.project_preparer import ProjectPreparer as PP

parser = argparse.ArgumentParser()
parser.add_argument('DataType', type = str, choices=['Prep','Depth','Cluster','ClusterClassification','TrackFish','AssociateClustersWithTracks', 'Train3DResnet','TrainRCNN','ManualAnnotation','ManualLabelVideos','ManualLabelFrames', 'Summary','All'], help = 'What type of analysis to perform')
parser.add_argument('AnalysisID', type = str, help = 'The ID of the analysis state this project belongs to')
parser.add_argument('ProjectID', type = str, help = 'Identify the project you want to analyze.')
parser.add_argument('--VideoIndex', nargs = '+', help = 'Optional argument to only download data for a subset of videos')

args = parser.parse_args()

fm_obj = FM(args.AnalysisID, projectID = args.ProjectID)
fm_obj.downloadProjectData(args.DataType, videoIndex = args.VideoIndex)

