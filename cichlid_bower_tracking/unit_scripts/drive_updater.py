import argparse, datetime, gspread, time, pdb, warnings
from cichlid_bower_tracking.helper_modules.file_manager import FileManager as FM
from cichlid_bower_tracking.helper_modules.log_parser import LogParser as LP
from cichlid_bower_tracking.helper_modules.googleController import GoogleController as GC

import matplotlib
matplotlib.use('Pdf')  # Enables creation of pdf without needing to worry about X11 forwarding when ssh'ing into the Pi
import matplotlib.pyplot as plt
import matplotlib.image as img
import numpy as np
from pydrive.auth import GoogleAuth
from pydrive.drive import GoogleDrive
from oauth2client.service_account import ServiceAccountCredentials
import oauth2client
from skimage import morphology
import pdb

parser = argparse.ArgumentParser()
parser.add_argument('Logfile', type = str, help = 'Name of logfile')
args = parser.parse_args()


class DriveUpdater:
    def __init__(self, logfile):
        self.lp = LP(logfile)

        self.fileManager = FM(projectID = self.lp.projectID, analysisID = self.lp.analysisID)
        self.node = self.lp.uname.split("node='")[1].split("'")[0]
        self.lastFrameTime = self.lp.frames[-1].time
        self.masterDirectory = self.fileManager.localMasterDir
        self.projectDirectory = self.fileManager.localProjectDir
        
        self.googleController = GC(self.fileManager.localCredentialSpreadsheet)
        self.googleController.addProjectID(self.lp.projectID, self.fileManager.localProjectDir + 'GoogleErrors.txt')

        self._createImage()

        self.credentialDrive = self.fileManager.localCredentialDrive

        self._uploadImage(self.projectDirectory + self.lp.tankID + '.jpg', self.projectDirectory + self.lp.tankID + '_2.jpg', self.lp.tankID, self.lp.tankID + '_2.jpg')

    def _createImage(self, stdcutoff = 0.1):
        lastHourFrames = [x for x in self.lp.frames if x.time > self.lastFrameTime - datetime.timedelta(hours = 1)] # frames from the last hour
        lastTwoHourFrames = [x for x in self.lp.frames if x.time > self.lastFrameTime - datetime.timedelta(hours = 2)] # frames from the last two hours
        daylightFrames = [x for x in self.lp.frames if x.time.hour >= 8 and x.time.hour <= 18] # frames during daylight
        th_change = str(self.lastFrameTime-lastTwoHourFrames[0].time)
        h_change = str(self.lastFrameTime - lastHourFrames[0].time)
        #
        # Dictionary to hold all the unique days that have daylight frames
        days={}        
        [days.update({x.time.day:1}) for x in daylightFrames] # This way we only identify days that have frames during the daylight

        
        # Determine the size of the figure and create it
        num_rows = 3 + len(days) # First pic rows, 1 hour, 2 hour, then 1 row for each unique day
        axes = [] # Hold axes in lis
        
        fig = plt.figure(figsize=(14,4*num_rows + 1))
        fig.suptitle(self.lp.projectID + ' ' + str(self.lastFrameTime))
        
        # Create subplots
        for i in range(num_rows):
            axes[3*i + 0] = fig.add_subplot(num_rows, 3, 3*i + 0) # Filtered Absolute Depth
            axes[3*i + 1] = fig.add_subplot(num_rows, 3, 3*i + 1) # Relative Depth Change
            axes[3*i + 2] = fig.add_subplot(num_rows, 3, 3*i + 2) # Bower changes
        ### TITLES ###
        axes[0].set_title('Kinect RGB Picture')
        axes[1].set_title('PiCamera RGB Picture')
        axes[2].set_title('Total Depth Change' + t_change)
        axes[3].set_title('Filtered Hour ago Depth')
        axes[4].set_title('Last hour change\n'+h_change)
        axes[5].set_title('Last hour bower\n')
        axes[6].set_title('Filtered 2 Hour ago Depth')
        axes[7].set_title('Last 2 hours change\n'+th_change)
        axes[8].set_title('Last 2 hours bower\n')
        
        for i in range(3, len(num_rows)):
            day_num=str(i-3)
            axes[3*i].set_title('Raw Day'+day_num+' Depth')
            axes[3*i+1].set_title(day_num+' Day change\n')
            axes[3*i+2].set_title(day_num+' bower\n')
        
        
        # Identify bad pixels
        std_template = np.load(self.projectDirectory + daylightFrames[0].std_file)
        stds = np.zeros(shape = (min(len(days), 10), std_template.shape[0], std_template.shape[1]), dtype = std_template.dtype())
        # Read in std deviation data to determine threshold
        #moved
        dpth_dif = np.load(self.projectDirectory + self.lp.frames[-1].npy_file)
        median_height = np.nanmedian(dpth_3)
        
        for i,day in enumerate(days.keys()):
            daylightFrames_day = [x for x in daylightFrames if x.time.day == day] # frames during daylight
            #stds[i] = np.load(self.projectDirectory + daylightFrames_day[0].std_file)
            dpth_day = np.load(self.projectDirectory + daylightFrames_day[0].npy_file)
            axes[3*i+9].imshow(dpth_day.copy(), vmin = median_height - 8, vmax = median_height + 8)
            daily_change = dpth_day - dpth_dif
            axes[3*i+10].imshow(daily_change.copy(), vmin = -1, vmax = 1)
            daily_bower = daily_change.copy()
            thresholded_change = np.where((daily_change >= 0.4) | (daily_change <= -0.4), True, False)
            thresholded_change = morphology.remove_small_objects(thresholded_change,1000).astype(int)
            daily_bower[(thresholded_change == 0) & (~np.isnan(daily_change))] = 0
            axes[3*i+11].imshow(daily_bower.copy(), vmin = -1, vmax = 1)
            dpth_dif=dpth_day.copy()

        #stds = (stds > stdcutoff).astype(int)
        #stds = np.sum(stds, axis = 0)

        # Read data for row 1,2,3 and plot it
        img_1 = img.imread(self.projectDirectory + self.lp.frames[-1].pic_file)
        try:
            img_2 = img.imread(self.projectDirectory + self.lp.movies[-1].pic_file)
        except:
            img_2 = img_1
        
        depth_last = np.load(self.projectDirectory + self.lp.frames[-1].npy_file)
        depth_first = np.load(self.projectDirectory + daylightFrames[0].npy_file)
        depth_hour = np.load(self.projectDirectory + lastHourFrames[0].npy_file)
        dpth_twohours = np.load(self.projectDirectory + lastTwoHourFrames[0].npy_file)


        dpth_3 = np.load(self.projectDirectory + self.lp.frames[-1].npy_file)
        dpth_4 = np.load(self.projectDirectory + daylightFrames[0].npy_file)
        #dpth_5 = np.load(self.projectDirectory + lastDayFrames[0].npy_file)
        dpth_6 = np.load(self.projectDirectory + lastTwoHourFrames[0].npy_file)
        dpth_7 = np.load(self.projectDirectory + lastHourFrames[0].npy_file)

        
        #not showing standard deviation anymore
        std_3 = np.load(self.projectDirectory + self.lp.frames[-1].std_file)
        std_4 = np.load(self.projectDirectory + daylightFrames[0].std_file)
        #std_5 = np.load(self.projectDirectory + lastDayFrames[0].std_file)
        std_6 = np.load(self.projectDirectory + lastTwoHourFrames[0].std_file)
        std_7 = np.load(self.projectDirectory + lastHourFrames[0].std_file)
        # Plot before filtering
        #removed non-filtered plots
        #ax10.imshow(dpth_5, vmin = median_height - 8, vmax = median_height + 8)
        #ax11.imshow(dpth_6, vmin = median_height - 8, vmax = median_height + 8)
        #ax12.imshow(dpth_7, vmin = median_height - 8, vmax = median_height + 8)

        # Filter out data thaat has a bad stdev
        #this part may need to be adjusted for 48-72 change
        bad_data_count = (std_3 > stdcutoff).astype(int) + (std_4 > stdcutoff).astype(int) + (std_6 > stdcutoff).astype(int) + (std_7 > stdcutoff).astype(int)
        dpth_3[bad_data_count > 3] = np.nan
        dpth_4[bad_data_count > 3] = np.nan
        #dpth_5[bad_data_count > 3] = np.nan
        dpth_6[bad_data_count > 3] = np.nan
        dpth_7[bad_data_count > 3] = np.nan
        

        # Filter out data that has bad initial height
        dpth_3[(dpth_4 > median_height + 4) | (dpth_4 < median_height - 4)] = np.nan # Filter out data 4cm lower and 8cm higher than tray
        #dpth_5[(dpth_4 > median_height + 4) | (dpth_4 < median_height - 4)] = np.nan # Filter out data 4cm lower and 8cm higher than tray
        dpth_6[(dpth_4 > median_height + 4) | (dpth_4 < median_height - 4)] = np.nan # Filter out data 4cm lower and 8cm higher than tray
        dpth_7[(dpth_4 > median_height + 4) | (dpth_4 < median_height - 4)] = np.nan # Filter out data 4cm lower and 8cm higher than tray
        dpth_4[(dpth_4 > median_height + 4) | (dpth_4 < median_height - 4)] = np.nan # Filter out data 4cm lower and 8cm higher than tray
        


        total_change = dpth_4 - dpth_3
        #daily_change = dpth_5 - dpth_3
        two_hourly_change = dpth_6 - dpth_3
        hourly_change = dpth_7 - dpth_3

        axes[0].imshow(img_1)
        axes[1].imshow(img_2)
        axes[2].imshow(total_change, vmin = -2, vmax = 2)
        #ax11.imshow(daily_change, vmin = -1, vmax = 1) # +- 2 cms
        axes[7].imshow(two_hourly_change, vmin = -.5, vmax = .5)
        axes[4].imshow(hourly_change, vmin = -.5, vmax = .5)


        #daily_bower = daily_change.copy()
        #thresholded_change = np.where((daily_change >= 0.4) | (daily_change <= -0.4), True, False)
        #thresholded_change = morphology.remove_small_objects(thresholded_change,1000).astype(int)
        #daily_bower[(thresholded_change == 0) & (~np.isnan(daily_change))] = 0

        two_hourly_bower = two_hourly_change.copy()
        thresholded_change = np.where((two_hourly_change >= 0.3) | (two_hourly_change <= -0.3), True, False)
        thresholded_change = morphology.remove_small_objects(thresholded_change,1000).astype(int)
        two_hourly_bower[(thresholded_change == 0) & (~np.isnan(two_hourly_change))] = 0

        hourly_bower = hourly_change.copy()
        thresholded_change = np.where((hourly_change >= 0.3) | (hourly_change <= -0.3), True, False)
        thresholded_change = morphology.remove_small_objects(thresholded_change,1000).astype(int)
        hourly_bower[(thresholded_change == 0) & (~np.isnan(daily_change))] = 0
        


        #ax12.imshow(daily_bower, vmin = -1, vmax = 1) # +- 2 cms
        axes[8].imshow(two_hourly_bower, vmin = -.5, vmax = .5)
        axes[5].imshow(hourly_bower, vmin = -.5, vmax = .5) # +- 1 cms
        #ax10.imshow(dpth_5, vmin = median_height - 8, vmax = median_height + 8)
        axes[6].imshow(dpth_6, vmin = median_height - 8, vmax = median_height + 8)
        axes[3].imshow(dpth_7, vmin = median_height - 8, vmax = median_height + 8)

        #ax16.imshow(std_5, vmin = 0, vmax = .25)
        #ax17.imshow(std_6, vmin = 0, vmax = .25)
        #ax18.imshow(std_7, vmin = 0, vmax = .25)

        #plt.subplots_adjust(bottom = 0.15, left = 0.12, wspace = 0.24, hspace = 0.57)
        plt.savefig(self.projectDirectory + self.lp.tankID + '.jpg')
        #return self.graph_summary_fname

        fig = plt.figure(figsize=(6,3))
        fig.tight_layout()
        ax1 = fig.add_subplot(1, 2, 1) #Pic from Kinect
        ax2 = fig.add_subplot(1, 2, 2) #Pic from Camera
        ax1.imshow(two_hourly_change, vmin = -.75, vmax = .75)
        ax1.axes.get_xaxis().set_visible(False)
        ax1.axes.get_yaxis().set_visible(False)

        ax2.imshow(hourly_change, vmin = -.75, vmax = .75) # +- 1 cms
        ax2.axes.get_xaxis().set_visible(False)
        ax2.axes.get_yaxis().set_visible(False)

        fig.tight_layout()

        fig.savefig(self.projectDirectory + self.lp.tankID + '_2.jpg')


    def _uploadImage(self, image_file1, image_file2, name1, name2): #name should have format 't###_icon' or 't###_link'
        self._authenticateGoogleDrive()
        drive = GoogleDrive(self.gauth)
        folder_id = "'151cke-0p-Kx-QjJbU45huK31YfiUs6po'"  #'Public Images' folder ID
        
        try:
            file_list = drive.ListFile({'q':"{} in parents and trashed=false".format(folder_id)}).GetList()
        except oauth2client.clientsecrets.InvalidClientSecretsError:
            self._authenticateGoogleDrive()
            file_list = drive.ListFile({'q':"{} in parents and trashed=false".format(folder_id)}).GetList()
        #print(file_list)
        # check if file name already exists so we can replace it
        flag1 = False
        flag2 = False
        count = 0
        while flag1 == False and count < len(file_list):
            if file_list[count]['title'] == name1:
                fileID1 = file_list[count]['id']
                flag1 = True
            else:
                count += 1
        count = 0
        while flag2 == False and count < len(file_list):
            if file_list[count]['title'] == name2:
                fileID2 = file_list[count]['id']
                flag2 = True
            else:
                count += 1

        if flag1 == True:
            # Replace the file if name exists
            f1 = drive.CreateFile({'id': fileID1})
            f1.SetContentFile(image_file1)
            f1.Upload()
            # print("Replaced", name, "with newest version")
        else:
            # Upload the image normally if name does not exist
            f1 = drive.CreateFile({'title': name1, 'mimeType':'image/jpeg',
                                 "parents": [{"kind": "drive#fileLink", "id": folder_id[1:-1]}]})
            f1.SetContentFile(image_file1)
            f1.Upload()                   
            # print("Uploaded", name, "as new file")

        if flag2 == True:
            # Replace the file if name exists
            f2 = drive.CreateFile({'id': fileID2})
            f2.SetContentFile(image_file2)
            f2.Upload()
            # print("Replaced", name, "with newest version")
        else:
            # Upload the image normally if name does not exist
            f2 = drive.CreateFile({'title': name2, 'mimeType':'image/jpeg',
                                 "parents": [{"kind": "drive#fileLink", "id": folder_id[1:-1]}]})
            f2.SetContentFile(image_file2)
            f2.Upload()                   
            # print("Uploaded", name, "as new file")


        info = '=HYPERLINK("' + f1['webContentLink'].replace('&export=download', '') + '", IMAGE("' + f2['webContentLink'] + '"))'

        #info = '=HYPERLINK("' + f['alternateLink'] + '", IMAGE("' + f['webContentLink'] + '"))'
        self.googleController.modifyPiGS('Image', info, ping = False)
    
    def _authenticateGoogleDrive(self):
        self.gauth = GoogleAuth()
        # Try to load saved client credentials
        self.gauth.LoadCredentialsFile(self.credentialDrive)
        if self.gauth.credentials is None:
            # Authenticate if they're not there
            self.gauth.LocalWebserverAuth()
        elif self.gauth.access_token_expired:
            # Refresh them if token is expired
            self.gauth.Refresh()
        else:
            # Initialize with the saved creds
            self.gauth.Authorize()
        # Save the current credentials to a file
        self.gauth.SaveCredentialsFile(self.credentialDrive)

dr_obj = DriveUpdater(args.Logfile)
#try:
#    dr_obj = DriveUpdater(args.Logfile)
#except Exception as e:
#    print(f'skipping drive update due to error: {e}')
