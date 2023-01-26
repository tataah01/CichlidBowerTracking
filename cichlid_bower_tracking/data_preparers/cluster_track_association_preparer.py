import subprocess, os, pdb, datetime
import pandas as pd
import numpy as np
from shapely.geometry import Point, Polygon
import datetime

def bin_tracklength(tl):
    tl = tl/30
    if tl <= 0.5:
        tl = '0-0.5s'
    elif tl <= 1:
        tl = '0.5-1.0s'
    elif tl <= 3:
        tl = '1.0-3.0s'
    elif tl <= 10:
        tl = '3.0-10.0s'
    elif tl <= 30:
        tl = '10.0-30.0s'
    else:
        tl = '>30.0s'

    return tl

class base:
 
    '''
    This converts the dataframe into comparable format 
    for example, 
    yolo does not output boxes in a format directly useable by open CV 
    We fix that here
    
    '''
   
    #this may need to consider switch if x y values not equal
    ydelta=60
    xdelta=60
    framerate=29
    #might be 30 sometimes
    IMG_W = 1296
    IMG_H = 972
    tdelta=framerate*2
    
    def __init__(self, path):
        self.path = path
        
    def clean_cluster(self):
        df=pd.read_csv(self.path, index_col=0)
        df['cluster_id']=df['LID'].copy()
        df['base_name']=df['VideoID'] .copy()
        df['yc']=df['X'].copy()
        df['xc']=df['Y'].copy()
        df['frame_span']=df['t_span'].copy()
        #convert to retangle points
        df['x1']=df['xc']-self.xdelta
        df['y1']=df['yc']-self.ydelta
        df['x2']=df['xc']+self.xdelta
        df['y2']=df['yc']+self.ydelta
        df['sframe']=(df['t']*self.framerate - self.tdelta).astype('int64')
        df['eframe']= (df['t']*self.framerate + self.tdelta).astype('int64')
        df=df[df['ClipCreated']=='Yes'] 
        return df   


    def clean_sort(self):
        df=pd.read_csv(self.path, index_col=0)
        #sort to pixel conversion rectangular form
        df['x1']=self.IMG_W*(df['xc']-0.5*df['w'])
        df['y1']=self.IMG_H*(df['yc']-0.5*df['h'])
        df['x2']=self.IMG_W*(df['xc']+0.5*df['w'])
        df['y2']=self.IMG_H*(df['yc']+0.5*df['h'])
        df['xc']=self.IMG_W*(df['xc'])
        df['yc']=self.IMG_H*(df['yc'])
        #df.rename(columns={'class_id': 'class'},inplace=True)
        return df

class ClusterTrackAssociationPreparer():
    # This class takes in directory information and a logfile containing depth information and performs the following:
    # 1. Identifies tray using manual input
    # 2. Interpolates and smooths depth data
    # 3. Automatically identifies bower location
    # 4. Analyze building, shape, and other pertinent info of the bower

    def __init__(self, fileManager):

        self.__version__ = '1.0.0'
        self.fm = fileManager

    def validateInputData(self):
        
        assert os.path.exists(self.fm.localLogfileDir)
        assert os.path.exists(self.fm.localAllFishDetectionsFile)
        assert os.path.exists(self.fm.localAllFishTracksFile)
        assert os.path.exists(self.fm.localOldVideoCropFile)
        assert os.path.exists(self.fm.localAllLabeledClustersFile)
    
    
        
    def find_identity(self,clusterdf, sortdf):
        
        #self.clusterdf['frame']=self.clusterdf['sframe']
        #clusterdf.rename(columns={'xc': 'xc1', 'yc': 'yc1'},inplace=True)
        #startdf= pd.merge(self.clusterdf, self.sortdf, on=["frame"])
        #startdf['distance']=np.sqrt( np.array(((startdf['xc']-startdf['xc1'])**2+((startdf['yc']-startdf['yc1']))**2), dtype=np.float64))
        df=pd.DataFrame(columns=list(clusterdf.columns)+['track_id', 'class'])
        nodf=pd.DataFrame(columns=clusterdf.columns)
        for i in clusterdf['base_name'].unique():
            cdf=clusterdf[clusterdf['base_name']==i].copy()
            tdf=sortdf[sortdf['base_name']==i].copy()
            for index, row in cdf.iterrows():
                 startdf=tdf[(tdf['frame']>=row['sframe']) & (tdf.frame<=row['eframe'])].copy()
                 if not startdf.empty:
                     startdf['distance'] = (startdf.xc + startdf.yc * 1j - (row.xc + row.yc * 1j)).abs()
                     startdf['meandist']=startdf.groupby('track_id').distance.transform(lambda x : x.mean())
                     startdf=startdf.loc[startdf['meandist'].idxmin]
                     row['track_id'] = startdf.track_id
                     row['class']=startdf.class_id
                     df=pd.concat([df, row.to_frame().T])
                     #MC_singlenuc21_3_Tk53_021220
                     #check this after run
                     
                 else:
                     nodf=pd.concat([nodf, row.to_frame().T])
        #change this
        df.to_csv(self.fm.localAllTracksAsscociationFile)
        return df
    
    def create_summary(self, poly, t_dt, d_dt):
        t_output = [poly.contains(Point(x, y)) for x,y in zip(t_dt.xc, t_dt.yc)]
        t_dt['InBounds'] = t_output
        track_lengths = t_dt.groupby('track_id').count()['base_name'].rename('track_length')
        t_dt = pd.merge(t_dt, track_lengths, left_on = 'track_id', right_on = track_lengths.index)
        t_dt['binned_track_length'] = t_dt.track_length.apply(bin_tracklength)

        try:
            temp = t_dt[t_dt.p_value > .7].groupby(['track_id', 'track_length', 'base_name']).mean()[['class', 'p_value','InBounds']].rename({'class':'SexCall'}, axis = 1).reset_index().sort_values(['base_name','track_id'])
            temp.to_csv(self.fm.localAllTracksSummaryFile, index = False)
            return temp
        except:
            pdb.set_trace()
            
    def runAssociationAnalysis(self):
        video_crop = np.load(self.fm.localOldVideoCropFile)
        poly = Polygon(video_crop)
        
        t_obj=base(self.fm.localAllFishTracksFile)
        t_dt = t_obj.clean_sort()
        c_obj = base(self.fm.localAllLabeledClustersFile)
        c_dt=c_obj.clean_cluster()
        a_dt=self.find_identity(c_dt, t_dt)
        
        #d_dt=pd.read_csv(self.fm.localAllFishDetectionsFile)
        #s_dt=self.create_summary(poly, t_dt, d_dt)
        
        
        

        # 1. Summarize tracks (summarized.csv)
        # Write code to determine the sex of each track and whether it is a reflection 

        # 2. Associate track with cluster (associatedCluster.csv)
        # Write code to add track (done), sex (done), and reflection data to each cluster
	# Find accurate framerate using the frame of the last cluster and the total number of frames (test at 29 and 30) 
        
