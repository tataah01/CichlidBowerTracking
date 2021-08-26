import platform, sys, os, shutil, datetime, subprocess, gspread, time, socket, pdb, time
from cichlid_bower_tracking.helper_modules.file_manager import FileManager as FM
from cichlid_bower_tracking.helper_modules.log_parser import LogParser as LP
import pandas as pd
from picamera import PiCamera
import numpy as np

import warnings
warnings.filterwarnings('ignore')


#with warnings.catch_warnings():
#    warnings.filterwarnings('ignore', message = 'Degrees of freedom <= 0 for slice.')
#    warnings.filterwarnings('ignore', message = 'Mean of empty slice')
    
from PIL import Image
# from oauth2client.service_account import ServiceAccountCredentials
import matplotlib.image

class CichlidTracker:
    def __init__(self):
        

        # 1: Define valid commands and ignore warnings
        self.commands = ['New', 'Restart', 'Stop', 'Rewrite', 'UploadData', 'LocalDelete', 'Snapshots']
        np.seterr(invalid='ignore')

        # 2: Determine which Kinect is attached (This script can handle v1 or v2 Kinects)
        self._identifyDevice() #Stored in self.device
        self.system = platform.node()

        # 3: Create file manager
        self.fileManager = FM()

        # 4: Start PiCamera
        self.camera = PiCamera()
        self.camera.resolution = (1296, 972)
        self.camera.framerate = 30
        self.piCamera = 'True'
        
        # 5: Download credential files
        self.fileManager.downloadData(self.fileManager.localCredentialDir)
        self.credentialSpreadsheet  = self.fileManager.localCredentialSpreadsheet # Rename to make code readable
        self._authenticateGoogleSpreadSheets() #Creates self.controllerGS
        self._identifyTank() #Stored in self.tankID
        self._identifyServiceAccount() 

        # 6: Connect to Google Spreadsheets
        self._modifyPiGS('Error', '')

        # 7: Keep track of processes spawned to convert and upload videofiles
        self.processes = [] 

        # 8: Set size of frame
        try:
            self.r
        except AttributeError:
            self.r = (0,0,640,480)

        # 9: Await instructions
        self.monitorCommands()
        
    def __del__(self):
        # Try to close out files and stop running Kinects
        self._modifyPiGS('Command','None')
        self._modifyPiGS('Status','Stopped')
        self._modifyPiGS('Error','UnknownError')

        if self.piCamera:
            if self.camera.recording:
                self.camera.stop_recording()
                self._print('PiCameraStopped: Time=' + str(datetime.datetime.now()) + ', File=Videos/' + str(self.videoCounter).zfill(4) + "_vid.h264")

        try:
            if self.device == 'kinect2':
                self.K2device.stop()
            if self.device == 'kinect':
                freenect.sync_stop()
                freenect.shutdown(self.a)
        except AttributeError:
            pass
        self._closeFiles()

    def monitorCommands(self, delta = 10):
        # This function checks the master Controller Google Spreadsheet to determine if a command was issued (delta = seconds to recheck)
        while True:
            command, projectID = self._returnCommand()
            if projectID in ['','None']:
                self._reinstructError('ProjectID must be set')
                time.sleep(delta)
                continue
            
            if command != 'None':
                print(command + '\t' + projectID)
                self.fileManager.createProjectData(projectID)    
                self.runCommand(command, projectID)

            self._modifyPiGS('Status', 'AwaitingCommand')
            time.sleep(delta)

    def runCommand(self, command, projectID):
        # This function is used to run a specific command found int he  master Controller Google Spreadsheet
        self.projectID = projectID

        # Rename files to make code more readable 
        self.projectDirectory = self.fileManager.localProjectDir
        self.loggerFile = self.fileManager.localLogfile
        self.googleErrorFile = self.fileManager.localProjectDir + 'GoogleErrors.txt'
        self.frameDirectory = self.fileManager.localFrameDir
        self.videoDirectory = self.fileManager.localVideoDir
        self.backupDirectory = self.fileManager.localBackupDir

        if command not in self.commands:
            self._reinstructError(command + ' is not a valid command. Options are ' + str(self.commands))
            
        if command == 'Stop':
            
            if self.piCamera:
                if self.camera.recording:
                    self.camera.stop_recording()
                    self._print('PiCameraStopped: Time: ' + str(datetime.datetime.now()) + ',,File: Videos/' + str(self.videoCounter).zfill(4) + "_vid.h264")
                    
                    command = ['python3', 'unit_scripts/process_video.py', self.videoDirectory + str(self.videoCounter).zfill(4) + '_vid.h264']
                    command += [str(self.camera.framerate[0]), self.projectID]
                    self._print(command)
                    self.processes.append(subprocess.Popen(command))

            try:
                if self.device == 'kinect2':
                    self.K2device.stop()
                if self.device == 'kinect':
                    freenect.sync_stop()
                    freenect.shutdown(self.a)
                if self.device == 'None':
                    pass
            except Exception as e:
                self._googlePrint(e)
                self._print('ErrorStopping kinect')
                
         

            self._closeFiles()

            self._modifyPiGS('Command', 'None')
            self._modifyPiGS('Status', 'AwaitingCommand')
            return

        if command == 'UploadData':

            self._modifyPiGS('Command', 'None')
            self._uploadFiles()
            return
            
        if command == 'LocalDelete':
            if os.path.exists(self.projectDirectory):
                shutil.rmtree(self.projectDirectory)
            self._modifyPiGS('Command', 'None')
            self._modifyPiGS('Status', 'AwaitingCommand')
            return

        self._modifyPiGS('Command', 'None')
        self._modifyPiGS('Status', 'Running')
        self._modifyPiGS('Error', '')
        

        if command == 'New':
            # Project Directory should not exist. If it does, report error
            if os.path.exists(self.projectDirectory):
                self._reinstructError('New command cannot be run if ouput directory already exists. Use Rewrite or Restart')

        if command == 'Rewrite':
            if os.path.exists(self.projectDirectory):
                shutil.rmtree(self.projectDirectory)
            os.makedirs(self.projectDirectory)
            
        if command in ['New','Rewrite']:
            self.masterStart = datetime.datetime.now()
            if command == 'New':
                os.makedirs(self.projectDirectory)
            os.makedirs(self.frameDirectory)
            os.makedirs(self.videoDirectory)
            os.makedirs(self.backupDirectory)
            #self._createDropboxFolders()
            self.frameCounter = 1
            self.videoCounter = 1

        if command == 'Restart':
            logObj = LP(self.loggerFile)
            self.masterStart = logObj.master_start
            #self.r = logObj.bounding_shape
            self.frameCounter = logObj.lastFrameCounter + 1
            self.videoCounter = logObj.lastVideoCounter + 1
            if self.system != logObj.system or self.device != logObj.device or self.piCamera != logObj.camera:
                self._reinstructError('Restart error. System, device, or camera does not match what is in logfile')
            if self.device != 'None':
                subprocess.Popen(['python3', 'unit_scripts/drive_updater.py', self.loggerFile])
                
        self.lf = open(self.loggerFile, 'a', buffering = 1) # line buffered
        self.g_lf = open(self.googleErrorFile, 'a', buffering = 1)
        self._modifyPiGS('MasterStart',str(self.masterStart))

        if command in ['New', 'Rewrite']:
            self._print('MasterStart: System: '+self.system + ',,Device: ' + self.device + ',,Camera: ' + str(self.piCamera) + ',,Uname: ' + str(platform.uname()) + ',,TankID: ' + self.tankID + ',,ProjectID: ' + self.projectID)
            self._print('MasterRecordInitialStart: Time: ' + str(self.masterStart))
            self._print('PrepFiles: FirstDepth: PrepFiles/FirstDepth.npy,,LastDepth: PrepFiles/LastDepth.npy,,PiCameraRGB: PiCameraRGB.jpg,,DepthRGB: DepthRGB.jpg')
            picamera_settings = {'AnalogGain': str(self.camera.analog_gain), 'AWB_Gains': str(self.camera.awb_gains), 
                                'AWB_Mode': str(self.camera.awb_mode), 'Brightness': str(self.camera.brightness), 
                                'ClockMode': str(self.camera.clock_mode), 'Contrast': str(self.camera.contrast),
                                'Crop': str(self.camera.crop),'DigitalGain': str(self.camera.digital_gain),
                                'ExposureCompensation': str(self.camera.exposure_compensation),'ExposureMode': str(self.camera.exposure_mode),
                                'ExposureSpeed': str(self.camera.exposure_speed),'FrameRate': str(self.camera.framerate),
                                'ImageDenoise': str(self.camera.image_denoise),'MeterMode': str(self.camera.meter_mode),
                                'RawFormat': str(self.camera.raw_format), 'Resolution': str(self.camera.resolution),
                                'Saturation': str(self.camera.saturation),'SensorMode': str(self.camera.sensor_mode),
                                'Sharpness': str(self.camera.sharpness),'ShutterSpeed': str(self.camera.shutter_speed),
                                'VideoDenoise': str(self.camera.video_denoise),'VideoStabilization': str(self.camera.video_stabilization)}
            self._print('PiCameraSettings: ' + ',,'.join([x + ': ' + picamera_settings[x] for x in sorted(picamera_settings.keys())]))
            #self._createROI(useROI = False)

        else:
            self._print('MasterRecordRestart: Time: ' + str(datetime.datetime.now()))

            
        # Start kinect
        if self.device != 'None':
            self._start_kinect()
            # Diagnose speed
            self._diagnose_speed()

        # Capture data
        self.captureFrames()
    
    def captureFrames(self, frame_delta = 5, background_delta = 5):

        current_background_time = datetime.datetime.now()
        current_frame_time = current_background_time + datetime.timedelta(seconds = 60 * frame_delta)

        command = ''
        
        while True:
            self._modifyPiGS('Command', 'None')
            self._modifyPiGS('Status', 'Running')
            self._modifyPiGS('Error', '')
 
            # Grab new time
            now = datetime.datetime.now()
            
            # Fix camera if it needs to be
            if self.piCamera:
                if self._video_recording() and not self.camera.recording:
                    self.camera.capture(self.videoDirectory + str(self.videoCounter).zfill(4) + "_pic.jpg")
                    self._print('PiCameraStarted: FrameRate: ' + str(self.camera.framerate) + ',,Resolution: ' + str(self.camera.resolution) + ',,Time: ' + str(datetime.datetime.now()) + ',,VideoFile: Videos/' + str(self.videoCounter).zfill(4) + '_vid.h264,,PicFile: Videos/' + str(self.videoCounter).zfill(4) + '_pic.jpg')
                    self.camera.start_recording(self.videoDirectory + str(self.videoCounter).zfill(4) + "_vid.h264", bitrate=7500000)
                elif not self._video_recording() and self.camera.recording:
                    self._print('PiCameraStopped: Time: ' + str(datetime.datetime.now()) + ',, File: Videos/' + str(self.videoCounter).zfill(4) + "_vid.h264")
                    self.camera.stop_recording()
                    #self._print(['rclone', 'copy', self.videoDirectory + str(self.videoCounter).zfill(4) + "_vid.h264"])
                    command = ['python3', 'unit_scripts/process_video.py', self.videoDirectory + str(self.videoCounter).zfill(4) + '_vid.h264']
                    command += [str(self.camera.framerate[0]), self.projectID]
                    self._print(command)
                    self.processes.append(subprocess.Popen(command))
                    self.videoCounter += 1

            # Capture a frame and background if necessary
            if self.device != 'None':
                if now > current_background_time:
                    if command == 'Snapshots':
                        out = self._captureFrame(current_frame_time, snapshots = True)
                    else:
                        out = self._captureFrame(current_frame_time)
                    if out is not None:
                        current_background_time += datetime.timedelta(seconds = 60 * background_delta)
                    #subprocess.Popen(['python3', 'unit_scripts/drive_updater.py', self.loggerFile])
                else:
                    if command == 'Snapshots':
                        out = self._captureFrame(current_frame_time, snapshots = True)
                    else:    
                        out = self._captureFrame(current_frame_time, stdev_threshold = stdev_threshold)
            current_frame_time += datetime.timedelta(seconds = 60 * frame_delta)

            self._modifyPiGS('Status', 'Running')
 
            
            # Check google doc to determine if recording has changed.
            try:
                command, projectID = self._returnCommand()
            except KeyError:
                continue                
            if command != 'None':
                if command == 'Snapshots':
                    self._modifyPiGS('Command', 'None')
                    self._modifyPiGS('Status', 'Writing Snapshots')
 
                    self._modifyPiGS(command = 'None', status = 'Writing Snapshots')
                    continue
                else:
                    break
            else:
                self._modifyPiGS('Error', '')
 
    def _authenticateGoogleSpreadSheets(self):
        # scope = [
        #     "https://spreadsheets.google.com/feeds",
        #     "https://www.googleapis.com/auth/spreadsheets"
        # ]
        # credentials = ServiceAccountCredentials.from_json_keyfile_name(self.credentialSpreadsheet, scope)
        
        # Get IP address
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        self.IP = s.getsockname()[0]
        s.close()

        for i in range(0,3): # Try to autheticate three times before failing
            try:
                # gs = gspread.authorize(credentials)
                gs = gspread.service_account(filename=self.credentialSpreadsheet)
            except Exception as e:
                self._googlePrint(e)
                continue
            try:
                self.controllerGS = gs.open('Controller')
                self.pi_ws = self.controllerGS.worksheet('RaspberryPi')
                data = self.pi_ws.get_all_values()
                dt = pd.DataFrame(data[1:], columns = data[0])
            except Exception as e:
                self._googlePrint(e)
                continue

            try:
                if len(dt.loc[dt.RaspberryPiID == platform.node()]) == 0:
                    self.pi_ws.append_row([platform.node(),self.ip,'','','','','','None','Stopped','Error: Awaiting assignment of TankID',str(datetime.datetime.now())])
                    return True
                else:
                    return True
            except Exception as e:
                self._googlePrint(e)
                continue    
            time.sleep(2)
        return False
            
    def _identifyDevice(self):
        try:
            global freenect
            import freenect
            self.a = freenect.init()
            if freenect.num_devices(self.a) == 0:
                kinect = False
            elif freenect.num_devices(self.a) > 1:
                self._initError('Multiple Kinect1s attached. Unsure how to handle')
            else:
                kinect = True
        except ImportError:
            kinect = False

        try:
            global rs
            import pyrealsense2 as rs

            ctx = rs.context()
            if len(ctx.devices) == 0:
                realsense = False
            elif len(ctx.devices) > 1:
                self._initError('Multiple RealSense devices attached. Unsure how to handle')
            else:
                realsense = True
        except ImportError:
            realsense = False

        if kinect and realsense:
            self._initError('Kinect1 and RealSense devices attached. Unsure how to handle')
        elif (not kinect) and (not realsense):
            self.device = 'None'
        elif kinect:
            self.device = 'kinect'
        else:
            self.device = 'realsense'
       
    def _identifyTank(self):
        while True:
            tankID = self._getPiGS('TankID')
            if tankID not in ['None','']:
                self.tankID = tankID
                
                self._modifyPiGS('Capability', 'Device=' + self.device + ',Camera=' + str(self.piCamera))
                self._modifyPiGS('Status', 'AwaitingCommand')
                break
            else:
                self._modifyPiGS('Error','Awaiting assignment of TankID')
                time.sleep(20)
    
    def _identifyServiceAccount(self):
        while True:
            serviceAccount = self._getPiGS('ServiceAccount')
            if serviceAccount not in ['None','']:
                self.serviceAccount = serviceAccount
                self.credentialSpreadsheet = self.credentialSpreadsheet.replace('_1.json', '_' + self.serviceAccount + '.json')
                self._authenticateGoogleSpreadSheets() #Creates self.controllerGS

                break
            else:
                self._modifyPiGS('Error','Awaiting assignment of ServiceAccount')
                time.sleep(20)

    def _initError(self, message):
        try:
            self._modifyPiGS('Command', 'None')
            self._modifyPiGS('Status', 'Stopped')
            self._modifyPiGS('Error', 'InitError: ' + message)

        except Exception as e:
            self._googlePrint(e)
            pass
        self._print('InitError: ' + message)
        raise TypeError
            
    def _reinstructError(self, message):
        try:
            self._modifyPiGS('Command', 'None')
            self._modifyPiGS('Status', 'AwaitingCommands')
            self._modifyPiGS('Error', 'InstructError: ' + message)
        except Exception as e:
            self._googlePrint(e)
            pass

        # Update google doc to indicate error
        self.monitorCommands()
 
    def _print(self, text):
        #temperature = subprocess.run(['/opt/vc/bin/vcgencmd','measure_temp'], capture_output = True)
        try:
            print(str(text), file = self.lf, flush = True)
        except Exception as e:
            pass
        print(str(text), file = sys.stderr, flush = True)

    def _googlePrint(self, e):
        try:
            print(str(datetime.datetime.now()) + ': ' + str(type(e)) + ': ' + str(e), file = self.g_lf, flush = True)
            time.sleep(20)
        except AttributeError as e2: # log file not created yet so just print to stderr
            print(str(datetime.datetime.now()) + ': ' + str(type(e)) + ': ' + str(e), flush = True)
            time.sleep(20)

    def _returnRegColor(self, crop = True):
        # This function returns a registered color array
        if self.device == 'kinect':
            out = freenect.sync_get_video()[0]
            
        if self.device == 'realsense':
            frames = self.pipeline.wait_for_frames(1000)
            color_frame = frames.get_color_frame()
            out = np.asanyarray(color_frame.get_data())

        if crop:
            return out[self.r[1]:self.r[1]+self.r[3], self.r[0]:self.r[0]+self.r[2]]
        else:
            return out
            
    def _returnDepth(self):
        # This function returns a float64 npy array containing one frame of data with all bad data as NaNs
        if self.device == 'kinect':
            data = freenect.sync_get_depth()[0].astype('float64')
            data[data == 2047] = np.nan # 2047 indicates bad data from Kinect 
            return data[self.r[1]:self.r[1]+self.r[3], self.r[0]:self.r[0]+self.r[2]]
        
        if self.device == 'realsense':
            depth_frame = self.pipeline.wait_for_frames(1000).get_depth_frame().as_depth_frame()
            data = np.asanyarray(depth_frame.data)*depth_frame.get_units() # Convert to meters
            data[data==0] = np.nan # 0 indicates bad data from RealSense
            data[data>1] = np.nan # Anything further away than 1 m is a mistake
            return data[self.r[1]:self.r[1]+self.r[3], self.r[0]:self.r[0]+self.r[2]]

    def _returnCommand(self):
        
        command, projectID = self._getPiGS(['Command','ProjectID'])
        return command, projectID


    def _getPiGS(self, column_names):
        # Make this compatible with both lists and also strings
        if not isinstance(column_names, list):
            column_name = [column_names]
        print('Read request: ' + str(datetime.datetime.now()))
        for i in range(3):
            try:
                data = self.pi_ws.get_all_values()
            except gspread.exceptions.APIError as e:
                if e.response.status_code == 429:
                # Read requests per minute exceeded
                    self._googlePrint('Read requests per minute exceeded')
                    continue
                elif e.response.status_code == 500:
                    self._googlePrint('Internal error encountered')
                    continue
                else:
                    self._googlePrint('gspread error of unknown nature: ' + str(e))
                    raise Exception

            dt = pd.DataFrame(data[1:], columns = data[0])
            self.dt = dt
            out_data = []
            for column_name in column_names:
                if column_name not in dt.columns:
                    self._googlePrint('Cant find column name in Controller: ' + column_name)
                    raise Exception
                try:
                    cell = dt.loc[(dt.RaspberryPiID == platform.node())&(dt.IP == self.IP),column_name]
                except AttributeError as error:
                    pdb.set_trace()
                if len(cell) > 1:
                    self._googlePrint('Multiple rows in the Controller with the same ID and IP')
                    raise Exception
                out_data.append(cell.values[0])

            if len(out_data == 1):
                return out_data[0]
            else:
                return out_data

    def _getRowColumn(self, column_name):
        column = self.dt.columns.get_loc(column_name)
        ping_column = self.dt.columns.get_loc('Ping')
        row = pd.Index((self.dt.RaspberryPiID == platform.node())&(self.dt.IP == self.IP)).get_loc(True)
        return (row + 2, column + 1, ping_column + 1) # 0 vs 1 indexing for pandas vs gspread + column names aren't in the pandas dataframe

    def _modifyPiGS(self, column_name, new_value):
        for i in range(3):
            try:
                row, column, ping_column = self._getRowColumn(column_name)
                
                self.pi_ws.update_cell(row, column, new_value)
                self.pi_ws.update_cell(row, ping_column, str(datetime.datetime.now()))
            except gspread.exceptions.APIError as e:
                if e.response.status_code == 429:
                    # Read requests per minute exceeded
                    self._googlePrint('Read requests per minute exceeded')
                    continue
                elif e.response.status_code == 500:
                    self._googlePrint('Internal error encountered')
                    continue
                else:
                    self._googlePrint('gspread error of unknown nature: ' + str(e))
                    raise Exception

    
    def _video_recording(self):
        if datetime.datetime.now().hour >= 8 and datetime.datetime.now().hour <= 18:
            return True
        else:
            return False
            
    def _start_kinect(self):
        if self.device == 'kinect':
            freenect.sync_get_depth() #Grabbing a frame initializes the device
            freenect.sync_get_video()

        elif self.device == 'realsense':
            # Create a context object. This object owns the handles to all connected realsense devices
            self.pipeline = rs.pipeline()

            # Configure streams
            config = rs.config()
            config.enable_stream(rs.stream.depth, rs.format.z16, 30)
            config.enable_stream(rs.stream.color, rs.format.rgb8, 30)

            # Start streaming
            self.pipeline.start(config)
        
            frames = self.pipeline.wait_for_frames(1000)
            depth = frames.get_depth_frame()
            self.r = (0,0,depth.width,depth.height)

    def _diagnose_speed(self, time = 10):
        print('Diagnosing speed for ' + str(time) + ' seconds.', file = sys.stderr)
        delta = datetime.timedelta(seconds = time)
        start_t = datetime.datetime.now()
        counter = 0
        while True:
            depth = self._returnDepth()
            counter += 1
            if datetime.datetime.now() - start_t > delta:
                break
        #Grab single snapshot of depth and save it
        depth = self._returnDepth()
        np.save(self.projectDirectory +'Frames/FirstFrame.npy', depth)

        #Grab a bunch of depth files to characterize the variability
        data = np.zeros(shape = (50, self.r[3], self.r[2]))
        for i in range(0, 50):
            data[i] = self._returnDepth()
            
        counts = np.count_nonzero(~np.isnan(data), axis = 0)
        std = np.nanstd(data, axis = 0)
        np.save(self.projectDirectory +'Frames/FirstDataCount.npy', counts)
        np.save(self.projectDirectory +'Frames/StdevCount.npy', std)
         
        self._print('DiagnoseSpeed: Rate: ' + str(counter/time))

        self._print('FirstFrameCaptured: FirstFrame: Frames/FirstFrame.npy,,GoodDataCount: Frames/FirstDataCount.npy,,StdevCount: Frames/StdevCount.npy')
    
    def _captureFrame(self, endtime, max_frames = 40, stdev_threshold = 20, snapshots = False):
        # Captures time averaged frame of depth data
        sums = np.zeros(shape = (self.r[3], self.r[2]))
        n = np.zeros(shape = (self.r[3], self.r[2]))
        stds = np.zeros(shape = (self.r[3], self.r[2]))
        
        current_time = datetime.datetime.now()
        if current_time >= endtime:
            self._print('Frame without data')
            return

        counter = 1

        all_data = np.empty(shape = (int(max_frames), self.r[3], self.r[2]))
        all_data[:] = np.nan
        
        for i in range(0, max_frames):
            all_data[i] = self._returnDepth()
            current_time = datetime.datetime.now()

            if snapshots:
                self._print('SnapshotCaptured: NpyFile: Frames/Snapshot_' + str(counter).zfill(6) + '.npy,,Time: ' + str(current_time)  + ',,GP: ' + str(np.count_nonzero(~np.isnan(all_data[i]))))
                np.save(self.projectDirectory +'Frames/Snapshot_' + str(counter).zfill(6) + '.npy', all_data[i])

            
            counter += 1

            if current_time >= endtime:
                break
            time.sleep(10)
        
        med = np.nanmean(all_data, axis = 0)
        
        std = np.nanstd(all_data, axis = 0)
        
        med[np.isnan(std)] = np.nan

        med[std > stdev_threshold] = np.nan
        std[std > stdev_threshold] = np.nan

        counts = np.count_nonzero(~np.isnan(all_data), axis = 0)

        med[counts < 3] = np.nan
        std[counts < 3] = np.nan

        color = self._returnRegColor()                        
        
        self._print('FrameCaptured: NpyFile: Frames/Frame_' + str(self.frameCounter).zfill(6) + '.npy,,PicFile: Frames/Frame_' + str(self.frameCounter).zfill(6) + '.jpg,,Time: ' + str(endtime)  + ',,NFrames: ' + str(i) + ',,AvgMed: '+ '%.2f' % np.nanmean(med) + ',,AvgStd: ' + '%.2f' % np.nanmean(std) + ',,GP: ' + str(np.count_nonzero(~np.isnan(med))))
        
        np.save(self.projectDirectory +'Frames/Frame_' + str(self.frameCounter).zfill(6) + '.npy', med)
        matplotlib.image.imsave(self.projectDirectory+'Frames/Frame_' + str(self.frameCounter).zfill(6) + '.jpg', color)
        
        self.frameCounter += 1

        return med

            
    def _uploadFiles(self):
        self._modifyPiGS('Status', 'Finishing converting and uploading of videos')
        for p in self.processes:
            p.communicate()
        
        for movieFile in os.listdir(self.videoDirectory):
            if '.h264' in movieFile:
                command = ['python3', 'unit_scripts/process_video.py', self.videoDirectory + movieFile]
                command += [str(self.camera.framerate[0]), self.projectID]
                self._print(command)
                self.processes.append(subprocess.Popen(command))

        for p in self.processes:
            p.communicate()

        self._modifyPiGS('Status','Creating prep files')

        # Move files around as appropriate
        prepDirectory = self.projectDirectory + 'PrepFiles/'
        shutil.rmtree(prepDirectory) if os.path.exists(prepDirectory) else None
        os.makedirs(prepDirectory)

        lp = LP(self.loggerFile)

        self.frameCounter = lp.lastFrameCounter + 1

        videoObj = [x for x in lp.movies if x.startTime.hour >= 8 and x.startTime.hour <= 20][0]
        subprocess.call(['cp', self.projectDirectory + videoObj.pic_file, prepDirectory + 'PiCameraRGB.jpg'])

        subprocess.call(['cp', self.projectDirectory + lp.movies[-1].pic_file, prepDirectory + 'LastPiCameraRGB.jpg'])

        # Find depthfile that is closest to the video file time
        if self.device != 'None':
            depthObj = [x for x in lp.frames if x.time > videoObj.startTime][0]


            subprocess.call(['cp', self.projectDirectory + depthObj.pic_file, prepDirectory + 'DepthRGB.jpg'])

            if not os.path.isdir(self.frameDirectory):
                self._modifyPiGS('Status', 'Error: ' + self.frameDirectory + ' does not exist.')
                return

            subprocess.call(['cp', self.frameDirectory + 'Frame_000001.npy', prepDirectory + 'FirstDepth.npy'])
            subprocess.call(['cp', self.frameDirectory + 'Frame_' + str(self.frameCounter-1).zfill(6) + '.npy', prepDirectory + 'LastDepth.npy'])
        
        try:
            self._modifyPiGS('Status', 'Uploading data to cloud')
            if self.device != 'None':
                self.fileManager.uploadData(self.frameDirectory, tarred = True)
            #print(prepDirectory)
            self.fileManager.uploadData(prepDirectory)
            #print(self.videoDirectory)
            self.fileManager.uploadData(self.videoDirectory)
            #print(self.loggerFile)
            self.fileManager.uploadData(self.loggerFile)
            self._modifyPiGS('Error','UploadSuccessful, ready for delete')

        except Exception as e:
            print('UploadError: ' + str(e))
            self._modifyPiGS('Error','UploadFailed, Need to rerun')
            raise Exception
        
    def _closeFiles(self):
       try:
            self._print('MasterRecordStop: ' + str(datetime.datetime.now()))
            self.lf.close()
       except AttributeError:
           pass
       try:
           if self.system == 'mac':
               self.caff.kill()
       except AttributeError:
           pass

