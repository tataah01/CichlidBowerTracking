import argparse, subprocess, pdb, datetime, os, sys
import pandas as pd
from cichlid_bower_tracking.helper_modules.file_manager import FileManager as FM

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)


parser = argparse.ArgumentParser(
    description='This script is used to manually prepared projects for downstream analysis')
parser.add_argument('AnalysisType', type=str, choices=['Prep', 'Depth', 'Cluster', 'ClusterClassification', 'Summary'],
                    help='Type of analysis to run')
parser.add_argument('AnalysisID', type = str, help = 'ID of analysis state name')
group.add_argument('--ProjectIDs', type=str, nargs='+', help='Name of projectIDs to restrict analysis to')
group.add_argument('--SummaryFile', type=str, help='Name of csv file that specifies projects to analyze')
parser.add_argument('--Workers', type=int, help='Number of workers')
parser.add_argument('--ModelID', type=str, help='ModelID to use to classify clusters with')
args = parser.parse_args()

# Identify projects to run analysis on
fm_obj = FM(analysisID = args.AnalysisID)
if not fm_obj.checkFileExists(fm_obj.localSummaryFile):
    print('Cant find ' + fm_obj.localSummaryFile)
    sys.exit()

fm_obj.downloadData(fm_obj.localSummaryFile)
dt = pd.read_csv(summary_file, index_col = False, dtype = {'StartingFiles':str, 'Prep':str, 'Depth':str, 'Cluster':str, 'ClusterClassification':str,'LabeledVideos':str,'LabeledFrames': str, 'Summary': str})
projectIDs = list(dt[dt[args.AnalysisType].str.upper() == 'FALSE'].projectID) # Only run analysis on projects that need it


if args.Workers is None:
    workers = os.cpu_count()
else:
    workers = args.Workers
#if args.ModelID is None:
#    args.ModelID = 'Model18_All'

# To run analysis efficiently, we download and upload data in the background while the main script runs
uploadProcesses = [] # Keep track of all of the processes still uploading so we don't quit before they finish

if args.SummaryFile is not None:
    dt.loc[dt.projectID == projectIDs[0],args.AnalysisType] = 'Running'
    dt.to_csv(summary_file, index = False)
    fm_obj.uploadData(summary_file)

