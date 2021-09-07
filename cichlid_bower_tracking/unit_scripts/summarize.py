import argparse
from cichlid_bower_tracking.data_preparers.project_preparer import ProjectPreparer as PP

parser = argparse.ArgumentParser(usage='This script is run after analysis to create useful figures and summary files')
parser.add_argument('ProjectID', type=str, help='Which projectID you want to identify')
parser.add_argument('--SummaryFile', type = str, help = 'Name of csv file that specifies projects to analyze', default=None)
args = parser.parse_args()

pp_obj = PP(args.ProjectID, summaryFile=args.SummaryFile)

pp_obj.runSummaryCreation()
