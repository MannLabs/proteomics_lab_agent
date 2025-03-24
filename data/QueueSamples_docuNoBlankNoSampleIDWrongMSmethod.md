# Queue and measure samples in HyStar


## Aim
Queuing samples in HyStar for LC-MS measurement.


## Materials

### Software
HyStar 6.0


## Procedure
Timing: 2 minutes

Prerequisite 1. Placed 5 ng HeLa Evotips at S1 from A1 to A6 and at S3 from A1 to A6.

Prerequisite 2. Calibrated the TIMS device in TimsControl.

1. In Hystar, navigated to the 'Acquisition' tab.

2. Chose an already existing sample table by pressing the arrow down button when hovering over the sample table name in the left sample table column.

3. Copied already existing sample table entries to modify them.

5. For performance evaluation of the LC-MS system, queued three dda-PASEF runs, three dia-PASEF runs.
**Error** Did not queue a blank at the start and end of queue.

6. Verified the column autocompletion settings by right-clicking on a field in the column 'vial' and selected 'Configure'. Values were set to autocomplete from A1-A12 indicated by arrows pointing to right. Ensured that the tray type was set to 'Evosep' and slots 1-6 were designated as '96Evotip'. Pressed 'OK'.

7. Matched the Evotip position with the sample's location in the Evotip box. To do this, pressed the arrow next to the value in the 'vial' column. Selected the position where the first sample Evotip was placed (S1 A1). Then automatically specified all remaining positions by dragging the values (similar to Excel's auto-fill function).

11. At 'MS method', set dda-PASEF maintenance method for all samples.
**Error** Last three samples would have to be linked to a dia-PASEF maintenance method.

4. Adjusted the sample ID so that it followed this pattern: currentDate_massSpec_user_sampleType_projectID_sampleName.
**Error** Missed to include projectID.

8. Verified 'path' folder for storing the raw files.

9. Verified separation method.

10. Verified that injection method is set to 'standard'.

13. Saved the sample table.

12. Stopped the idle flow on the Evosep by right-clicking on the Evosep logo and selecting 'Cancel maintenance procedure'.

14. **Omitted** Right-clicked on the top row of the freshly defined sample table entries and selected 'upload sample conditions' to pre-check if all LC and MS methods could be loaded correctly. The status changed to loaded.

15. Pressed 'start' and 'start sequence'.


## Results
Chromatogram is not shown in video.
