# Calibrate the TIMS device


## Aim
Calibrating a TIMS device in timsControl.


## Materials

### Software
timsControl 6.0


## Procedure
Timing: 1.5 minutes

1. Verified that dia-PASEF method had an ion mobility range that matched the ion mobility range of the method intended to be used in the proteomics study: ion mobility range from 0.7 to 1.3 1/K₀. Hence the 1/K₀ start and end values were set to 0.7 and 1.3, respectively.

2. Activated the locked sign at 1/K₀ end.

3. Adjusted the 1/K₀ start from 0.7 to 0.85. This altered the ion mobility range from 0.7-1.3 1/K₀ to 0.85-1.45 1/K₀.

4. Waited until the TIC in Chromatogram View was stable. This took approximately 1 minute.

5. Switched the scan mode to 'MS', set MS averaging to 30 and kept the polygon heatmap deactivated .

6. In timsControl, navigated to 'calibration', then 'mobility'.

6. Verified that the reference list '[ESI] Tuning Mix ES-TOF (ESI)' is selected that contains the calibrant masses 622, 922, 1221.

7. Verified the linear mode and 5% as detection range and ±0.1 Da as width.

8. Proceeded by selecting 'calibrate'.

9. To verify that the calibrants had been picked correctly at the center, clicked on them in the reference list.

10. No adjustments by clicking on the peak in the TIMS view window were necessary.

11. When the score reached 100%, pressed accept.

12. [Cursor clicks not on video: Tried to save the method] and said "Discard all changes".

13. Set MS averaging back to 1.


## Results
- The score in the tab "Calibration" was at 100%
