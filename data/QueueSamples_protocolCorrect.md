# Queue and measure samples in HyStar


## Abstract
This protocol explains how to queue sample in HyStar for LC-MS measurement.


## Materials

### Software

| Software | Version | Purpose | Source/Link |
|----------|---------|---------|------------|
| HyStar | 6.0 | Controls LC and MS | On every instrument computer |


## Procedure
Estimated timing: 6 minutes

Prerequisite 1. Prepare samples for analysis by loading them onto Evotips. Place these Evotips in Evotip boxes on top of the Evosep LC system and note down their position in these boxes. In this example, 5 ng HeLa Evotips were placed at S1 from A1 to A6 and blanks at S3 from A1 to A6.
   Critical step: Blank Evotis can be unused and dry Evotips.

Prerequisite 2. Calibrate the TIMS device in TimsControl. The TIMS device should be calibrated each time before you start a sample queue.

1. In Hystar, navigate to the 'Acquisition' tab.

2. Either select 'New', and subsequently choose 'LC-MS sample table' (Figure 1) to generate a new sample table or choose an already existing sample table by pressing the arrow down button when hovering over the sample table name in the left sample table column.

3. In both cases, copy already existing sample table entries to modify them.

4. Adjust the sample ID so that it follows this pattern: currentDate_massSpec_user_sampleType_projectID_ sampleName. Typical examples for sampleType: "SA_blank", "MA_HeLa", "DIAMA_HeLa".

5. For performance evaluation of the LC-MS system, we recommend to queue one blank, three dda-PASEF runs, three dia-PASEF runs and ending with another blank.
    Critical step: Always start the queue with a sacrificial Evotip such as a blank tip as the first run might have altered chromatographic conditions that could introduce technical errors to your measurements.

6. Verify the column autocompletion settings with right-click on a field in the column 'vial' such as S1-A1 in Figure 1 and select 'Configure'. The arrows allow one to define the direction in which the vial positions on the 96-well are autocompleted when dragging values similar to Excel in the sample table. Decide whether the values should increase from A1-A12 indicated by arrows pointing to right. Ensure that the tray type is set to 'Evosep' and slots 1-6 are designated as '96Evotip'. Press 'OK'.

7. Match the Evotip position with the sample's location in the Evotip box. To do this, press the arrow next to the value in the 'vial' column (Figure 1). Select the position where the first Evotip is placed, for instance S1 A1. You can then either specify all remaining positions automatically by dragging the values (similar to Excel's auto-fill function) or specify each position individually.

8. Specify a 'path' folder for storing the raw files.

9. Choose an existing separation method or create a new one. To create a new separation method, right-click on the separation method field, select 'new method' followed by 'edit method'. Choose the method type listed under 'name' and then press 'OK'. Specify its name and save it.

10. Set the injection method to 'standard'.

11. At 'MS method', load either dda-PASEF and dia-PASEF maintenance methods to check the LC-MS performance or the method intended to be used for measuring the study.

12. Stop the idle flow on the Evosep by right-clicking on the Evosep logo and selecting 'Cancel maintenance procedure'.

13. Save the sample table.

14. Right-click somewhere on the top row of the freshly defined sample table entries and select 'upload sample conditions' to pre-check if all LC and MS method can be loaded correctly. The status should be change to loaded.

15. Press 'start' and 'start sequence'.


## Expected Results
Typical chromatogram shape with MS TIC (green line) increasing drastically around 4 minutes and another increase (wash-out) at 15 minutes. Higher MS2 intensities (red line) for dia-PASEF.


## Figures

### Figure 1: Hystar
- Screenshot of reaauired Hystar settings


## References
1. Skowronek, P., Wallmann, G., Wahle, M. et al. An accessible workflow for high-sensitivity proteomics using parallel accumulation–serial fragmentation (PASEF). Nat Protoc (2025). https://doi.org/10.1038/s41596-024-01104-w
2. TODO: Refer to Hystar manual
3. TODO: Maybe upload video which shows protocol in action
