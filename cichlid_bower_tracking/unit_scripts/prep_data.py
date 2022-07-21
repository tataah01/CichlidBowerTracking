import argparse, subprocess
from cichlid_bower_tracking.data_preparers.prep_preparer import PrepPreparer as PrP
from cichlid_bower_tracking.helper_modules.file_manager import FileManager as FM

parser = argparse.ArgumentParser(usage = 'This script will prompt user to identify tray location and registration info between depth and video data. Works on a single projectID')
parser.add_argument('ProjectID', type = str, help = 'Manually identify the project you want to analyze')
parser.add_argument('AnalysisID', type = str, help = 'Manually identify the project you want to analyze')

args = parser.parse_args()

fileManager = FM(projectID = args.ProjectID, analysisID=args.AnalysisID)

prp_obj = PrP(fileManager = fileManager)
prp_obj.validateInputData()
prp_obj.prepData()