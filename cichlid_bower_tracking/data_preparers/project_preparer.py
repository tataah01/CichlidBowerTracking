import datetime, os, subprocess, pdb

from cichlid_bower_tracking.helper_modules.file_manager import FileManager as FM
from cichlid_bower_tracking.data_preparers.prep_preparer import PrepPreparer as PrP
from cichlid_bower_tracking.data_preparers.depth_preparer import DepthPreparer as DP
from cichlid_bower_tracking.data_preparers.cluster_preparer import ClusterPreparer as CP
from cichlid_bower_tracking.data_preparers.threeD_classifier_preparer import ThreeDClassifierPreparer as TDCP
from cichlid_bower_tracking.data_preparers.manual_label_video_preparer import ManualLabelVideoPreparer as MLVP
from cichlid_bower_tracking.data_preparers.manual_label_frames_preparer import ManualLabelFramesPreparer as MLFP
from cichlid_bower_tracking.data_preparers.threeD_model_preparer import ThreeDModelPreparer as TDMP
from cichlid_bower_tracking.data_preparers.summary_preparer import SummaryPreparer as SP

class ProjectPreparer():
	# This class takes in a projectID and runs all the appropriate analysis

	def __init__(self, projectID = None, modelID = None, workers = None, summaryFile=None):
		self.projectID = projectID
		if modelID == 'None':
			modelID = None
		self.fileManager = FM(projectID = projectID, modelID = modelID, summaryFile=summaryFile)
		self.modelID = modelID
		if not self._checkProjectID():
			raise Exception(projectID + ' is not valid.')
		self.workers = workers

	def _checkProjectID(self):
		if self.projectID is None:
			return True
		projectIDs = subprocess.run(['rclone', 'lsf', self.fileManager.cloudMasterDir + '__ProjectData/'], capture_output = True, encoding = 'utf-8').stdout.split()
		if self.projectID + '/' in projectIDs:
			return True
		else:
			pdb.set_trace()
			return False

	def downloadData(self, dtype, videoIndex = None):
		self.fileManager.downloadProjectData(dtype, videoIndex)

	def uploadData(self, dtype, videoIndex = None, delete = False, no_upload = False):
		print(no_upload)
		self.fileManager.uploadProjectData(dtype, videoIndex, delete, no_upload)

	def runPrepAnalysis(self):
		prp_obj = PrP(self.fileManager)
		prp_obj.validateInputData()
		prp_obj.prepData()

	def runDepthAnalysis(self):
		dp_obj = DP(self.fileManager)
		dp_obj.validateInputData()
		dp_obj.createSmoothedArray()
		dp_obj.createRGBVideo()

	def runClusterAnalysis(self, videoIndex):
		if videoIndex is None:
			videos = list(range(len(self.fileManager.lp.movies)))
		else:
			videos = [videoIndex]
		for videoIndex in videos:
			cp_obj = CP(self.fileManager, videoIndex, self.workers)
			cp_obj.validateInputData()
			cp_obj.runClusterAnalysis()

	def run3DClassification(self):
		tdcp_obj = TDCP(self.fileManager)
		tdcp_obj.validateInputData()
		tdcp_obj.predictLabels()
		tdcp_obj.createSummaryFile()

	def manuallyLabelVideos(self, initials, number):
		mlv_obj = MLVP(self.fileManager, initials, number)
		mlv_obj.validateInputData()
		mlv_obj.labelVideos()

	def manuallyLabelFrames(self, initials, number):
		mlf_obj = MLFP(self.fileManager, initials, number)
		mlf_obj.validateInputData()
		mlf_obj.labelFrames()
	
	def createModel(self, MLtype, projectIDs, gpu):
		if MLtype == '3DResnet':
			tdm_obj = TDMP(self.fileManager, projectIDs, self.modelID, gpu)
			tdm_obj.validateInputData()
			tdm_obj.create3DModel()

	def runMLFishDetection(self):
		pass

	def runSummaryCreation(self):
		sp_obj = SP(self.fileManager)
		sp_obj.createFullSummary()

	def backupAnalysis(self):
		uploadCommands = set()

		uploadFiles = [x for x in os.listdir(self.fileManager.localUploadDir) if 'UploadData' in x]

		for uFile in uploadFiles:
			with open(self.fileManager.localUploadDir + uFile) as f:
				line = next(f)
				for line in f:
					tokens = line.rstrip().split(',')
					tokens[2] = bool(int(tokens[2]))
					uploadCommands.add(tuple(tokens))

		for command in uploadCommands:
			self.fileManager.uploadData(command[0], command[1], command[2])

		for uFile in uploadFiles:
			subprocess.run(['rm', '-rf', self.fileManager.localUploadDir + uFile])

		self.fileManager.uploadData(self.fileManager.localAnalysisLogDir, self.fileManager.cloudAnalysisLogDir, False)
		subprocess.run(['rm', '-rf', self.projFileManager.localMasterDir])

	def localDelete(self):
		subprocess.run(['rm', '-rf', self.fileManager.localProjectDir])

	def createUploadFile(self, uploads):
		with open(self.fileManager.localUploadDir + 'UploadData_' + str(datetime.datetime.now().timestamp()) + '.csv', 'w') as f:
			print('Local,Cloud,Tar', file = f)
			for upload in uploads:
				print(upload[0] + ',' + upload[1] + ',' + str(upload[2]), file = f)

	def createAnalysisUpdate(self, aType, procObj):
		now = datetime.datetime.now()
		with open(self.fileManager.localAnalysisLogDir + 'AnalysisUpdate_' + str(now.timestamp()) + '.csv', 'w') as f:
			print('ProjectID,Type,Version,Date', file = f)
			print(self.projectID + ',' + aType + ',' + procObj.__version__ + '_' + os.getenv('USER') + ',' + str(now), file= f)
