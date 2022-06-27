import argparse, sys
from cichlid_bower_tracking.helper_modules.cichlid_tracker import CichlidTracker as CT

parser = argparse.ArgumentParser(usage='This command starts a script on a Raspberry Pis to collect depth and RGB data. Allows control through a Google Spreadsheet.')
parser.add_argument('-a', '--all_data', action = 'store_true', help = 'Use this option if want to store all of the depth data used to create frames. Will increase size by ~30 fold')

args = parser.parse_args()
	
CT(args.all_data)