print('Downloading: ' + projectIDs[0] + ' ' + str(datetime.datetime.now()), flush = True)
subprocess.run(['python3', '-m', 'cichlid_bower_tracking.unit_scripts.download_data',args.AnalysisType, '--ProjectID', projectIDs[0], '--ModelID', str(args.ModelID)])
while len(projectIDs) != 0:
    projectID = projectIDs[0]

    print('Running: ' + projectID + ' ' + str(datetime.datetime.now()), flush = True)

    # Run appropriate analysis script
    if args.AnalysisType == 'Prep':
        p1 = subprocess.Popen(['python3', '-m', 'cichlid_bower_tracking.unit_scripts.prep_data', projectID])
    elif args.AnalysisType == 'Depth':
        p1 = subprocess.Popen(['python3', '-m', 'cichlid_bower_tracking.unit_scripts.analyze_depth', projectID])
    elif args.AnalysisType == 'Cluster':
        p1 = subprocess.Popen(
            ['python3', '-m', 'cichlid_bower_tracking.unit_scripts.analyze_clusters', projectID, '--Workers',
             str(workers)])
    elif args.AnalysisType == 'ClusterClassification':
        p1 = subprocess.Popen(
            ['python3', '-m', 'cichlid_bower_tracking.unit_scripts.classify_clusters', projectID, args.ModelID])
    elif args.AnalysisType == 'Summary':
        if args.SummaryFile is None:
            p1 = subprocess.Popen(['python3', '-m', 'cichlid_bower_tracking.unit_scripts.summarize', projectID])
        else:
            p1 = subprocess.Popen(
                ['python3', '-m', 'cichlid_bower_tracking.unit_scripts.summarize', projectID, '--SummaryFile',
                 args.SummaryFile])

    # In the meantime, download data for next project in the background

    if args.SummaryFile:
        fm_obj.downloadData(summary_file)
        dt = pd.read_csv(summary_file, index_col = False, dtype = {'StartingFiles':str, 'Prep':str, 'Depth':str, 'Cluster':str, 'ClusterClassification':str,'LabeledVideos':str,'LabeledFrames': str})
        projectIDs = list(dt[dt[args.AnalysisType].str.upper() == 'FALSE'].projectID) # Only run analysis on projects that need it

        if len(projectIDs) != 0:
            dt.loc[dt.projectID == projectIDs[0],args.AnalysisType] = 'Running'
            dt.to_csv(summary_file, index = False)
            fm_obj.uploadData(summary_file)

            print('Downloading: ' + projectIDs[0] + ' ' + str(datetime.datetime.now()), flush = True)
            p2 = subprocess.Popen(['python3', '-m', 'cichlid_bower_tracking.unit_scripts.download_data', args.AnalysisType, '--ProjectID', projectIDs[0]])

    else:
        projectIDs = projectIDs[1:]
        if len(projectIDs) != 0:
            print('Downloading: ' + projectIDs[0] + ' ' + str(datetime.datetime.now()), flush = True)
            p2 = subprocess.Popen(['python3', '-m', 'cichlid_bower_tracking.unit_scripts.download_data', args.AnalysisType, '--ProjectID', projectIDs[0]])

    # Pause script until current analysis is complete and data for next project is downloaded
    p1.communicate()
    if p1.returncode != 0:
        sys.exit()
    try:
        p2.communicate() # Need to catch an exception if only one project is analyzed
    except NameError:
        pass
    #Modify summary file if necessary
    if args.SummaryFile:
        fm_obj.downloadData(summary_file)
        dt = pd.read_csv(summary_file, index_col = False, dtype = {'StartingFiles':str, 'Prep':str, 'Depth':str, 'Cluster':str, 'ClusterClassification':str,'LabeledVideos':str,'LabeledFrames': str})

        dt.loc[dt.projectID == projectID,args.AnalysisType] = 'TRUE'
        dt.to_csv(summary_file, index = False)
        fm_obj.uploadData(summary_file)


    #Upload data and keep track of it
    print('Uploading: ' + projectID + ' ' + str(datetime.datetime.now()), flush = True)

    uploadProcesses.append(subprocess.Popen(
        ['python3', '-m', 'cichlid_bower_tracking.unit_scripts.upload_data', args.AnalysisType, '--Delete',
         '--ProjectID', projectID]))
# uploadProcesses.append(subprocess.Popen(['python3', '-m', 'cichlid_bower_tracking.unit_scripts.upload_data', args.AnalysisType, projectID]))

for i,p in enumerate(uploadProcesses):
    print('Finishing uploading process ' + str(i) + ': ' + str(datetime.datetime.now()), flush = True)
    p.communicate()

"""
if args.AnalysisType == 'Summary':
    import PyPDF2 as pypdf
    paths = [x for x in os.listdir(fm_obj.localAnalysisStatesDir) if '_DepthSummary.pdf' in x]
    writer = pypdf.PdfFileWriter()
    for path in paths:
        f = open(fm_obj.localAnalysisStatesDir + path, 'rb')
        reader = pypdf.PdfFileReader(f)
        for page_number in range(reader.numPages):
            writer.addPage(reader.getPage(page_number))
    with open(fm_obj.localAnalysisStatesDir + 'Collated_DepthSummary.pdf', 'wb') as f:
        writer.write(f)
    print('Finished analysis: ' + str(datetime.datetime.now()), flush = True)
    fm_obj.uploadData(fm_obj.localAnalysisStatesDir + 'Collated_DepthSummary.pdf')
"""
