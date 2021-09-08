from matplotlib import (cm, colors, gridspec, ticker)
import matplotlib.pyplot as plt
from mpl_toolkits.axes_grid1.inset_locator import inset_axes
import pandas as pd
import numpy as np
import seaborn as sns
import datetime
import os
import subprocess
from types import SimpleNamespace
import sys
from sklearn.neighbors import KernelDensity
from skimage import morphology
from math import sqrt
import glob
import re
from cichlid_bower_tracking.helper_modules.file_manager import FileManager as FM
import pickle
import pdb
import PyPDF2 as pypdf

class SummaryPreparer:

    def __init__(self, FileManager, ca=None, da=None):
        self.__version__ = '1.0.0'
        self.fm = FileManager
        self.projectID = self.fm.projectID
        self.da_obj = da
        self.ca_obj = ca
        self.euth_data = None
        self.lp = None
        self.pid = None
        self.validateDepthData()
        self.validateClusterData()
        self.validateSinglenucData()

    def validateDepthData(self):
        # Determine whether or not the required data for depth figures in present, and initiate a DepthAnalyzer
        # object if it is. Otherwise, return False
        if self.da_obj is not None:
            return
        # List out required files
        reqs = [self.fm.localLogfile,
                self.fm.localSummaryDir,
                self.fm.localSmoothDepthFile,
                self.fm.localTrayFile]

        # Check that each required file is present. If any file is missing, return False
        for path in reqs:
            if not os.path.exists(path):
                return False

        # If all required files were present, initiate the LogParser and DepthAnalyzer
        self.lp = self.fm.lp
        self.da_obj = DepthAnalyzer(self.fm)

    def validateClusterData(self):
        # Determine whether or not the required data for cluster figures in present, and initiate a ClusterAnalyzer
        # object if it is. Otherwise, return False
        if self.ca_obj is not None:
            return

        # List out required files
        reqs = [self.fm.localLogfile,
                self.fm.localSummaryDir,
                self.fm.localAllLabeledClustersFile,
                self.fm.localTransMFile]

        # Check that each required file is present. If any file is missing, return False
        for path in reqs:
            if not os.path.exists(path):
                return False

        # If all required files were present, initiate the LogParser and ClusterAnalyzer
        self.lp = self.fm.lp
        self.ca_obj = ClusterAnalyzer(self.fm)

    def validateSinglenucData(self):
        # confirm that files required for both cluster and depth analysis are present, that euthanization data
        # is accessible, and that the project ID is present in the euthanization data
        if self.ca_obj is None:
            self.validateClusterData()
        if self.da_obj is None:
            self.validateDepthData()
        if (self.da_obj is None) or (self.ca_obj is None):
            return False

        try:
            self.euth_data = pd.read_csv(self.fm.localEuthData, index_col='pid', parse_dates=['dissection_time'],
                                         infer_datetime_format=True)
            self.euth_data = self.euth_data.loc[self.projectID]
            self.euth_data.dissection_time = self.euth_data.dissection_time.to_pydatetime()

        except:
            return False

    def createDepthFigures(self, hourlyDelta=2):
        # Create all figures based on depth data. Adjust hourlyDelta to influence the resolution of the
        # HourlyDepthSummary.pdf figure

        # Check that the DepthAnalzer object has been created, indicating that the required files are present.
        # Otherwise, skip creation of Depth Figures
        if self.da_obj is None:
            return

        # figures based on the depth data

        # Create summary figure of daily values
        figDaily = plt.figure(num=1, figsize=(11, 8.5))
        figDaily.suptitle(self.lp.projectID + ' Daily Depth Summary')
        gridDaily = gridspec.GridSpec(3, 1)

        # Create summary figure of hourly values
        figHourly = plt.figure(num=2, figsize=(11, 8.5))
        figHourly.suptitle(self.lp.projectID + ' Hourly Depth Summary')

        start_day = self.lp.frames[0].time.replace(hour=0, minute=0, second=0, microsecond=0)
        totalChangeData = vars(self.da_obj.returnVolumeSummary(self.lp.frames[0].time, self.lp.frames[-1].time))

        # Show picture of final depth
        topGrid = gridspec.GridSpecFromSubplotSpec(1, 3, subplot_spec=gridDaily[0])
        topAx1 = figDaily.add_subplot(topGrid[0])
        topAx1_ax = topAx1.imshow(self.da_obj.returnHeight(self.lp.frames[-1].time, cropped=True), vmin=50, vmax=70)
        topAx1.set_title('Final Depth (cm)')
        topAx1.tick_params(colors=[0, 0, 0, 0])
        plt.colorbar(topAx1_ax, ax=topAx1)

        # Show picture of total depth change
        topAx2 = figDaily.add_subplot(topGrid[1])
        topAx2_ax = topAx2.imshow(self.da_obj.returnHeightChange(
            self.lp.frames[0].time, self.lp.frames[-1].time, cropped=True), vmin=-5, vmax=5)
        topAx2.set_title('Total Depth Change (cm)')
        topAx2.tick_params(colors=[0, 0, 0, 0])
        plt.colorbar(topAx2_ax, ax=topAx2)

        # Show picture of pit and castle mask
        topAx3 = figDaily.add_subplot(topGrid[2])
        topAx3_ax = topAx3.imshow(self.da_obj.returnHeightChange(self.lp.frames[0].time, self.lp.frames[-1].time, cropped = True, masked = True), vmin = -5, vmax = 5)
        topAx3.set_title('Masked Depth Change (cm)')
        topAx3.tick_params(colors=[0, 0, 0, 0])
        plt.colorbar(topAx3_ax, ax=topAx3)

        # Create figures and get data for daily Changes
        dailyChangeData = []
        w_ratios = ([1.0] * self.lp.numDays) + [0.25]
        midGrid = gridspec.GridSpecFromSubplotSpec(3, self.lp.numDays + 1, subplot_spec=gridDaily[1], width_ratios=w_ratios)
        v = 2
        for i in range(self.lp.numDays):
            start = start_day + datetime.timedelta(hours=24 * i)
            stop = start_day + datetime.timedelta(hours=24 * (i + 1))
            dailyChangeData.append(vars(self.da_obj.returnVolumeSummary(start, stop)))
            dailyChangeData[i]['Day'] = i + 1
            dailyChangeData[i]['Midpoint'] = i + 1 + .5
            dailyChangeData[i]['StartTime'] = str(start)

            current_axs = [figDaily.add_subplot(midGrid[n, i]) for n in [0, 1, 2]]
            current_axs[0].imshow(self.da_obj.returnHeightChange(start_day, stop, cropped=True), vmin=-v, vmax=v)
            current_axs[0].set_title('Day %i' % (i + 1))
            current_axs[1].imshow(self.da_obj.returnHeightChange(start, stop, cropped=True), vmin=-v, vmax=v)
            current_axs[2].imshow(self.da_obj.returnHeightChange(start, stop, masked=True, cropped=True), vmin=-v, vmax=v)
            [ax.tick_params(colors=[0, 0, 0, 0]) for ax in current_axs]
            [ax.set_adjustable('box') for ax in current_axs]
        cax = figDaily.add_subplot(midGrid[:, -1])
        plt.colorbar(cm.ScalarMappable(norm=colors.Normalize(vmin=-v, vmax=v), cmap='viridis'), cax=cax)

        figHourly = plt.figure(figsize=(11, 8.5))
        gridHourly = plt.GridSpec(self.lp.numDays, int(24 / hourlyDelta) + 2, wspace=0.05, hspace=0.05)
        bounding_ax = figHourly.add_subplot(gridHourly[:, :])
        bounding_ax.xaxis.set_visible(False)
        bounding_ax.set_ylabel('Day')
        bounding_ax.set_ylim(self.lp.numDays + 0.5, 0.5)
        bounding_ax.yaxis.set_major_locator(ticker.MultipleLocator(base=1.0))
        bounding_ax.set_yticklabels(range(self.lp.numDays + 1))
        sns.despine(ax=bounding_ax, left=True, bottom=True)

        hourlyChangeData = []
        v = 1
        for i in range(0, self.lp.numDays):
            for j in range(int(24 / hourlyDelta)):
                start = start_day + datetime.timedelta(hours=24 * i + j * hourlyDelta)
                stop = start_day + datetime.timedelta(hours=24 * i + (j + 1) * hourlyDelta)

                hourlyChangeData.append(vars(self.da_obj.returnVolumeSummary(start, stop)))
                hourlyChangeData[-1]['Day'] = i + 1
                hourlyChangeData[-1]['Midpoint'] = i + 1 + ((j + 0.5) * hourlyDelta) / 24
                hourlyChangeData[-1]['StartTime'] = str(start)

                current_ax = figHourly.add_subplot(gridHourly[i, j])

                current_ax.imshow(self.da_obj.returnHeightChange(start, stop, cropped=True), vmin=-v, vmax=v)
                current_ax.set_adjustable('box')
                current_ax.tick_params(colors=[0, 0, 0, 0])
                if i == 0:
                    current_ax.set_title(str(j * hourlyDelta) + '-' + str((j + 1) * hourlyDelta))

            current_ax = figHourly.add_subplot(gridHourly[i, -2])
            current_ax.imshow(self.da_obj.returnBowerLocations(stop - datetime.timedelta(hours=24), stop, cropped=True),
                              vmin=-v, vmax=v)
            current_ax.set_adjustable('box')
            current_ax.tick_params(colors=[0, 0, 0, 0])
            if i == 0:
                current_ax.set_title('Daily\nMask')

            current_ax = figHourly.add_subplot(gridHourly[i, -1])
            current_ax.imshow(self.da_obj.returnHeightChange(stop - datetime.timedelta(hours=24), stop, cropped=True),
                              vmin=-v, vmax=v)
            current_ax.set_adjustable('box')
            current_ax.tick_params(colors=[0, 0, 0, 0])
            if i == 0:
                current_ax.set_title('Daily\nChange')

        totalDT = pd.DataFrame([totalChangeData])
        dailyDT = pd.DataFrame(dailyChangeData)
        hourlyDT = pd.DataFrame(hourlyChangeData)

        writer = pd.ExcelWriter(self.fm.localSummaryDir + 'DepthDataSummary.xlsx')
        totalDT.to_excel(writer, 'Total')
        dailyDT.to_excel(writer, 'Daily')
        hourlyDT.to_excel(writer, 'Hourly')
        writer.save()

        bottomGrid = gridspec.GridSpecFromSubplotSpec(2, 1, subplot_spec=gridDaily[2], hspace=0.05)
        bIAx = figDaily.add_subplot(bottomGrid[1])
        bIAx.axhline(linewidth=1, alpha=0.5, y=0)
        bIAx.scatter(dailyDT['Midpoint'], dailyDT['depthBowerIndex'])
        bIAx.scatter(hourlyDT['Midpoint'], hourlyDT['depthBowerIndex'])
        bIAx.set_xlabel('Day')
        bIAx.set_ylabel('Bower\nIndex')
        bIAx.xaxis.set_major_locator(ticker.MultipleLocator(base=1.0))

        volAx = figDaily.add_subplot(bottomGrid[0], sharex=bIAx)
        volAx.plot(dailyDT['Midpoint'], dailyDT['depthBowerVolume'])
        volAx.plot(hourlyDT['Midpoint'], hourlyDT['depthBowerVolume'])
        volAx.set_ylabel('Volume\nChange')
        plt.setp(volAx.get_xticklabels(), visible=False)

        figDaily.savefig(self.fm.localSummaryDir + 'DailyDepthSummary.pdf')
        subprocess.run(['cp', self.fm.localSummaryDir + 'DailyDepthSummary.pdf', self.fm.localAnalysisStatesDir + self.projectID + '_DepthSummary.pdf'])
        figHourly.savefig(self.fm.localSummaryDir + 'HourlyDepthSummary.pdf')

        plt.close('all')

    def createClusterFigures(self, hourlyDelta=1):
        # Create all figures based on Cluster data. Adjust hourlyDelta to influence the resolution of the
        # HourlyScoopSpitDensities.pdf figure

        # Check that the ClusterAnalyzer object has been created, indicating that the required files are present.
        # Otherwise, skip creation of Cluster Figures
        if self.ca_obj is None:
            return

        # figures based on the cluster data

        # semi-transparent scatterplots showing the spatial distrubtion of each cluster classification each day
        fig, axes = plt.subplots(10, self.lp.numDays, figsize=(8.5, 11))
        if self.lp.numDays == 1:
            axes = np.reshape(axes, (10, 1))
        fig.suptitle(self.lp.projectID + ' Daily Cluster Distributions')
        t0 = self.lp.frames[0].time.replace(hour=0, minute=0, second=0, microsecond=0)
        df_cropped = self.ca_obj.sliceDataframe(cropped=True)
        x_limits = (self.ca_obj.cropped_dims[0], 0)
        y_limits = (0, self.ca_obj.cropped_dims[1])
        for i in range(self.lp.numDays):
            t1 = t0 + datetime.timedelta(hours=24)
            df_slice = self.ca_obj.sliceDataframe(t0=t0, t1=t1, input_frame=df_cropped)
            for j, bid in enumerate(self.ca_obj.bids):
                df_slice_slice = self.ca_obj.sliceDataframe(input_frame=df_slice, bid=bid)
                sns.scatterplot(x='Y_depth', y='X_depth', data=df_slice_slice, ax=axes[j, i], s=10,
                                linewidth=0, alpha=0.1)
                axes[j, i].tick_params(colors=[0, 0, 0, 0])
                axes[j, i].set(xlabel=None, ylabel=None, aspect='equal', xlim=y_limits, ylim=x_limits)
                if j == 0:
                    axes[0, i].set_title('day %i' % (i + 1))
                if i == 0:
                    axes[j, 0].set_ylabel(str(bid))
            t0 = t1
        fig.savefig(self.fm.localSummaryDir + 'DailyClusterDistributions.pdf')
        plt.close(fig=fig)

        # heatmaps of the estimated daily scoop and spit areal densities
        start_day = self.lp.frames[0].time.replace(hour=0, minute=0, second=0, microsecond=0)
        fig, axes = plt.subplots(2, self.lp.numDays, figsize=(1.5 * self.lp.numDays, 4))
        if self.lp.numDays == 1:
            axes = np.reshape(axes, (2, 1))
        fig.suptitle(self.lp.projectID + ' Daily Scoop Spit Heatmaps')
        vmax = 0
        cbar_reference = None
        subplot_handles = []
        dailyChangeData = []
        for i in range(self.lp.numDays):
            start = start_day + datetime.timedelta(hours=24 * i)
            stop = start_day + datetime.timedelta(hours=24 * (i + 1))
            dailyChangeData.append(vars(self.da_obj.returnVolumeSummary(start, stop)))
            dailyChangeData[i]['Day'] = i + 1
            dailyChangeData[i]['Midpoint'] = i + 1 + .5
            dailyChangeData[i]['StartTime'] = str(start)

            z_scoop = self.ca_obj.returnClusterKDE(t0=start, t1=stop, bid='c', cropped=True)
            z_spit = self.ca_obj.returnClusterKDE(t0=start, t1=stop, bid='p', cropped=True)
            z = z_spit - z_scoop
            im = axes[0, i].imshow(z, cmap='viridis', interpolation='none')
            subplot_handles.append(im)
            axes[0, i].set(title='day %i' % (i + 1), xlabel=None, ylabel=None, aspect='equal')
            axes[0, i].tick_params(colors=[0, 0, 0, 0])
            if np.max(np.abs(z)) > vmax:
                vmax = np.max(np.abs(z))
                cbar_reference = im
            bowers = self.ca_obj.returnBowerLocations(start, stop, cropped=True)
            axes[1, i].imshow(bowers, cmap='viridis', vmin=-1, vmax=1)
            axes[1, i].set(xlabel=None, ylabel=None, aspect='equal')
            axes[1, i].tick_params(colors=[0, 0, 0, 0])
        for im in subplot_handles:
            im.set_clim(-vmax, vmax)
        if vmax != 0:
            cbar = fig.colorbar(cbar_reference, ax=axes[0, :].tolist(), shrink=0.7)
            cbar.set_label(r'$spits/cm^2$ - $scoops/cm^2$')
            cbar = fig.colorbar(cm.ScalarMappable(norm=colors.Normalize(vmin=-1, vmax=1), cmap=cm.get_cmap('viridis', 3)),
                         ax=axes[1, :].tolist(), shrink=0.7)
            cbar.set_label('bower region')
            cbar.set_ticks([-1, 0, 1])

        fig.savefig(self.fm.localSummaryDir + 'DailyScoopSpitDensities.pdf')
        plt.close(fig=fig)

        # heatmaps of the estimated hourly scoop and spit areal densities
        fig = plt.figure(figsize=(11, 8.5))
        grid = plt.GridSpec(self.lp.numDays, int(10 / hourlyDelta) + 2, wspace=0.05, hspace=0.05)
        bounding_ax = fig.add_subplot(grid[:, :])
        bounding_ax.xaxis.set_visible(False)
        bounding_ax.set_ylabel('Day')
        bounding_ax.set_ylim(self.lp.numDays + 0.5, 0.5)
        bounding_ax.yaxis.set_major_locator(ticker.MultipleLocator(base=1.0))
        bounding_ax.set_yticklabels(range(self.lp.numDays + 1))
        sns.despine(ax=bounding_ax, left=True, bottom=True)

        hourlyChangeData = []
        v = 3
        for i in range(0, self.lp.numDays):
            for j in range(int(10 / hourlyDelta)):
                start = start_day + datetime.timedelta(hours=24 * i + j * hourlyDelta + 8)
                stop = start_day + datetime.timedelta(hours=24 * i + (j + 1) * hourlyDelta + 8)

                hourlyChangeData.append(vars(self.ca_obj.returnClusterSummary(start, stop)))
                hourlyChangeData[-1]['Day'] = i + 1
                hourlyChangeData[-1]['Midpoint'] = i + 1 + ((j + 0.5) * hourlyDelta + 8) / 24
                hourlyChangeData[-1]['StartTime'] = str(start)

                current_ax = fig.add_subplot(grid[i, j])

                scoops = self.ca_obj.returnClusterKDE(start, stop, 'c', cropped=True)
                spits = self.ca_obj.returnClusterKDE(start, stop, 'p', cropped=True)
                current_ax.imshow(spits - scoops, vmin=-v, vmax=v)
                current_ax.set_adjustable('box')
                current_ax.tick_params(colors=[0, 0, 0, 0])
                if i == 0:
                    current_ax.set_title(str(j * hourlyDelta + 8) + '-' + str((j + 1) * hourlyDelta + 8))

            current_ax = fig.add_subplot(grid[i, -2])
            current_ax.imshow(self.ca_obj.returnBowerLocations(stop - datetime.timedelta(hours=24), stop, cropped=True),
                              vmin=-1, vmax=1)
            current_ax.set_adjustable('box')
            current_ax.tick_params(colors=[0, 0, 0, 0])
            if i == 0:
                current_ax.set_title('Daily\nMask')

            current_ax = fig.add_subplot(grid[i, -1])
            scoops = self.ca_obj.returnClusterKDE(stop - datetime.timedelta(hours=24), stop, 'c', cropped=True)
            spits = self.ca_obj.returnClusterKDE(stop - datetime.timedelta(hours=24), stop, 'p', cropped=True)
            current_ax.imshow(spits - scoops, vmin=-v, vmax=v)
            current_ax.set_adjustable('box')
            current_ax.tick_params(colors=[0, 0, 0, 0])
            if i == 0:
                current_ax.set_title('Daily\nTotal')

        fig.savefig(self.fm.localSummaryDir + 'HourlyScoopSpitDensities.pdf')
        plt.close(fig=fig)

        totalChangeData = vars(self.ca_obj.returnClusterSummary(self.lp.frames[0].time, self.lp.frames[-1].time))

        totalDT = pd.DataFrame([totalChangeData])
        dailyDT = pd.DataFrame(dailyChangeData)
        hourlyDT = pd.DataFrame(hourlyChangeData)

        writer = pd.ExcelWriter(self.fm.localSummaryDir + 'ClusterDataSummary.xlsx')
        totalDT.to_excel(writer, 'Total')
        dailyDT.to_excel(writer, 'Daily')
        hourlyDT.to_excel(writer, 'Hourly')
        writer.save()

        # heatmap of the estimated whole-trial scoop and spit areal densities
        fig, ax = plt.subplots(1, 1)
        scoops = self.ca_obj.returnClusterKDE(self.lp.frames[0].time, self.lp.frames[-1].time, 'c', cropped=True)
        spits = self.ca_obj.returnClusterKDE(self.lp.frames[0].time, self.lp.frames[-1].time, 'p', cropped=True)
        z = spits - scoops
        v = 0.75 * np.max(np.abs(z))
        handle = ax.imshow(z, vmin=-v, vmax=v)
        cbar = fig.colorbar(handle, ax=ax)
        cbar.set_label(r'$spits/cm^2$ - $scoops/cm^2$')
        ax.set(title='whole-trial spit-scoop KDE', xlabel=None, ylabel=None, aspect='equal')
        ax.tick_params(colors=[0, 0, 0, 0])
        fig.savefig(self.fm.localSummaryDir + 'WholeTrialScoopSpitDensities.pdf')
        plt.close(fig=fig)

    def createCombinedFigures(self):
        # Create all figures that depend simultaneously on depth and cluster data.

        # Check that the ClusterAnalyzer object and DepthAnalyzer object have been created, indicating that the
        # required files are present. Otherwise, skip creation of Combined Figures
        if (self.ca_obj is None) or (self.da_obj is None):
            return

        # create figures based on a combination of cluster and depth data

        # plot overlap of daily bower regions identified from depth and cluster data
        fig, axes = plt.subplots(3, self.lp.numDays, figsize=(1.5 * self.lp.numDays, 6))
        if self.lp.numDays == 1:
            axes = np.reshape(axes, (3, 1))
        fig.suptitle(self.lp.projectID + ' Daily Bower Identification Consistency')
        t0 = self.lp.frames[0].time.replace(hour=0, minute=0, second=0, microsecond=0)
        for i in range(self.lp.numDays):
            t1 = t0 + datetime.timedelta(hours=24)

            depth_bowers = self.da_obj.returnBowerLocations(t0, t1, cropped=True)
            axes[0, i].imshow(depth_bowers, cmap='viridis', vmin=-1, vmax=1)
            axes[0, i].set(xlabel=None, ylabel=None, aspect='equal')
            axes[0, i].tick_params(colors=[0, 0, 0, 0])

            cluster_bowers = self.ca_obj.returnBowerLocations(t0, t1, cropped=True)
            axes[1, i].imshow(cluster_bowers, cmap='viridis', vmin=-1, vmax=1)
            axes[1, i].set(xlabel=None, ylabel=None, aspect='equal')
            axes[1, i].tick_params(colors=[0, 0, 0, 0])

            bower_intersection = np.where((depth_bowers == cluster_bowers) & (depth_bowers != 0), True, False)
            bower_intersection_area = np.count_nonzero(bower_intersection)
            bower_union = np.where((depth_bowers != 0) | (cluster_bowers != 0), True, False)
            bower_union_area = np.count_nonzero(bower_union)
            if bower_intersection_area == bower_union_area == 0:
                similarity = 1.0
            elif (bower_intersection_area == 0) | (bower_union_area == 0):
                similarity = 0.0
            else:
                similarity = bower_intersection_area / bower_union_area

            axes[2, i].imshow(-1 *((2 * bower_intersection) - bower_union), cmap='bwr', vmin=-1, vmax=1)
            axes[2, i].set(xlabel='J = {0:.3f}'.format(similarity), ylabel=None, aspect='equal')
            axes[2, i].tick_params(colors=[0, 0, 0, 0])

            t0 = t1

        axes[0, 0].set_ylabel('Depth Bowers')
        axes[1, 0].set_ylabel('Cluster Bowers')
        axes[2, 0].set_ylabel('Overlap')

        cbar = fig.colorbar(cm.ScalarMappable(norm=colors.Normalize(vmin=-1, vmax=1), cmap=cm.get_cmap('viridis', 3)),
                            ax=axes[0, :].tolist(), shrink=0.7)
        cbar.set_label('bower region')
        cbar.set_ticks([-1, 0, 1])
        cbar.set_ticklabels(['-', '0', '+'])

        cbar = fig.colorbar(cm.ScalarMappable(norm=colors.Normalize(vmin=-1, vmax=1), cmap=cm.get_cmap('viridis', 3)),
                            ax=axes[1, :].tolist(), shrink=0.7)
        cbar.set_label('bower region')
        cbar.set_ticks([-1, 0, 1])
        cbar.set_ticklabels(['-', '0', '+'])

        cbar = fig.colorbar(cm.ScalarMappable(norm=colors.Normalize(vmin=-1, vmax=1), cmap=cm.get_cmap('bwr', 3)),
                            ax=axes[2, :].tolist(), shrink=0.7)
        cbar.set_label('Labels Agree?')
        cbar.set_ticks([-1, 1])
        cbar.set_ticklabels(['Y', 'N'])

        fig.savefig(self.fm.localSummaryDir + 'DailyBowerIdentificationConsistency.pdf')
        plt.close(fig=fig)

        # create figure of whole-trial bower identification overlap

        fig, axes = plt.subplots(3, 1, figsize=(2, 6))
        fig.suptitle(self.lp.projectID + ' Whole-Trial Bower Identification Consistency')
        t0 = self.lp.master_start.replace(hour=0, minute=0, second=0, microsecond=0)
        t1 = t0 + (self.lp.numDays * datetime.timedelta(hours=24))

        depth_bowers = self.da_obj.returnBowerLocations(t0, t1, cropped=True)
        axes[0].imshow(depth_bowers, cmap='viridis', vmin=-1, vmax=1)
        axes[0].set(xlabel=None, ylabel=None, aspect='equal')
        axes[0].tick_params(colors=[0, 0, 0, 0])

        cluster_bowers = self.ca_obj.returnBowerLocations(t0, t1, cropped=True)
        axes[1].imshow(cluster_bowers, cmap='viridis', vmin=-1, vmax=1)
        axes[1].set(xlabel=None, ylabel=None, aspect='equal')
        axes[1].tick_params(colors=[0, 0, 0, 0])

        bower_intersection = np.where((depth_bowers == cluster_bowers) & (depth_bowers != 0), True, False)
        bower_intersection_area = np.count_nonzero(bower_intersection)
        bower_union = np.where((depth_bowers != 0) | (cluster_bowers != 0), True, False)
        bower_union_area = np.count_nonzero(bower_union)
        if bower_intersection_area == bower_union_area == 0:
            similarity = 1.0
        elif (bower_intersection_area == 0) | (bower_union_area == 0):
            similarity = 0.0
        else:
            similarity = bower_intersection_area / bower_union_area

        axes[2].imshow(-1 *((2 * bower_intersection) - bower_union), cmap='bwr', vmin=-1, vmax=1)
        axes[2].set(xlabel='J = {0:.3f}'.format(similarity), ylabel=None, aspect='equal')
        axes[2].tick_params(colors=[0, 0, 0, 0])

        axes[0].set_ylabel('Depth Bowers')
        axes[1].set_ylabel('Cluster Bowers')
        axes[2].set_ylabel('Overlap')

        cbar = fig.colorbar(cm.ScalarMappable(norm=colors.Normalize(vmin=-1, vmax=1), cmap=cm.get_cmap('viridis', 3)),
                            ax=axes[0], shrink=0.7)
        cbar.set_label('bower region')
        cbar.set_ticks([-1, 0, 1])
        cbar.set_ticklabels(['-', '0', '+'])

        cbar = fig.colorbar(cm.ScalarMappable(norm=colors.Normalize(vmin=-1, vmax=1), cmap=cm.get_cmap('viridis', 3)),
                            ax=axes[1], shrink=0.7)
        cbar.set_label('bower region')
        cbar.set_ticks([-1, 0, 1])
        cbar.set_ticklabels(['-', '0', '+'])

        cbar = fig.colorbar(cm.ScalarMappable(norm=colors.Normalize(vmin=-1, vmax=1), cmap=cm.get_cmap('bwr', 3)),
                            ax=axes[2], shrink=0.7)
        cbar.set_label('Labels Agree?')
        cbar.set_ticks([-1, 1])
        cbar.set_ticklabels(['Y', 'N'])

        fig.savefig(self.fm.localSummaryDir + 'WholeTrialBowerIdentificationConsistency.pdf')
        plt.close(fig=fig)

    def createPaceSummary(self):
        # if the troubleshooting directory contains .out files, uses them to summarize the PACE analysis. Otherwise,
        # print a message indicating that no .out files are present and move on.
        if os.path.exists(self.fm.localPaceDir) and len(glob.glob(str(self.fm.localPaceDir) + '*.out*')) > 0:
            regexes = {'job_id': re.compile(r'Job id:(?P<job_id>.*)\n'),
                       'job_name': re.compile(r'Job name:(?P<job_name>.*)\n'),
                       'requested': re.compile(r'Resources:(?P<requested>.*)\n'),
                       'used': re.compile(r'Rsrc Used:(?P<used>.*)\n'),
                       'start': re.compile(r'Begin PBS Prologue (?P<start>.*)\n'),
                       'end': re.compile(r'End PBS Epilogue (?P<end>.*)\n'),
                       'outcome': re.compile(r'PBS: job killed: (?P<outcome>.*)\n')}

            rows = []
            for f_name in glob.glob(str(self.fm.localPaceDir) + '*.out*'):
                row = {}
                with open(f_name) as f:
                    line = f.readline()
                    while line:
                        for key, rx in regexes.items():
                            match = rx.search(line)
                            if match:
                                if (key == 'requested') or (key == 'used'):
                                    update = [tuple([i.strip() for i in item.split('=', 1)])
                                              for item in re.split(r',|(?=.):(?=\D)', match.group(key))]
                                    update = [x + tuple('Y') if (len(x) is 1) else x for x in update]
                                    row.update(update)
                                else:
                                    row.update({key: match.group(key)})
                                if 'outcome' not in row.keys():
                                    row.update({'outcome': 'successful'})
                        line = f.readline()
                rows.append(row)
            all_data = pd.DataFrame(rows).sort_values(by='job_name').reset_index(drop=True)
            all_data.to_csv(self.fm.localSummaryDir + 'paceSummary.csv')

        else:
            pass

    def createSinglenucFigures(self, time_window=90, dt=10):

        # confirm that the required data is present
        if self.euth_data is None:
            return

        n_plots = int(time_window/dt)
        half_viridis = colors.LinearSegmentedColormap.from_list('name', cm.viridis(np.linspace(0.5, 1)))

        # determine time window immediately before euthanization
        t1 = self.euth_data.dissection_time - datetime.timedelta(minutes=5)
        t0 = t1 - datetime.timedelta(minutes=time_window)

        # generate a parent figure
        fig = plt.figure(figsize=(17, 22))
        fig.suptitle(self.projectID + ' activity in 90 minutes preceding euthanization')
        outer_grid = gridspec.GridSpec(11, 1)

        # plot whole-period metrics at the top of the parent figure
        curr_grid = gridspec.GridSpecFromSubplotSpec(1, 5, subplot_spec=outer_grid[0:2])

        curr_ax = fig.add_subplot(curr_grid[0])
        height_change = self.da_obj.returnHeightChange(t0, t1, cropped=True)
        v = np.nanquantile(np.abs(height_change), 0.99)
        curr_ax.imshow(height_change, vmin=-v, vmax=v)
        curr_ax.set_title('Depth Change')
        curr_ax.set(aspect='equal')
        cbar = fig.colorbar(cm.ScalarMappable(norm=colors.Normalize(vmin=-v, vmax=v), cmap=cm.get_cmap('viridis', 30)),
                            ax=curr_ax, use_gridspec=False, shrink=0.7, location='bottom')
        cbar.set_label('depth change (cm)')
        cbar.set_ticks([-v, 0, v])
        cbar.set_ticklabels(['{0:.2f}'.format(-v), '0', '{0:.2f}'.format(v)])
        curr_ax.tick_params(colors=[0, 0, 0, 0])

        curr_ax = fig.add_subplot(curr_grid[1])
        depth_bowers = self.da_obj.returnBowerLocations(t0, t1, cropped=True)
        curr_ax.imshow(depth_bowers, vmin=-1, vmax=1)
        curr_ax.set_title('Depth Bowers')
        curr_ax.set(aspect='equal')
        cbar = fig.colorbar(cm.ScalarMappable(norm=colors.Normalize(vmin=-1, vmax=1), cmap=cm.get_cmap('viridis', 3)),
                            ax=curr_ax, use_gridspec=False, shrink=0.7, location='bottom')
        cbar.set_label('bower region')
        cbar.set_ticks([-1, 0, 1])
        cbar.set_ticklabels(['-', '0', '+'])
        curr_ax.tick_params(colors=[0, 0, 0, 0])

        curr_ax = fig.add_subplot(curr_grid[2])
        scoops = self.ca_obj.returnClusterKDE(t0, t1, 'c', cropped=True)
        spits = self.ca_obj.returnClusterKDE(t0, t1, 'p', cropped=True)
        z = spits - scoops
        v = 0.75*np.max(np.abs(z))
        curr_ax.imshow(z, vmin=-v, vmax=v)
        cbar = fig.colorbar(cm.ScalarMappable(norm=colors.Normalize(vmin=-v, vmax=v), cmap=cm.get_cmap('viridis', 30)),
                            ax=curr_ax, use_gridspec=False, shrink=0.7, location='bottom')
        cbar.set_label('spit-scoop difference\n'+r'$events/cm^2$')
        cbar.set_ticks([-v, 0, v])
        cbar.set_ticklabels(['{0:.2f}'.format(-v), '0', '{0:.2f}'.format(v)])
        curr_ax.set_title('Spit-scoop KDE')
        curr_ax.set(aspect='equal')
        curr_ax.tick_params(colors=[0, 0, 0, 0])

        curr_ax = fig.add_subplot(curr_grid[3])
        cluster_bowers = self.ca_obj.returnBowerLocations(t0, t1, cropped=True)
        curr_ax.imshow(cluster_bowers, vmin=-1, vmax=1)
        curr_ax.set_title('Spit-Scoop Bowers')
        curr_ax.set(aspect='equal')
        curr_ax.tick_params(colors=[0, 0, 0, 0])
        cbar = fig.colorbar(cm.ScalarMappable(norm=colors.Normalize(vmin=-1, vmax=1), cmap=cm.get_cmap('viridis', 3)),
                            ax=curr_ax, use_gridspec=False, shrink=0.7, location='bottom')
        cbar.set_label('bower region')
        cbar.set_ticks([-1, 0, 1])
        cbar.set_ticklabels(['-', '0', '+'])

        curr_ax = fig.add_subplot(curr_grid[4])
        bower_intersection = np.where((depth_bowers == cluster_bowers) & (depth_bowers != 0), True, False)
        bower_intersection_area = np.count_nonzero(bower_intersection)
        bower_union = np.where((depth_bowers != 0) | (cluster_bowers != 0), True, False)
        bower_union_area = np.count_nonzero(bower_union)
        if bower_intersection_area == bower_union_area == 0:
            similarity = 1.0
        elif (bower_intersection_area == 0) | (bower_union_area == 0):
            similarity = 0.0
        else:
            similarity = bower_intersection_area / bower_union_area
        curr_ax.imshow(-1 * ((2 * bower_intersection) - bower_union), cmap='bwr', vmin=-1, vmax=1)
        curr_ax.set_title('Overlap')
        curr_ax.set(aspect='equal')
        curr_ax.tick_params(colors=[0, 0, 0, 0])
        cbar = fig.colorbar(cm.ScalarMappable(norm=colors.Normalize(vmin=-1, vmax=1), cmap=cm.get_cmap('bwr', 3)),
                            ax=curr_ax, use_gridspec=False, shrink=0.7, location='bottom')
        cbar.set_label('J = {0:.3f}'.format(similarity))
        cbar.set_ticks([-1, 1])
        cbar.set_ticklabels(['N', 'Y'])
        curr_ax.set_title('Overlap')
        #
        # plot detailed depth change over the pre-euthanization period
        wr = [1] + ([5] * n_plots) + [1]
        curr_grid = gridspec.GridSpecFromSubplotSpec(1, n_plots+2, subplot_spec=outer_grid[3], width_ratios=wr)
        dt = (t1 - t0)/n_plots
        t0_curr = t0
        v_max = 0
        axes = [fig.add_subplot(curr_grid[i]) for i in range(n_plots+1)]
        plot_axes = axes[1:]
        text_ax = axes[0]

        for plot_ax in plot_axes:
            height_change = self.da_obj.returnHeightChange(t0_curr, t0_curr+dt, cropped=True)
            v = np.nanquantile(np.abs(height_change), 0.99)
            v_max = v if v > v_max else v_max
            plot_ax.imshow(height_change, vmin=-1, vmax=1)
            plot_ax.tick_params(bottom=False, left=False, labelbottom=False, labelleft=False, which='both')
            mins_to_euth = ((self.euth_data.dissection_time - t0_curr) - (dt/2)).seconds/60
            plot_ax.set_title(r'$t_{euth} - $' + '{0:.0f} m'.format(mins_to_euth), fontdict={'fontsize': 12})
            abs_height_change = np.nansum(np.abs(height_change))
            abs_vol_change = abs_height_change * (self.fm.pixelLength ** 2)
            plot_ax.set_xlabel('|dV|={0:.2f}'.format(abs_vol_change) + r' $cm^3$', fontdict={'fontsize': 9}, labelpad=1)
            plot_ax.set(aspect='equal')
            t0_curr = t0_curr + dt
        v_max = np.round(v_max, 2)
        for plot_ax in plot_axes:
            plot_ax.get_images()[0].set_clim(-v_max, v_max)

        cax_parent = fig.add_subplot(curr_grid[-1])
        cax_parent.axis('off')
        cax = inset_axes(cax_parent, height='100%', width='70%', loc='center')
        cbar = plt.colorbar(cm.ScalarMappable(norm=colors.Normalize(vmin=-v_max, vmax=v_max),
                                              cmap='viridis'), cax=cax, shrink=0.7)
        cbar.set_label('cm', size=9)
        cbar.set_ticks([-v_max, 0, v_max])
        cbar.set_ticklabels(['{0:.2f}'.format(-v_max), '0', '{0:.2f}'.format(v_max)])

        text_ax.text(0.5, 0.5, 'sand-height\nchange', size=9, ha='center', va='center', rotation='vertical')
        text_ax.axis('off')


        # plot detailed spit-scoop kde's over the pre-euthanization period
        wr = [1] + ([5] * n_plots) + [1]
        curr_grid = gridspec.GridSpecFromSubplotSpec(1, n_plots+2, subplot_spec=outer_grid[4], width_ratios=wr)
        v_max = 0
        dt = (t1 - t0)/n_plots
        t0_curr = t0
        axes = [fig.add_subplot(curr_grid[i]) for i in range(n_plots+1)]
        plot_axes = axes[1:]
        text_ax = axes[0]

        for plot_ax in plot_axes:
            scoops = self.ca_obj.returnClusterKDE(t0_curr, t0_curr+dt, 'c', cropped=True)
            spits = self.ca_obj.returnClusterKDE(t0_curr, t0_curr+dt, 'p', cropped=True)
            z = spits - scoops
            v = 0.75*np.max(np.abs(z))
            v_max = v if v > v_max else v_max
            n_events = self.ca_obj.returnClusterCounts(t0=t0_curr, t1=t0_curr+dt, bid=['p', 'c'], cropped=True)
            plot_ax.imshow(z, vmin=-1, vmax=1, cmap='viridis')
            plot_ax.set_xlabel('N = {}'.format(n_events), fontdict={'fontsize': 9}, labelpad=1)
            plot_ax.set(aspect='equal')
            plot_ax.tick_params(bottom=False, left=False, labelbottom=False, labelleft=False, which='both')
            t0_curr = t0_curr + dt
        v_max = np.round(v_max, 2)
        for plot_ax in plot_axes:
            plot_ax.get_images()[0].set_clim(-v_max, v_max)

        cax_parent = fig.add_subplot(curr_grid[-1])
        cax_parent.axis('off')
        cax = inset_axes(cax_parent, height='100%', width='70%', loc='center')
        cbar = plt.colorbar(cm.ScalarMappable(norm=colors.Normalize(vmin=-v_max, vmax=v_max),
                                              cmap='viridis'), cax=cax, shrink=0.7)
        cbar.set_label(r'$(events/cm^2)$', size=9)
        cbar.set_ticks([-v_max, 0, v_max])
        cbar.set_ticklabels(['{0:.2f}'.format(-v_max), '0', '{0:.2f}'.format(v_max)])

        text_ax.text(0.5, 0.5, 'spit-scoop\ndifference', size=9, ha='center', va='center', rotation='vertical')
        text_ax.axis('off')

        # plot detailed kde's for individual behaviors of interest
        bids = ['c', 'p', 'b', 'f', 't', 'm', 's']
        v_max = 0
        dt = (t1 - t0) / n_plots
        wr = [1] + ([5] * n_plots) + [1]
        curr_grid = gridspec.GridSpecFromSubplotSpec(len(bids), n_plots + 2, subplot_spec=outer_grid[5:5+len(bids)],
                                                     width_ratios=wr)
        plot_axes = []

        for row, bid in enumerate(bids):
            t0_curr = t0
            axes = [fig.add_subplot(curr_grid[row, i]) for i in range(n_plots + 1)]
            axes[0].axis('off')
            axes[0].text(0.5, 0.5, self.ca_obj.bid_labels[bid], size=9, ha='center', va='center', rotation='vertical')
            for plot_ax in axes[1:]:
                plot_axes.append(plot_ax)
                kde = self.ca_obj.returnClusterKDE(t0_curr, t0_curr + dt, bid, cropped=True)
                n_events = self.ca_obj.returnClusterCounts(t0=t0_curr, t1=t0_curr + dt, bid=bid, cropped=True)
                v = 0.75 * np.max(kde)
                v_max = v if v > v_max else v_max
                plot_ax.imshow(kde, vmin=0, vmax=1, cmap=half_viridis)
                plot_ax.tick_params(bottom=False, left=False, labelbottom=False, labelleft=False, which='both')
                plot_ax.set_xlabel('N={}'.format(n_events), fontdict={'fontsize': 9}, labelpad=1)
                plot_ax.set(aspect='equal')
                t0_curr = t0_curr + dt
        for plot_ax in plot_axes:
            plot_ax.get_images()[0].set_clim(0, v_max)

        cax_parent = fig.add_subplot(curr_grid[:, -1])
        cax_parent.axis('off')
        cax = inset_axes(cax_parent, height='100%', width='70%', loc='center')
        cbar = plt.colorbar(cm.ScalarMappable(norm=colors.Normalize(vmin=0, vmax=v_max),
                                              cmap=half_viridis), cax=cax, shrink=0.7)
        cbar.set_label(r'$(events/cm^2)$', size=9)

        fig.savefig(self.fm.localSummaryDir + 'SingleNucFigures.pdf')
        plt.close(fig=fig)

        # generate a summary csv

        def get_row(t0, t1):
            ca_data = vars(self.ca_obj.returnClusterSummary(t0, t1))
            da_data = vars(self.da_obj.returnVolumeSummary(t0, t1))
            row = {'t0': t0, 't1': t1,
                   't_euth-t0': (self.euth_data.dissection_time - t0).seconds/60,
                   't_euth-t1': (self.euth_data.dissection_time - t1).seconds/60}
            row.update(ca_data)
            row.update(da_data)
            return row

        total_df = pd.DataFrame([get_row(t0, t1)])
        detail_df = []
        t0_curr = t0
        dt = (t1 - t0) / n_plots
        t1_curr = t0 + dt
        while t1_curr <= t1:
            detail_df.append(get_row(t0_curr, t1_curr))
            t0_curr = t0_curr + dt
            t1_curr = t1_curr + dt
        detail_df = pd.DataFrame(detail_df)

        writer = pd.ExcelWriter(self.fm.localSummaryDir + 'SingleNucDataSummary.xlsx')
        total_df.to_excel(writer, 'Total')
        detail_df.to_excel(writer, 'Detail')
        writer.save()

    def createFullSummary(self, clusterHourlyDelta=1, depthHourlyDelta=2):
        # Attempt to create all possible figures and summary files. If files required for a particular figure are
        # missing, it will be skipped without throwing an error. Adjust clusterHourlyDelta and depthHourlyDelta to
        # set the hourlyDelta argument of createDepthFigures and createClusterFigures respectively.
        self.createDepthFigures(hourlyDelta=depthHourlyDelta)
        self.createClusterFigures(hourlyDelta=clusterHourlyDelta)
        self.createCombinedFigures()
        self.createPaceSummary()
        self.createSinglenucFigures()

