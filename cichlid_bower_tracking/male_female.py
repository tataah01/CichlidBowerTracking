import cv2, os, pdb, sys, random, torch
from cichlid_bower_tracking.helper_modules.file_manager import FileManager as FM
from torch.utils.data import Dataset, DataLoader
import pandas as pd 

# This code ensures that modules can be found in their relative directories
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)

class MaleFemaleDataLoader(Dataset):
    def __init__(self, main_directory):
        self.main_directory = main_directory
        male_videos = os.listdir(main_directory + 'Male/')
        female_videos = os.listdir(main_directory + 'Female/')

        dt = pd.DataFrame(columns = ['video_location','video_index','label','datatype'])
        for m_video in male_videos:
            new_data = {'video_location':[], 'video_index': [], 'label':[],'datatype':[]}
            cap = cv2.VideoCapture(main_directory + 'Male/' + m_video)
            frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

            video_location = main_directory + 'Male/' + m_video
            for i in range(frames):
                new_data['video_location'].append(video_location)
                new_data['video_index'].append(i)
                new_data['label'].append('m')
                if random.randint(0,10) == 0:
                    new_data['datatype'].append('Validation')
                else:
                    new_data['datatype'].append('Train')
            dt = dt.append(pd.DataFrame(new_data))
        for f_video in female_videos:
            new_data = {'video_location':[], 'video_index': [], 'label':[],'datatype':[]}
            cap = cv2.VideoCapture(main_directory + 'Female/' + f_video)
            frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    
            video_location = main_directory + 'Female/' + f_video
            for i in range(frames):
                new_data['video_location'].append(video_location)
                new_data['video_index'].append(i)
                new_data['label'].append('f')
                if random.randint(0,10) == 0:
                    new_data['datatype'].append('Validation')
                else:
                    new_data['datatype'].append('Train')
            dt = dt.append(pd.DataFrame(new_data))

        self.dt = dt.sample(len(dt)).reset_index()[['label','video_index','video_location','datatype']]

    def choose_datatype(self,datatype):
        self.datatype = datatype
        self.sub_dt = self.dt[self.dt.datatype == datatype]

    def __len__(self):
        return len(self.sub_dt)

    def __getitem__(self, idx):

        frame_info = self.sub_dt.iloc[idx]
        cap = cv2.VideoCapture(frame_info.video_location)
        cap.set(cv2.CAP_PROP_POS_FRAMES, frame_info.video_index)
        ret, frame = cap.read()
        img_tensor = torch.from_numpy(frame)
        img_tensor = img_tensor.permute(2, 0, 1)

        if frame_info.label == 'm':
            class_id = torch.tensor([0])
        else:
            class_id = torch.tensor([1])
 
        return img_tensor, class_id

fm_obj = FM('PatrickTesting')

mf_obj = MaleFemaleDataLoader(fm_obj.localMaleFemalesVideosDir)
mf_obj.choose_datatype('Train')
mf_obj[0]
mf_obj[5]