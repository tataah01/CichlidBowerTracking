from cichlid_bower_tracking.helper_modules.file_manager import FileManager as FM
import argparse, subprocess, os, pdb

parser = argparse.ArgumentParser()
parser.add_argument('VideoFile', type = str, help = 'Name of h264 file to be processed')
parser.add_argument('Framerate', type = float, help = 'Video framerate')
parser.add_argument('ProjectID', type = str, help = 'Video framerate')

args = parser.parse_args()

fileManager = FM(projectID = args.ProjectID)

if '.h264' not in args.VideoFile:
	raise Exception(args.VideoFile + ' not an h264 file')

# Convert h264 to mp4
ffmpeg_output = subprocess.run(['ffmpeg', '-r', str(args.Framerate), '-i', args.VideoFile, '-threads', '1', '-c:v', 'copy', '-r', str(args.Framerate), args.VideoFile.replace('.h264', '.mp4')], capture_output = True)

try:
	assert os.path.isfile(args.VideoFile.replace('.h264', '.mp4'))
	assert os.path.getsize(args.VideoFile.replace('.h264','.mp4')) > os.path.getsize(args.VideoFile)
except:
	pdb.set_trace()

# Sync with cloud (will return error if something goes wrong)
try:
	fileManager.uploadData(args.VideoFile.replace('.h264', '.mp4'))
except:
	try:
		fileManager.uploadData(args.VideoFile.replace('.h264', '.mp4'))
	except:
		try:
			fileManager.uploadData(args.VideoFile.replace('.h264', '.mp4'))
		except:
			pdb.set_trace()

# Move video

subprocess.run(['mv', args.VideoFile, args.VideoFile.split('/Videos/')[0] + '/Backups/'])
#subprocess.run(['rm', '-f', args.VideoFile])
#subprocess.run(['rm', '-f', args.VideoFile.replace('.h264', '.mp4')])

print('Video Processed')