class MultiSummaryPreparer:
    # class for creating figures that summarize/compare data from multiple projects. Built for the single-nuc projects,
    # but could be adapted more generally with some modification
    def __init__(self, fileManager, use_pickle=True, smooth_depth=True):
        self.smooth_depth = smooth_depth
        self.fm = fileManager
        self.fm.downloadData(self.fm.localSummaryFile)
        self.fm.downloadData(self.fm.localEuthData)
        self.analysis_states = pd.read_csv(self.fm.localSummaryFile, index_col='projectID')
        self.euth_data = pd.read_csv(self.fm.localEuthData, index_col='pid', parse_dates=['dissection_time'],
                                     infer_datetime_format=True)
        self.pids = list(self.analysis_states.index)
        self.das_pickle = self.fm.localAnalysisStatesDir + 'das.pkl'
        self.cas_pickle = self.fm.localAnalysisStatesDir + 'cas.pkl'
        if use_pickle and os.path.exists(self.cas_pickle) and os.path.exists(self.das_pickle):
            with open(self.cas_pickle, 'rb') as f:
                self.cas = pickle.load(f)
            with open(self.das_pickle, 'rb') as f:
                self.das = pickle.load(f)
            if self.das[self.pids[0]].smooth_depth != self.smooth_depth:
                print('pickled depth analyzers do not match the chosen option for smooth_depth. Recreating')
                self.load_data()
        else:
            self.cas = {}
            self.das = {}
            self.load_data()
        self.sps = {pid: SummaryPreparer(self.cas[pid].fileManager, self.cas[pid], self.das[pid]) for pid in self.pids}
        self.bid_labels = self.cas[list(self.cas)[0]].bid_labels
        self.total_df = self.collate_total_data()
        self.cluster_detail_df = self.collate_detail_data_cluster()
        self.depth_detail_df = self.collate_detail_data_depth()

    def plot_all(self):
        self.plot_vol_change_lineplot()
        self.plot_build_feed_spawn_lineplots()
        self.plot_build_feed_spawn_histograms()
        self.generate_summary_spreadsheet()

    def load_data(self, time_window=90):
        for pid in self.pids:
            print(pid)
            t_max = self.euth_data.loc[pid, 'dissection_time'] - datetime.timedelta(minutes=5)
            t_min = t_max - datetime.timedelta(minutes=time_window)
            fm = FM(projectID=pid, summaryFile=os.path.basename(self.fm.localSummaryFile))
            fm.downloadProjectData('Summary')
            fm.downloadData(fm.localInterpDepthFile)
            self.cas.update({pid: ClusterAnalyzer(fm)})
            self.das.update({pid: DepthAnalyzer(fm, smooth_depth=self.smooth_depth)})
            self.das[pid].clip_data(t_min, t_max)

    def save_pickle(self):
        with open(self.cas_pickle, 'wb') as f:
            pickle.dump(self.cas, f)
        with open(self.das_pickle, 'wb') as f:
            pickle.dump(self.das, f)

    def collate_total_data(self, time_window=90):
        df = []
        pixel_length = 0.1030168618
        for pid in self.pids:
            row = {'pid': pid, 'behave_or_control': self.euth_data.loc[pid, 'behave_or_control']}
            ca = self.cas[pid]
            da = self.das[pid]
            t_max = self.euth_data.loc[pid, 'dissection_time'] - datetime.timedelta(minutes=5)
            t_min = t_max - datetime.timedelta(minutes=time_window)
            bids = ['c', 'p', 'b', 'f', 't', 'm', 's']
            for bid in bids:
                row.update({bid: ca.returnClusterCounts(t_min, t_max, bid)})
            row.update({'c+p+b': row['c'] + row['p'] + row['b']})
            row.update({'f+t+m': row['f'] + row['t'] + row['m']})
            bower_mask = np.abs(da.returnBowerLocations(t_min, t_max, force_window=True))
            abs_height_change = np.abs(da.returnHeightChange(t_min, t_max))
            total_abs_vol_change = np.nansum(abs_height_change) * (pixel_length ** 2)
            inbower_abs_vol_change = np.nansum(abs_height_change * bower_mask) * (pixel_length ** 2)
            row.update({'total_abs_vol_change': total_abs_vol_change,
                        'inbower_abs_vol_change': inbower_abs_vol_change})
            df.append(row)
        df = pd.DataFrame(df)
        return df

    def collate_detail_data_cluster(self, time_step=10, time_window=90):
        df = []
        time_step = datetime.timedelta(minutes=time_step)
        bids = ['c', 'p', 'b', 'f', 't', 'm', 's', ['c', 'p', 'b'], ['f', 't', 'm']]
        for pid in self.pids:
            ca = self.cas[pid]
            t_max = self.euth_data.loc[pid, 'dissection_time'] - datetime.timedelta(minutes=5)
            t_min = t_max - datetime.timedelta(minutes=time_window)
            for bid in bids:
                t0 = t_min
                t1 = t0 + time_step
                while t1 <= t_max:
                    row = {'pid': pid, 'behave_or_control': self.euth_data.loc[pid, 'behave_or_control']}
                    row.update({'bid': '+'.join(bid) if type(bid) is list else bid})
                    row.update({'t_euth-t0': (self.euth_data.loc[pid, 'dissection_time'] - t0).seconds/60})
                    row.update({'t_euth-t1': (self.euth_data.loc[pid, 'dissection_time'] - t1).seconds/60})
                    row.update({'n events': ca.returnClusterCounts(t0, t1, bid)})
                    df.append(row)
                    t1 += time_step
                    t0 += time_step
        df = pd.DataFrame(df)
        return df

    def collate_detail_data_depth(self, time_step=10, time_window=90):
        df = []
        time_step = datetime.timedelta(minutes=time_step)
        pixel_length = 0.1030168618
        for pid in self.pids:
            da = self.das[pid]
            t_max = self.euth_data.loc[pid, 'dissection_time'] - datetime.timedelta(minutes=5)
            t_min = t_max - datetime.timedelta(minutes=time_window)
            bower_mask = np.abs(da.returnBowerLocations(t_min, t_max, force_window=True))
            t0 = t_min
            t1 = t0 + time_step
            while t1 <= t_max:
                row = {'pid': pid, 'behave_or_control': self.euth_data.loc[pid, 'behave_or_control']}
                row.update({'t_euth-t0': (self.euth_data.loc[pid, 'dissection_time'] - t0).seconds/60})
                row.update({'t_euth-t1': (self.euth_data.loc[pid, 'dissection_time'] - t1).seconds/60})
                abs_height_change = np.abs(da.returnHeightChange(t0, t1))
                total_abs_vol_change = np.nansum(abs_height_change) * (pixel_length ** 2)
                inbower_abs_vol_change = np.nansum(abs_height_change * bower_mask) * (pixel_length ** 2)
                row.update({'total_abs_vol_change': total_abs_vol_change,
                            'inbower_abs_vol_change': inbower_abs_vol_change})
                df.append(row)
                t1 += time_step
                t0 += time_step
        df = pd.DataFrame(df)
        return df

    def plot_build_feed_spawn_histograms(self, n_bins=30):
        fig, axes = plt.subplots(3, 1, figsize=(5.5, 8.5))
        axes = axes.flatten()
        for i, behavior in enumerate(['c+p+b', 'f+t+m', 's']):
            sns.histplot(self.total_df, x=behavior, hue='behave_or_control', ax=axes[i], kde=True, bins=n_bins)
            axes[i].set(title=behavior, xlabel='n events in 90 minutes preceding euthanization')
        fig.tight_layout()
        fig.savefig(self.fm.localAnalysisStatesDir + 'behavioral_histograms.pdf')
        plt.close(fig)

    def plot_build_feed_spawn_lineplots(self):
        fig, axes = plt.subplots(2, 3, figsize=(11, 8.5), sharex='all', sharey='col')
        behaviors = ['c+p+b', 'f+t+m', 's']
        trial_types = ['C', 'B']
        df = self.cluster_detail_df[self.cluster_detail_df.bid.isin(behaviors)]
        for i, behavior in enumerate(behaviors):
            for j, trial_type in enumerate(trial_types):
                sub_df = df[(df.bid == behavior) & (df['behave_or_control'] == trial_type)]
                sns.lineplot(data=sub_df, x=sub_df['t_euth-t1'] * -1, y='n events', ax=axes[j, i], hue='pid', alpha=0.5, legend=False)
                title = behavior + (' Behave' if trial_type == 'B' else ' Control')
                axes[j, i].set(title=title, xlabel='time until euthanization (minutes)', ylabel='n events')
        fig.tight_layout()
        fig.savefig(self.fm.localAnalysisStatesDir + 'behavioral_lineplots.pdf')
        plt.close(fig)

    def plot_vol_change_lineplot(self):
        fig, ax = plt.subplots(1, 1, figsize=(5.5, 5.5))
        df = self.depth_detail_df
        for pid in self.pids:
            sub_df = df[df.pid == pid]
            color = 'red' if sub_df['behave_or_control'].iloc[0] == 'B' else 'blue'
            sns.lineplot(x=sub_df['t_euth-t1']*-1, y=np.cumsum(sub_df['inbower_abs_vol_change']), ax=ax, color=color)
            if (sub_df['inbower_abs_vol_change'].iloc[-1] > 0) and (sub_df['behave_or_control'].iloc[0] == 'C'):
                print('non-zero in-bower depth change for control trial {}'.format(pid))
            elif (sub_df['inbower_abs_vol_change'].iloc[-1] < 0.1) and (sub_df['behave_or_control'].iloc[0] == 'B'):
                print('zero in-bower depth change for behave trial {}'.format(pid))
        ax.set(xlabel='time before euthanization, minutes', ylabel='cumulative absolute in-bower volume change (cm^3)')
        fig.tight_layout()
        fig.savefig(self.fm.localAnalysisStatesDir + 'volume_lineplots.pdf')
        plt.close(fig)

    def merge_project_pdfs(self, filename):
        paths = [ca.fileManager.localSummaryDir + filename for ca in list(self.cas.values())]
        writer = pypdf.PdfFileWriter()
        for path in paths:
            f = open(path, 'rb')
            reader = pypdf.PdfFileReader(f)
            for page_number in range(reader.numPages):
                writer.addPage(reader.getPage(page_number))
        with open(self.fm.localAnalysisStatesDir + 'Collated' + filename, 'wb') as f:
            writer.write(f)

    def generate_summary_spreadsheet(self):
        writer = pd.ExcelWriter(self.fm.localAnalysisStatesDir + 'SingleNucDataSummary.xlsx')
        self.total_df.to_excel(writer, 'Total')
        self.cluster_detail_df.to_excel(writer, 'Cluster_Detail')
        self.depth_detail_df.to_excel(writer, 'Depth_Detail')
        writer.save()

    def generate_individual_plots(self):
        for pid in self.pids:
            self.sps[pid].createSinglenucFigures()


