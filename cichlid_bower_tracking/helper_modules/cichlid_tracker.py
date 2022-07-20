import platform, sys, os, shutil, datetime, subprocess, gspread, time, socket, pdb, time, requests
from cichlid_bower_tracking.helper_modules.file_manager import FileManager as FM
from cichlid_bower_tracking.helper_modules.log_parser import LogParser as LP
from cichlid_bower_tracking.helper_modules.googleController import GoogleController as GC
import pandas as pd
from picamera import PiCamera
import numpy as np

import warnings
warnings.filterwarnings('ignore')
from PIL import Image
import matplotlib.image

sys.path.append(sys.path[0] + '/unit_scripts')
sys.path.append(sys.path[0] + '/helper_modules')

class CichlidTracker:
    def __init__(self):

        # 1: Define valid commands and ignore warnings
        self.commands = ['New', 'Restart', 'Stop', 'Rewrite', 'UploadData', 'LocalDelete']
        np.seterr(invalid='ignore')

        # 2: Determine which depth sensor is attached (This script can handle DepthSense cameras)
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
        self.googleController = GC(self.fileManager.localCredentialSpreadsheet)
       
        # 6: Keep track of processes spawned to convert and upload videofiles
        self.processes = [] 

        # 7: Set size of frame
        try:
            self.r
        except AttributeError:
            self.r = (0,0,640,480)

        # 9: Await instructions
        print('Monitoring commands')
        self.monitorCommands()
        
    def __del__(self):
        # Try to close out files and stop running Kinects
        self.googleController.modifyPiGS('Command','None', ping = False)
        self.googleController.modifyPiGS('Status','Stopped', ping = False)
        self.googleController.modifyPiGS('Error','UnknownError', ping = False)

        if self.piCamera:
            if self.camera.recording:
                self.camera.stop_recording()
                self._print('PiCameraStopped: Time=' + str(datetime.datetime.now()) + ', File=Videos/' + str(self.videoCounter).zfill(4) + "_vid.h264")

        if self.device == 'realsense':
            self.pipeline.stop()

        self._closeFiles()

    def monitorCommands(self, delta = 20):
        # This function checks the master Controller Google Spreadsheet to determine if a command was issued (delta = seconds to recheck)
        self.googleController.modifyPiGS('Status', 'AwaitingCommand')
        self.googleController.modifyPiGS('Error', '', ping = False)

        while True:
            command, projectID, analysisID = self._returnCommand()
            if projectID in ['','None']:
                self._reinstructError('ProjectID must be set')
                time.sleep(delta)
                continue
            
            elif analysisID in ['','None']:
                self._reinstructError('AnalysisID must be set')
                time.sleep(delta)
                continue

            if command not in ['None',None]:
                print(command + '\t' + projectID + '\t' + analysisID)
                self.fileManager = FM(analysisID = analysisID, projectID = projectID)
                self.projectID = projectID
                self.analysisID = analysisID

                self.runCommand(command)

            time.sleep(delta)

    def runCommand(self, command):
        # This function is used to run a specific command found in the  master Controller Google Spreadsheet

        # Rename files to make code more readable 
        self.projectDirectory = self.fileManager.localProjectDir
        self.loggerFile = self.fileManager.localLogfile
        self.googleErrorFile = self.fileManager.localProjectDir + 'GoogleErrors.txt'
        self.frameDirectory = self.fileManager.localFrameDir
        self.videoDirectory = self.fileManager.localVideoDir
        self.backupDirectory = self.fileManager.localBackupDir

        if command not in self.commands:
            self._reinstructError(command + ' is not a valid command. Options are ' + str(self.commands))

        self.googleController.addProjectID(self.projectID, self.googleErrorFile)
            
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
                if self.device == 'realsense':
                    self.pipeline.stop()
            except Exception as e:
                self._print('ErrorStopping kinect')
                
            self._closeFiles()

            self.googleController.modifyPiGS('Command', 'None', ping = False)
            self.googleController.modifyPiGS('Status', 'AwaitingCommand', ping = False)
            return

        if command == 'UploadData':

            self.googleController.modifyPiGS('Command', 'None')
            self.googleController.uploadFiles()
            return
            
        if command == 'LocalDelete':
            if os.path.exists(self.projectDirectory):
                shutil.rmtree(self.projectDirectory)
            self.googleController.modifyPiGS('Command', 'None', ping = False)
            self.googleController.modifyPiGS('Status', 'AwaitingCommand', ping = False)
            return

        self.googleController.modifyPiGS('Command', 'None', ping = False)
        self.googleController.modifyPiGS('Status', 'Running', ping = False)
        self.googleController.modifyPiGS('Error', '', ping = False)


        if command == 'New':
            # Project Directory should not exist. If it does, report error
            if os.path.exists(self.projectDirectory):
                self._reinstructError('New command cannot be run if ouput directory already exists on the pi. Use Rewrite or Restart')
            if self.fileManager.checkFileExists(self.projectDirectory)
                self._reinstructError('New command cannot be run if ouput directory already exists on the cloud. Did you forget to rename the project? If not delete the data on Dropbox')

        if command == 'Rewrite':
            if os.path.exists(self.projectDirectory):
                shutil.rmtree(self.projectDirectory)
            if self.fileManager.checkFileExists(self.projectDirectory)
                self._reinstructError('Rewrite command cannot be run if ouput directory already exists on the cloud. Delete the data on Dropbox')
            
        if command in ['New','Rewrite']:
            self.masterStart = datetime.datetime.now()
            
            os.makedirs(self.projectDirectory)
            os.makedirs(self.frameDirectory)
            os.makedirs(self.videoDirectory)
            os.makedirs(self.backupDirectory)
            #self._createDropboxFolders()
            self.frameCounter = 1
            self.videoCounter = 1
            self.firstDepthCaptured = False

        if command == 'Restart':
            logObj = LP(self.loggerFile)
            self.masterStart = logObj.master_start
            self.frameCounter = logObj.lastFrameCounter + 1
            self.videoCounter = logObj.lastVideoCounter + 1
            if self.system != logObj.system or self.device != logObj.device:
                self._reinstructError('Restart error. LogData: ' + ','.join([str(x) for x in [logObj.system,logObj.device,logObj.camera]]) + ',, SystemData: ' + ','.join([str(x) for x in [self.system, self.device, self.camera]]))
                return
            if self.device != 'None':
                subprocess.Popen(['python3', 'unit_scripts/drive_updater.py', self.loggerFile])
                pass

        self.lf = open(self.loggerFile, 'a', buffering = 1) # line buffered
        self.googleController.modifyPiGS('MasterStart',str(self.masterStart), ping = False)

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
                    out = self._captureFrame(current_frame_time, keep_all_data = self.all_data)
                    if out is not None:
                        current_background_time += datetime.timedelta(seconds = 60 * background_delta)
                    subprocess.Popen(['python3', 'unit_scripts/drive_updater.py', self.loggerFile])
                else:
                    out = self._captureFrame(current_frame_time, stdev_threshold = stdev_threshold, keep_all_data = self.all_data)
            else:
                while datetime.datetime.now() < current_frame_time:
                    time.sleep(5)

            current_frame_time += datetime.timedelta(seconds = 60 * frame_delta)

            # Check google doc to determine if recording has changed.
            try:
                command, projectID = self._returnCommand()
            except KeyError:
                continue                
            if command != 'None' and command is not None:
                break
            else:
                self._modifyPiGS('Error', '')

    def _identifyDevice(self):

        try:
            global rs
            import pyrealsense2 as rs

            ctx = rs.context()
            if len(ctx.devices) == 0:
                self.device = 'None'
            elif len(ctx.devices) > 1:
                self._initError('Multiple RealSense devices attached. Unsure how to handle')
            else:
                self.device = 'realsense'
        except Exception:
            self.device = 'None'


    def _initError(self, message):
        self.googleController.modifyPiGS('Command', 'None')
        self.googleController.modifyPiGS('Status', 'Stopped', ping = False)
        self.googleController.modifyPiGS('Error', 'InitError: ' + message, ping = False)

        self._print('InitError: ' + message)
        raise TypeError
            
    def _reinstructError(self, message):
        self.googleController.modifyPiGS('Error', 'InstructError: ' + message, ping = False)
        self._print(message)

        # Update google doc to indicate error
        self.monitorCommands()
 
    def _print(self, text):
        #temperature = subprocess.run(['/opt/vc/bin/vcgencmd','measure_temp'], capture_output = True)
        try:
            print(str(text), file = self.lf, flush = True)
        except Exception as e:
            pass
        print(str(text), file = sys.stderr, flush = True)

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

        if self.device == 'realsense':
            frames = self.pipeline.wait_for_frames(1000)
            frames = self.align.process(frames)
            depth_frame = frames.get_depth_frame().as_depth_frame()

            #except RuntimeError:
            #    self._googlePrint('No frame received from Kinect. Restarting')
            #    self._start_kinect()
            #    depth_frame = self.pipeline.wait_for_frames(1000).get_depth_frame().as_depth_frame()

            data = np.asanyarray(depth_frame.data)*depth_frame.get_units()*100 # Convert to centimeters
            data[data==0] = np.nan # 0 indicates bad data from RealSense
            data[data>1] = np.nan # Anything further away than 1 m is a mistake
            return data[self.r[1]:self.r[1]+self.r[3], self.r[0]:self.r[0]+self.r[2]]

    def _returnCommand(self):

        command, projectID = self.googleController.getPiGS(['Command','ProjectID','AnalysisID'])
        return command, projectID

    def _video_recording(self, time = None):
        if time is None:
            time = datetime.datetime.now()
        if time.hour >= 8 and time.hour < 18:
            return True
        else:
            return False
            
    def _start_kinect(self):

        if self.device == 'realsense':
            # Create a context object. This object owns the handles to all connected realsense devices
            self.pipeline = rs.pipeline()
            self.align = rs.align(rs.stream.color)

            # Configure streams
            config = rs.config()
            config.enable_stream(rs.stream.depth, 640, 480, rs.format.z16, 30)
            config.enable_stream(rs.stream.color, 640, 480, rs.format.rgb8, 30)

            # Start streaming
            self.profile = self.pipeline.start(config)
            #device = self.profile.get_device()
            #depth_sensor = device.first_depth_sensor()
            #device.hardware_reset()

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

        self._print('FirstFrameCaptured: FirstFrame: Frames/FirstFrame.npy,,GoodDataCount: Frames/FirstDataCount.npy,,StdevCount: Frames/StdevCount.npy,,Units: cm')
    
    def _captureFrame(self, endtime, max_frames = 40, stdev_threshold = .05, count_threshold = 10, keep_all_data = False):
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
            
            counter += 1

            if current_time >= endtime:
                break
            time.sleep(10)
        
        if (endtime.minute > 0 and endtime.minute <= 5) or keep_all_data:
            self._print('AllDataCaptured: NpyFile: Frames/AllData_' + str(self.frameCounter).zfill(6) + '.npy,,PicFile: Frames/Frame_' + str(self.frameCounter).zfill(6) + '.jpg,,Time: ' + str(endtime)  + ',,NFrames: ' + str(i))
            np.save(self.projectDirectory +'Frames/AllData_' + str(self.frameCounter).zfill(6) + '.npy', all_data)

        bad_all_pixels = np.count_nonzero(np.isnan(all_data))
        good_all_pixels = np.count_nonzero(~np.isnan(all_data))

        med = np.nanmedian(all_data, axis = 0)
        std = np.nanstd(all_data, axis = 0)
        
        med[np.isnan(std)] = np.nan

        bad_std_avg_pixels = (std > stdev_threshold).sum()
        med[std > stdev_threshold] = np.nan
        std[std > stdev_threshold] = np.nan


        counts = np.count_nonzero(~np.isnan(all_data), axis = 0)

        bad_count_avg_pixels = (counts<count_threshold).sum()
        med[counts < count_threshold] = np.nan
        std[counts < count_threshold] = np.nan

        color = self._returnRegColor()                        
        
        outstring = 'FrameCaptured: NpyFile: Frames/Frame_' + str(self.frameCounter).zfill(6) + '.npy,,PicFile: Frames/Frame_' + str(self.frameCounter).zfill(6) + '.jpg,,'
        outstring += 'Time: ' + str(endtime)  + ',,NFrames: ' + str(i) + ',,AvgMed: '+ '%.2f' % np.nanmean(med) + ',,AvgStd: ' + '%.2f' % np.nanmean(std) + ',,'
        outstring += 'GP: ' + str(np.count_nonzero(~np.isnan(med))) + ',,AllPixelsBad: ' + str(bad_all_pixels) + ',,AllPixelsGood: ' + str(good_all_pixels) + ',,'
        outstring += 'FilteredStdPixels: ' + str(bad_std_avg_pixels) + ',,FilteredCountPixels: ' + str(bad_count_avg_pixels) + ',,LOF: ' + str(self._video_recording(time = endtime))
        
        self._print(outstring)
        np.save(self.projectDirectory +'Frames/Frame_' + str(self.frameCounter).zfill(6) + '.npy', med)
        matplotlib.image.imsave(self.projectDirectory+'Frames/Frame_' + str(self.frameCounter).zfill(6) + '.jpg', color)
        
        self.frameCounter += 1

        return med

            
    def _uploadFiles(self):
        self.googleController.modifyPiGS('Status', 'Finishing converting and uploading of videos')
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

        self.googleController.modifyPiGS('Status','Creating prep files')

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
            # Filter depth objects for those that are in the daytime
            depthObjs = [x for x in lp.frames if (x.time > videoObj.startTime and self._video_recording(time = x.time))]

            subprocess.call(['cp', self.projectDirectory + depthObjs[0].pic_file, prepDirectory + 'DepthRGB.jpg'])
            subprocess.call(['cp', self.projectDirectory + depthObjs[0].npy_file, prepDirectory + 'FirstDepth.npy'])
            subprocess.call(['cp', self.projectDirectory + depthObjs[-1].npy_file, prepDirectory + 'LastDepth.npy'])

            if not os.path.isdir(self.frameDirectory):
                self.googleController.modifyPiGS('Status', 'Error: ' + self.frameDirectory + ' does not exist.')
                return
        
        try:
            self.googleController.modifyPiGS('Status', 'Uploading data to cloud')
            if self.device != 'None':
                self.fileManager.uploadData(self.frameDirectory, tarred = True)
            #print(prepDirectory)
            self.fileManager.uploadData(prepDirectory)
            #print(self.videoDirectory)
            self.fileManager.uploadData(self.videoDirectory)
            #print(self.loggerFile)
            self.fileManager.uploadData(self.loggerFile)
            self.googleController.odifyPiGS('Error','UploadSuccessful, ready for delete')

        except Exception as e:
            print('UploadError: ' + str(e))
            self.googleController.modifyPiGS('Error','UploadFailed, Need to rerun')
            raise Exception
        
    def _closeFiles(self):
       try:
            self._print('MasterRecordStop: ' + str(datetime.datetime.now()))
            self.lf.close()
       except AttributeError:
           pass

