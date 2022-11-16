import subprocess, os, pdb, datetime
import pandas as pd
import numpy as np
from shapely.geometry import Point, Polygon

class ClusterTrackAssociationPreparer():
	# This class takes in directory information and a logfile containing depth information and performs the following:
	# 1. Identifies tray using manual input
	# 2. Interpolates and smooths depth data
	# 3. Automatically identifies bower location
	# 4. Analyze building, shape, and other pertinent info of the bower

	def __init__(self, fileManager):

		self.__version__ = '1.0.0'
		self.fileManager = fileManager

	def validateInputData(self):
		
		assert os.path.exists(self.fileManager.localLogfileDir)
		assert os.path.exists(self.fileManager.localAllFishDetectionsFile)
		assert os.path.exists(self.fileManager.localAllFishTracksFile)
		assert os.path.exists(self.fileManager.localOldVideoCropFile)
		assert os.path.exists(self.fileManager.localAllLabeledClustersFile)

	def runAssociationAnalysis(self):
		video_crop = np.load(self.fileManager.localOldVideoCropFile)
		poly = Polygon(video_crop)

		t_dt = pd.read_csv(self.fileManager.localAllFishTracksFile, index_col = 0)
		d_dt = pd.read_csv(self.fileManager.localAllFishDetectionsFile, index_col=0)
		c_dt = pd.read_csv(self.fileManager.localAllLabeledClustersFile, index_col = 0)

		pdb.set_trace()

		# 1. Summarize tracks (summarized.csv)
		# Write code to determine the sex of each track and whether it is a reflection

		# 2. Associate track with cluster (associatedCluster.csv)
		# Write code to add track, sex, and reflection data to each cluster
