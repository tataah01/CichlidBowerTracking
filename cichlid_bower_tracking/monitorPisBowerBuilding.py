import pdb, datetime
import pandas as pd
from cichlid_bower_tracking.helper_modules.googleController import GoogleController as GC
from cichlid_bower_tracking.helper_modules.file_manager import FileManager as FM

fm_obj = FM()
fm_obj.createPiData() # Function that creates annotation files.
fm_obj.downloadData(fm_obj.localCredentialDir)

gc_obj = GC(fm_obj.localCredentialSpreadsheet, nonPiFlag = True)
dt = pd.DataFrame(gc_obj.all_data[1:], columns = gc_obj.all_data[0])
dt['LastPing'] = datetime.datetime.now() - pd.to_datetime(dt['Ping']).dt.to_pydatetime()
b_pis = dt[(dt['LastPing'] > datetime.timedelta(minutes = 15)) & (dt.Status == 'Running') & (dt.User == 'Bree')]

pdb.set_trace()