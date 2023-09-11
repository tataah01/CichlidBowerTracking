import platform, sys, os, shutil, datetime, subprocess, pdb, time, sendgrid, psutil
from cichlid_bower_tracking.helper_modules.file_manager import FileManager as FM
from cichlid_bower_tracking.helper_modules.googleController import GoogleController as GC
import csv

'''
when started
open error_log.txt
determine if error required restart
if error required restart
    determine pi ID
    check google controller sheet for PI ID
        if status is awaiting command, set to running. Append comment - "edited controller sheet"
    append date/time of completion. Append "nothing to do" if comment not "edited controller sheet"
'''
class RestartMaster():
    def __init__(self):
        print('FM')
        self.fileManager = FM()
        print('Download local creds')
        self.fileManager.downloadData(self.fileManager.localCredentialDir)
        print('GC')
        self.googleController = GC(self.fileManager.localCredentialSpreadsheet)
        print('tank')
        self.tankID = self.googleController.tankID
        
       # is_restarted = self.open_logs # 1 true 0 false
        #print(is_restarted)
        is_restarted = True
        comment = 'Nothing to do'
        
        if is_restarted == True:
            print("in controller sheet")
            status = self._returnStatus()
            print(status)
            #print(projectID)
            #print(analysisID) 
            if status == 'AwaitingCommand':
                self.googleController.modifyPiGS('Command', 'Restart')
                comment = 'Edited controller sheet'
        
        print(comment)
        self.write_logs(comment)

    def open_logs(self):
        print('open logs')
        with open(self.fileManager.localPiErrorFile, 'r', encoding='UTF8') as f:
            f.seek(0,2)
            v = f.read(1)
            var = str(var)
            print("the read character is"+var)
        if var == 1:
            print('true')
            return True
        else:
            print('false')
            return False
        
    def write_logs(self,reason):
        print("writing logs")
        get_time = datetime.datetime.now()
        data = ","+str(get_time)+","+reason
        with open(self.fileManager.localPiErrorFile, 'a+', encoding='UTF8') as f:
             f.write(data)

            def write_logs(self,reason):
        print("writing logs")
        get_time = datetime.datetime.now()
        data = ","+str(get_time)+","+reason
        with open(self.fileManager.localPiErrorFile, 'a+', encoding='UTF8') as f:
             f.write(data)

        
    def _returnStatus(self): #this is a copy from cichlid_tracker. Could be better
        status = self.googleController.getPiGS(['Status'])
        return status