class DepthAnalyzer:
    # Contains code process depth data for figure creation

    def __init__(self, fileManager, smooth_depth=True):
        self.smooth_depth = smooth_depth
        self.fileManager = fileManager
        self.lp = self.fileManager.lp
        self._loadData()
        self.goodPixels = (self.tray_r[2] - self.tray_r[0]) * (self.tray_r[3] - self.tray_r[1])

    def _loadData(self):
        # Loads depth tray information and smoothedDepthData from files that have already been downloaded

        # If tray attribute already exists, exit
        try:
            self.tray_r
        except AttributeError:
            with open(self.fileManager.localTrayFile) as f:
                line = next(f)
                tray = line.rstrip().split(',')
                self.tray_r = [int(x) for x in tray]
        if self.smooth_depth:
            try:
                self.depth_data
            except AttributeError:
                self.depth_data = np.load(self.fileManager.localSmoothDepthFile)
                self.depth_data[:, :self.tray_r[0], :] = np.nan
                self.depth_data[:, self.tray_r[2]:, :] = np.nan
                self.depth_data[:, :, :self.tray_r[1]] = np.nan
                self.depth_data[:, :, self.tray_r[3]:] = np.nan
        else:
            try:
                self.depth_data
            except AttributeError:
                self.depth_data = np.load(self.fileManager.localInterpDepthFile)
                self.depth_data[:, :self.tray_r[0], :] = np.nan
                self.depth_data[:, self.tray_r[2]:, :] = np.nan
                self.depth_data[:, :, :self.tray_r[1]] = np.nan
                self.depth_data[:, :, self.tray_r[3]:] = np.nan
            except FileNotFoundError:
                self.depth_data = None


    def t_to_index(self, t):
        try:
            index = max([False if x.time <= t else True for x in self.lp.frames].index(True) - 1, 0)
        except ValueError:
            if t > self.lp.frames[-1].time:
                index = len(self.lp.frames) - 1
            else:
                index = 0
        return index

    def clip_data(self, t0, t1):
        # clips the data and log parser to a particular time range. Useful for reducing the size of
        # the DepthAnalyzer when generating multiple DepthAnalyzer objects
        self._checkTimes(t0, t1)
        i0, i1 = (self.t_to_index(t) for t in [t0, t1])
        self.depth_data = self.depth_data[i0:i1 + 1]
        self.lp.frames = self.lp.frames[i0:i1+1]

    def returnBowerLocations(self, t0, t1, cropped=True, force_window=False):
        # Returns 2D numpy array using thresholding and minimum size data to identify bowers
        # Pits = -1, Castle = 1, No bower = 0

        # Check times are good
        self._checkTimes(t0, t1)

        # Identify total height change and time change
        totalHeightChange = self.returnHeightChange(t0, t1, masked=False, cropped=cropped, force_window=force_window)
        timeChange = t1 - t0

        # Determine threshold and minimum size of bower to use based upon timeChange
        if timeChange.total_seconds() < 7300:  # 2 hours or less
            totalThreshold = self.fileManager.hourlyDepthThreshold
            minPixels = self.fileManager.hourlyMinPixels
        elif timeChange.total_seconds() < 129600:  # 2 hours to 1.5 days
            totalThreshold = self.fileManager.dailyDepthThreshold
            minPixels = self.fileManager.dailyMinPixels
        else:  # 1.5 days or more
            totalThreshold = self.fileManager.totalDepthThreshold
            minPixels = self.fileManager.totalMinPixels

        tCastle = np.where(totalHeightChange >= totalThreshold, True, False)
        tCastle = morphology.remove_small_objects(tCastle, minPixels).astype(int)

        tPit = np.where(totalHeightChange <= -1 * totalThreshold, True, False)
        tPit = morphology.remove_small_objects(tPit, minPixels).astype(int)

        bowers = tCastle - tPit

        return bowers

    def returnHeight(self, t, cropped=True):
        # return the frame from the smoothedDepthData numpy closest to time t. If cropped is True, crop the frame
        # to include only the area defined by tray_r

        # Check times are good
        self._checkTimes(t)

        # Find closest frames to desired times
        try:
            first_index = max([False if x.time <= t else True for x in self.lp.frames].index(True) - 1,
                              0)  # This ensures that we get overnight changes when kinect wasn't running
        except ValueError:
            if t > self.lp.frames[-1].time:
                first_index = -1
            else:
                first_index = 0

        change = self.depth_data[first_index]

        if cropped:
            change = change[self.tray_r[0]:self.tray_r[2], self.tray_r[1]:self.tray_r[3]]

        return change

    def returnHeightChange(self, t0, t1, masked=False, cropped=True, force_window=False):
        # return the height change, based on the smoothedDepthData numpy, from the frame closest to t0 to the frame
        # closest to t1. If cropped is True, crop the frame to include only the area defined by tray_r. If masked is
        # True, set the pixel value in all non-bower regions (see returnBowerLocations) to 0

        # Check times are good
        self._checkTimes(t0, t1)

        # Find closest frames to desired times
        try:
            first_index = max([False if x.time <= t0 else True for x in self.lp.frames].index(True) - 1,
                              0)  # This ensures that we get overnight changes when kinect wasn't running
        except ValueError:
            if t0 > self.lp.frames[-1].time:
                first_index = -1
            else:
                first_index = 0
        if force_window:
            while self.lp.frames[first_index].time < t0:
                first_index += 1

        try:
            last_index = max([False if x.time <= t1 else True for x in self.lp.frames].index(True) - 1, 0)
        except ValueError:
            last_index = len(self.lp.frames) - 1

        change = self.depth_data[first_index] - self.depth_data[last_index]

        if cropped:
            change = change[self.tray_r[0]:self.tray_r[2], self.tray_r[1]:self.tray_r[3]]

        if masked:
            change[self.returnBowerLocations(t0, t1, cropped=cropped) == 0] = 0



        return change

    def returnVolumeSummary(self, t0, t1):
        # calculate various summary statistics for the depth change from t0 to t1

        # Check times are good
        self._checkTimes(t0, t1)

        pixelLength = self.fileManager.pixelLength
        bowerIndex_pixels = int(self.goodPixels * self.fileManager.bowerIndexFraction)

        bowerLocations = self.returnBowerLocations(t0, t1)


        heightChange = self.returnHeightChange(t0, t1)
        heightChangeAbs = heightChange.copy()
        heightChangeAbs = np.abs(heightChangeAbs)

        outData = SimpleNamespace()
        # Get data
        outData.projectID = self.lp.projectID
        outData.depthAbsoluteVolume = np.nansum(heightChangeAbs) * pixelLength ** 2
        outData.depthSummedVolume = np.nansum(heightChange) * pixelLength ** 2
        outData.depthCastleArea = np.count_nonzero(bowerLocations == 1) * pixelLength ** 2
        outData.depthPitArea = np.count_nonzero(bowerLocations == -1) * pixelLength ** 2
        outData.depthCastleVolume = np.nansum(heightChange[bowerLocations == 1]) * pixelLength ** 2
        outData.depthPitVolume = np.nansum(heightChange[bowerLocations == -1]) * -1 * pixelLength ** 2
        outData.depthBowerVolume = outData.depthCastleVolume + outData.depthPitVolume

        flattenedData = heightChangeAbs.flatten()
        sortedData = np.sort(flattenedData[~np.isnan(flattenedData)])
        try:
            threshold = sortedData[-1 * bowerIndex_pixels]
        except IndexError:
            pdb.set_trace()
        outData.thresholdCastleVolume = np.nansum(heightChangeAbs[(bowerLocations == 1) & (heightChangeAbs > threshold)])
        outData.thresholdPitVolume = np.nansum(heightChangeAbs[(bowerLocations == -1) & (heightChangeAbs > threshold)])

        outData.depthBowerIndex = (outData.thresholdCastleVolume - outData.thresholdPitVolume) / (outData.thresholdCastleVolume + outData.thresholdPitVolume)

        return outData

    def _checkTimes(self, t0, t1=None):
        # validate the given times
        if t1 is None:
            if type(t0) != datetime.datetime:
                try:
                    t0 = t0.to_pydatetime()
                except AttributeError:
                    raise Exception('Timepoints to must be datetime.datetime objects')
            return
        # Make sure times are appropriate datetime objects
        if type(t0) != datetime.datetime or type(t1) != datetime.datetime:
            try:
                t0 = t0.to_pydatetime()
                t1 = t1.to_pydatetime()
            except AttributeError:
                raise Exception('Timepoints to must be datetime.datetime objects')
        if t0 > t1:
            print('Warning: Second timepoint ' + str(t1) + ' is earlier than first timepoint ' + str(t0),
                  file=sys.stderr)


