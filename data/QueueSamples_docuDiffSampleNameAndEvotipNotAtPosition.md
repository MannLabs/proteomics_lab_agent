# Queue and measure samples in HyStar


## Aim
Queuing samples in HyStar for LC-MS measurement.


## Materials

### Software
HyStar 6.0


## Procedure
Timing: 2 minutes

Prerequisite 1. Placed HeLa Evotips at S1 from A1 to A6 and blanks at S3 from A1 to A6.

Prerequisite 2. Calibrated the TIMS device in TimsControl.

1. In Hystar, navigated to the 'Acquisition' tab.

2. Chose an already existing sample table by pressing the arrow down button when hovering over the sample table name in the left sample table column.

3. Copied already existing sample table entries to modify them.

4. Adjusted the sample ID so that it followed this pattern: currentDate_massSpec_user_sampleType_projectID_sampleName.

5. For measuring a study, queued one blank, two dia-PASEF runs. **Error** No blank queued for the end of the queue.

6. **Omitted** Verified the column autocompletion settings by right-clicking on a field in the column 'vial' and selected 'Configure'. Values were set to autocomplete from A1-A12 indicated by arrows pointing to right. Ensured that the tray type was set to 'Evosep' and slots 1-6 were designated as '96Evotip'. Pressed 'OK'.

7. Matched the Evotip position with the sample's location in the Evotip box. To do this, pressed the arrow next to the value in the 'vial' column. Specified Evotip positions individually. 
**Error** 6

8. Verified 'path' folder for storing the raw files.

9. Verified separation method.

10. Verified that injection method is set to 'standard'.

11. At 'MS method', adjusted dda-PASEF and dia-PASEF maintenance methods according to sample ID.

12. **Omitted** Stopped the idle flow on the Evosep by right-clicking on the Evosep logo and selecting 'Cancel maintenance procedure'.

13. Saved the sample table.

14. Right-clicked on the top row of the freshly defined sample table entries and selected 'upload sample conditions' to pre-check if all LC and MS methods could be loaded correctly. The status changed to loaded.

15. Pressed 'start' and 'start sequence'.


## Results
Chromatogram is not shown in video.