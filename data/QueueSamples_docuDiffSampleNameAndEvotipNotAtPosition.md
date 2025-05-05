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
. Adjusted the sample ID so that it followed this pattern: currentDate_massSpec_user_sampleType_projectID_sampleName.
7. ❌ **Error:** For measuring a study, queued one blank, two dia-PASEF runs, but missed to queue blank at the end of the queue.
8. ❌ **Omitted:** Missed to verify the column autocompletion settings. 
9. ❌ **Error:** Did not match the Evotip position with the sample's location in the Evotip box. 
10. Verified 'path' folder for storing the raw files.
11. Verified separation method.
12. Verified that injection method is set to 'standard'.
13. At 'MS method', adjusted dda-PASEF and dia-PASEF maintenance methods according to sample ID.
14. ❌ **Omitted:** Stopped the idle flow on the Evosep by right-clicking on the Evosep logo and selecting 'Cancel maintenance procedure'.
15. Saved the sample table.
16. Right-clicked on the top row of the freshly defined sample table entries and selected 'upload sample conditions' to pre-check if all LC and MS methods could be loaded correctly. The status changed to loaded.
17. Pressed 'start' and 'start sequence'.


## Results
Chromatogram is not shown in video.
