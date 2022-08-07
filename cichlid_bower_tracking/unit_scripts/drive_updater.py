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

        f = self._uploadImage(self.projectDirectory + self.lp.tankID + '.jpg', self.lp.tankID)

    def _createImage(self):
        lastHourFrames = [x for x in self.lp.frames if x.time > self.lastFrameTime - datetime.timedelta(hours = 1)]  
        lastDayFrames = [x for x in self.lp.frames if x.time > self.lastFrameTime - datetime.timedelta(days = 1)]
        daylightFrames = [x for x in self.lp.frames if x.time.hour >= 8 and x.time.hour <= 18]
        if len(daylightFrames) != 0:
            t_change = str(self.lastFrameTime - daylightFrames[0].time)
        else:
            daylightFrames = lastDayFrames
            t_change = str(self.lastFrameTime - lastDayFrames[0].time)
        d_change = str(self.lastFrameTime - lastDayFrames[0].time)
        h_change = str(self.lastFrameTime - lastHourFrames[0].time)
        
        fig = plt.figure(figsize=(10,13))
        fig.suptitle(self.lastFrameTime)
        ax1 = fig.add_subplot(4, 3, 1) #Pic from Kinect
        ax2 = fig.add_subplot(4, 3, 2) #Pic from Camera
        ax3 = fig.add_subplot(4, 3, 3) #Depth from Kinect
        ax4 = fig.add_subplot(4, 3, 4) #Total Depth Change
        ax5 = fig.add_subplot(4, 3, 5) #Day Depth Change
        ax6 = fig.add_subplot(4, 3, 6) #Hour Depth Change
        ax7 = fig.add_subplot(4, 3, 7) #Total Depth Change 
        ax8 = fig.add_subplot(4, 3, 8) #Day Depth Change
        ax9 = fig.add_subplot(4, 3, 9) #Hour Depth Change
        ax10 = fig.add_subplot(4, 3, 10) #Total Depth Change 
        ax11 = fig.add_subplot(4, 3, 11) #Day Depth Change
        ax12 = fig.add_subplot(4, 3, 12) #Hour Depth Change

        img_1 = img.imread(self.projectDirectory + self.lp.frames[-1].pic_file)
        try:
            img_2 = img.imread(self.projectDirectory + self.lp.movies[-1].pic_file)
        except:
            img_2 = img_1

        with warnings.catch_warnings():
            warnings.filterwarnings("ignore", message="All-NaN slice encountered")
            dpth_3 = np.load(self.projectDirectory + self.lp.frames[-1].npy_file)
            dpth_4 = np.load(self.projectDirectory + daylightFrames[0].npy_file)
            dpth_5 = np.load(self.projectDirectory + lastDayFrames[0].npy_file)
            dpth_6 = np.load(self.projectDirectory + lastHourFrames[0].npy_file)

        median_height = np.nanmedian(dpth_3)
        dpth_3[(dpth_3 > median_height + 8) | (dpth_3 < median_height - 8)] = np.nan # Filter out data 4cm lower and 8cm higher than tray
        dpth_4[(dpth_4 > median_height + 8) | (dpth_4 < median_height - 8)] = np.nan # Filter out data 4cm lower and 8cm higher than tray
        dpth_5[(dpth_5 > median_height + 8) | (dpth_5 < median_height - 8)] = np.nan # Filter out data 4cm lower and 8cm higher than tray
        dpth_6[(dpth_6 > median_height + 8) | (dpth_6 < median_height - 8)] = np.nan # Filter out data 4cm lower and 8cm higher than tray


        total_change = dpth_4 - dpth_3
        daily_change = dpth_5 - dpth_3
        hourly_change = dpth_6 - dpth_3


        ### TITLES ###
        ax1.set_title('Kinect RGB Picture')
        ax2.set_title('PiCamera RGB Picture')
        ax3.set_title('Current Kinect Depth')
        ax4.set_title('Total Change\n'+t_change)
        ax5.set_title('Last 24 hours change\n'+d_change)
        ax6.set_title('Last 1 hour change\n'+h_change)
        ax7.set_title('Total Bower\n'+t_change)
        ax8.set_title('Last 24 hours bower\n'+d_change)
        ax9.set_title('Last 1 hour bower\n'+h_change)
        ax10.set_title('Hour ago Depth')
        ax11.set_title('24 hour ago Depth')
        ax12.set_title('First daylight Depth')

        ax1.imshow(img_1)
        ax2.imshow(img_2)
        ax3.imshow(dpth_3, vmin = median_height - 8, vmax = median_height + 8)
        ax4.imshow(total_change, vmin = -2, vmax = 2) # +- 2 cms
        ax5.imshow(daily_change, vmin = -1.5, vmax = 1.5)
        ax6.imshow(hourly_change, vmin = -1, vmax = 1) # +- 1 cms
        total_bower = total_change.copy()
        total_bower[(total_change < 0.75) & (total_change > -0.75)] = 0
        daily_bower = daily_change.copy()
        daily_bower[(daily_change < 0.5) & (daily_change > -0.5)] = 0
        hourly_bower = hourly_change.copy()
        hourly_bower[(hourly_change < 0.5) & (hourly_change > -0.5)] = 0
        
        ax7.imshow(total_bower, vmin = -2, vmax = 2) # +- 2 cms
        ax8.imshow(daily_bower, vmin = -1.5, vmax = 1.5)
        ax9.imshow(hourly_bower, vmin = -1, vmax = 1) # +- 1 cms
        
        ax10.imshow(dpth_4, vmin = median_height - 8, vmax = median_height + 8)
        ax11.imshow(dpth_5, vmin = median_height - 8, vmax = median_height + 8)
        ax12.imshow(dpth_6, vmin = median_height - 8, vmax = median_height + 8)


        #plt.subplots_adjust(bottom = 0.15, left = 0.12, wspace = 0.24, hspace = 0.57)
        plt.savefig(self.projectDirectory + self.lp.tankID + '.jpg')
        #return self.graph_summary_fname

    def _uploadImage(self, image_file, name): #name should have format 't###_icon' or 't###_link'
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
        flag = False
        count = 0
        while flag == False and count < len(file_list):
            if file_list[count]['title'] == name:
                fileID = file_list[count]['id']
                flag = True
            else:
                count += 1

        if flag == True:
            # Replace the file if name exists
            f = drive.CreateFile({'id': fileID})
            f.SetContentFile(image_file)
            f.Upload()
            # print("Replaced", name, "with newest version")
        else:
            # Upload the image normally if name does not exist
            f = drive.CreateFile({'title': name, 'mimeType':'image/jpeg',
                                 "parents": [{"kind": "drive#fileLink", "id": folder_id[1:-1]}]})
            f.SetContentFile(image_file)
            f.Upload()                   
            # print("Uploaded", name, "as new file")
        
        info = '=HYPERLINK("' + f['alternateLink'] + '", IMAGE("' + f['webContentLink'] + '"))'
        self.googleController.modifyPiGS('Image', info, ping = False)
        return f
    
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
