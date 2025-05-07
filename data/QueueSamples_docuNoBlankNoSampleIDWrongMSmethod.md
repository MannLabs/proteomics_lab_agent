# Queue and measure samples in HyStar


## Aim
Queuing samples in HyStar for LC-MS measurement.


## Materials

### Software
HyStar 6.0


## Procedure
*Timing: 2 minutes*

1. Verified that Evotips are placed on top of Evosep. 5 ng HeLa Evotips at S1 from A1 to A6 and blanks at S3 from A1 to A6.
2. Verified that the calibration of the TIMS device in TimsControl is valid.
3. In Hystar, navigated to the 'Acquisition' tab.
4. Chose an already existing sample table by pressing the arrow down button when hovering over the sample table name in the left sample table column.
5. Copied already existing sample table entries to modify them.
7. ❌ **Error:** Queued three dda-PASEF runs, three dia-PASEF runs, but missed to queue a blank at the start and end of queue as recommended.
8. Verified the column autocompletion settings by right-clicking on a field in the column 'vial' and selected 'Configure'. Values were set to autocomplete from A1-A12 indicated by arrows pointing to right. Ensured that the tray type was set to 'Evosep' and slots 1-6 were designated as '96Evotip'. Pressed 'OK'.
9. Matched the Evotip position with the sample's location in the Evotip box: S1 from A1 to A6 and blanks at S3 from A1 to A6.
13. ⚠️ **Deviation: Altered step order** & ❌ **Error:** At 'MS method', set dda-PASEF maintenance method for all samples. However, the last three samples would have to be linked to a dia-PASEF maintenance method.
6. ⚠️ **Deviation: Altered step order** & ❌ **Error:** Adjusted the sample ID so that it followed this pattern: currentDate_massSpec_user_sampleType_sampleName, but missed to include projectID.
10. Verified 'path' folder for storing the raw files.
11. Verified separation method.
12. Verified that injection method is set to 'standard'.
15. ⚠️ **Deviation: Altered step order** Saved the sample table.
14. Stopped the idle flow on the Evosep by right-clicking on the Evosep logo and selecting 'Cancel maintenance procedure'.
16. ❌ **Omitted:** Missed to right-click on the top row of the freshly defined sample table entries and select 'upload sample conditions' to pre-check if all LC and MS methods could be loaded correctly. The status did not changed to loaded.
17. Pressed 'start' and 'start sequence'.


## Results
Chromatogram is not shown in video.