class ClusterAnalyzer:
    # Contains code process cluster data for figure creation
    def __init__(self, fileManager):
        self.fileManager = fileManager
        self.bids = ['c', 'p', 'b', 'f', 't', 'm', 's', 'd', 'o', 'x']
        self.bid_labels = {'c':'bower scoop', 'p': 'bower spit', 'b': 'bower multiple',
                           'f': 'feed scoop', 't': 'feed spit', 'm': 'feed multiple',
                           's': 'spawn', 'd': 'drop sand', 'o': 'fish other', 'x': 'no fish other'}
        self.lp = self.fileManager.lp
        self._loadData()

    def _loadData(self):
        # load the required data

        self.transM = np.load(self.fileManager.localTransMFile)
        self.clusterData = pd.read_csv(self.fileManager.localAllLabeledClustersFile, index_col='TimeStamp',
                                       parse_dates=True, infer_datetime_format=True)
        self._appendDepthCoordinates()
        with open(self.fileManager.localTrayFile) as f:
            line = next(f)
            tray = line.rstrip().split(',')
            self.tray_r = [int(x) for x in tray]
            if self.tray_r[0] > self.tray_r[2]:
                self.tray_r = [self.tray_r[2], self.tray_r[1], self.tray_r[0], self.tray_r[3]]
            if self.tray_r[1] > self.tray_r[3]:
                self.tray_r = [self.tray_r[0], self.tray_r[3], self.tray_r[2], self.tray_r[1]]

        self.cropped_dims = [self.tray_r[2] - self.tray_r[0], self.tray_r[3] - self.tray_r[1]]
        self.goodPixels = (self.tray_r[2] - self.tray_r[0]) * (self.tray_r[3] - self.tray_r[1])

    def _appendDepthCoordinates(self):
        # adds columns containing X and Y in depth coordinates to all cluster csv
        self.clusterData['Y_depth'] = self.clusterData.apply(
            lambda row: (self.transM[0][0] * row.Y + self.transM[0][1] * row.X + self.transM[0][2]) / (
                    self.transM[2][0] * row.Y + self.transM[2][1] * row.X + self.transM[2][2]), axis=1)
        self.clusterData['X_depth'] = self.clusterData.apply(
            lambda row: (self.transM[1][0] * row.Y + self.transM[1][1] * row.X + self.transM[1][2]) / (
                    self.transM[2][0] * row.Y + self.transM[2][1] * row.X + self.transM[2][2]), axis=1)
        scaling_factor = sqrt(np.linalg.det(self.transM))
        self.clusterData['approx_radius'] = self.clusterData.apply(
            lambda row: (np.mean(row.X_span + row.Y_span) * scaling_factor)/2, axis=1)
        # self.clusterData.round({'X_Depth': 0, 'Y_Depth': 0})

        self.clusterData.to_csv(self.fileManager.localAllLabeledClustersFile)

    def sliceDataframe(self, t0=None, t1=None, bid=None, columns=None, input_frame=None, cropped=True):
        # utility function to access specific slices of the Dataframe based on the AllClusterData csv.
        #
        # t0: return only rows with timestamps after t0
        # t1: return only rows with timestamps before t1
        # bid: string or list of strings: return only rows for which the behavioral id matches the given string(s)
        # columns: list of strings: return only the columns of data matching the given keys
        # input_frame: pd.DataFrame: dataframe to slice from, instead of the default full dataframe.
        #              Allows for iterative slicing
        # cropped: If True, return only rows corresponding to events that occur within the area defined by tray_r

        df_slice = self.clusterData if input_frame is None else input_frame
        df_slice = df_slice.dropna(subset=['Prediction']).sort_index()
        if t0 is not None:
            self._checkTimes(t0, t1)
            df_slice = df_slice[t0:t1]
        if bid is not None:
            df_slice = df_slice[df_slice.Prediction.isin(bid if type(bid) is list else [bid])]
        if cropped:
            df_slice = df_slice[(df_slice.X_depth > self.tray_r[0]) & (df_slice.X_depth < self.tray_r[2]) &
                                (df_slice.Y_depth > self.tray_r[1]) & (df_slice.Y_depth < self.tray_r[3])]
            df_slice.X_depth = df_slice.X_depth - self.tray_r[0]
            df_slice.Y_depth = df_slice.Y_depth - self.tray_r[1]
        if columns is not None:
            df_slice = df_slice[columns]
        return df_slice

    def returnClusterCounts(self, t0, t1, bid='all', cropped=True):
        # return the number of behavioral events for a given behavior id (bid), or all bids, between t0 and t1
        #
        # t0: beginning of desired time frame
        # t1: end of desired time frame
        # bid: string or 'all': bid that will be counted. if a single bid is given, return counts (as an int) for that
        #      bid only. If 'all' (default behavior) return a dict of counts for all bids, keyed by bid.
        # cropped: If True, count only events occuring within the area defined by tray_r
        self._checkTimes(t0, t1)
        if bid == 'all':
            df_slice = self.sliceDataframe(t0=t0, t1=t1, cropped=cropped)
            row = df_slice.Prediction.value_counts().to_dict
            return row
        else:
            df_slice = self.sliceDataframe(t0=t0, t1=t1, bid=bid, cropped=cropped)
            cell = df_slice.Prediction.count()
            return cell

    def returnClusterKDE(self, t0, t1, bid, cropped=True, bandwidth=None):
        # Geneate a kernel density estimate corresponding to the number events per cm^2 over a given timeframe for
        # a particular behavior id (bid)
        #
        # t0: beginning of time frame
        # t1: end of time frame
        # bid: string: generate a kde for this bid
        # cropped: if True, only include events within the area defined by tray_r
        # bandwidth: Can be used to manually set the kde bandwith (see sklearn.neighbors.KernelDensity). By default,
        #            use a bandwidth based on the average approximate event radius (see _appendDepthCoordinates)
        if bandwidth is None:
            bandwidth = self.sliceDataframe(t0, t1, bid, 'approx_radius').mean()/2
        df_slice = self.sliceDataframe(t0=t0, t1=t1, bid=bid, cropped=cropped, columns=['X_depth', 'Y_depth'])
        n_events = len(df_slice.index)
        x_bins = int(self.tray_r[2] - self.tray_r[0])
        y_bins = int(self.tray_r[3] - self.tray_r[1])
        xx, yy = np.mgrid[0:x_bins, 0:y_bins]
        if n_events == 0:
            z = np.zeros_like(xx)
        else:
            xy_sample = np.vstack([xx.ravel(), yy.ravel()]).T
            xy_train = df_slice.to_numpy()
            kde = KernelDensity(bandwidth=bandwidth, kernel='gaussian').fit(xy_train)
            z = np.exp(kde.score_samples(xy_sample)).reshape(xx.shape)
            z = (z * n_events) / (z.sum() * (self.fileManager.pixelLength ** 2))
        return z

    def returnBowerLocations(self, t0, t1, cropped=True, bandwidth=None):
        # Returns 2D numpy array using thresholding and minimum size data to identify bowers based on KDEs of spit and
        # scoop densities. Pits = -1, Castle = 1, No bower = 0
        #
        # t0: beginning of time frame
        # t1: end of time frame
        # cropped: if True, include in bower calculation only events within the area defined by tray_r
        # bandwith: see returnClusterKDE

        self._checkTimes(t0, t1)
        timeChange = t1 - t0

        if timeChange.total_seconds() < 7300:  # 2 hours or less
            totalThreshold = self.fileManager.hourlyClusterThreshold
            minPixels = self.fileManager.hourlyMinPixels
        elif timeChange.total_seconds() < 129600:  # 2 hours to 1.5 days
            totalThreshold = self.fileManager.dailyClusterThreshold
            minPixels = self.fileManager.dailyMinPixels
        else:  # 1.5 days or more
            totalThreshold = self.fileManager.totalClusterThreshold
            minPixels = self.fileManager.totalMinPixels

        z_scoop = self.returnClusterKDE(t0, t1, 'c', cropped=cropped, bandwidth=bandwidth)
        z_spit = self.returnClusterKDE(t0, t1, 'p', cropped=cropped, bandwidth=bandwidth)

        scoop_binary = np.where(z_spit - z_scoop <= -1 * totalThreshold, True, False)
        scoop_binary = morphology.remove_small_objects(scoop_binary, minPixels).astype(int)

        spit_binary = np.where(z_spit - z_scoop >= totalThreshold, True, False)
        spit_binary = morphology.remove_small_objects(spit_binary, minPixels).astype(int)

        bowers = spit_binary - scoop_binary
        return bowers

    def returnClusterSummary(self, t0, t1):
        # calculate various summary statistics for the scoop and spit KDEs from t0 to t1
        self._checkTimes(t0, t1)
        pixelLength = self.fileManager.pixelLength
        bowerIndex_pixels = int(self.goodPixels * self.fileManager.bowerIndexFraction)
        bowerLocations = self.returnBowerLocations(t0, t1)
        clusterKde = self.returnClusterKDE(t0, t1, 'p') - self.returnClusterKDE(t0, t1, 'c')
        clusterKdeAbs = clusterKde.copy()
        clusterKdeAbs = np.abs(clusterKdeAbs)

        outData = SimpleNamespace()
        # Get data
        outData.projectID = self.lp.projectID
        outData.kdeAbsoluteVolume = np.nansum(clusterKdeAbs) * pixelLength ** 2
        outData.kdeSummedVolume = np.nansum(clusterKde) * pixelLength ** 2
        outData.kdeCastleArea = np.count_nonzero(bowerLocations == 1) * pixelLength ** 2
        outData.kdePitArea = np.count_nonzero(bowerLocations == -1) * pixelLength ** 2
        outData.kdeCastleVolume = np.nansum(clusterKde[bowerLocations == 1]) * pixelLength ** 2
        outData.kdePitVolume = np.nansum(clusterKde[bowerLocations == -1]) * -1 * pixelLength ** 2
        outData.kdeBowerVolume = outData.kdeCastleVolume + outData.kdePitVolume

        flattenedData = clusterKdeAbs.flatten()
        sortedData = np.sort(flattenedData[~np.isnan(flattenedData)])
        try:
            threshold = sortedData[-1 * bowerIndex_pixels]
        except IndexError:
            threshold = 0
        thresholdCastleKdeVolume = np.nansum(clusterKdeAbs[(bowerLocations == 1) & (clusterKdeAbs > threshold)])
        thresholdPitKdeVolume = np.nansum(clusterKdeAbs[(bowerLocations == -1) & (clusterKdeAbs > threshold)])

        outData.kdeBowerIndex = (thresholdCastleKdeVolume - thresholdPitKdeVolume) / (thresholdCastleKdeVolume + thresholdPitKdeVolume)

        return outData

    def _checkTimes(self, t0, t1=None):
        # validate the given times
        if t1 is None:
            if type(t0) != datetime.datetime:
                try:
                    t0 = t0.to_pydatetime()
                except AttributeError:
                    raise Exception('Timepoints to must be datetime.datetime objects')
            return
        # Make sure times are appropriate datetime objects
        if type(t0) != datetime.datetime or type(t1) != datetime.datetime:
            try:
                t0 = t0.to_pydatetime()
                t1 = t1.to_pydatetime()
            except AttributeError:
                raise Exception('Timepoints to must be datetime.datetime objects')
        if t0 > t1:
            print('Warning: Second timepoint ' + str(t1) + ' is earlier than first timepoint ' + str(t0),
                  file=sys.stderr)

