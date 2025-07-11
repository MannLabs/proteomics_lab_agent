# Calibrate the TIMS device


## Abstract
This protocol explains how to calibrate a TIMS device in timsControl.
Important: We recommend to calibrate the TIMS device each time before a sample queue is started.


## Materials

### Software
| Software | Version | Purpose | Source/Link |
|----------|---------|---------|------------|
| timsControl | 6.0 (latest) | Software to control timsTof mass spectrometers | Available on every instrument computer |


## Procedure
*Estimated timing: 3 minutes*

Critical step: If the instrument has been operated with another source than the UltraSource or CaptiveSpray source, it is highly recommended to wait for 3 hours before initiating the TIMS calibration process. This waiting period permits the temperature and pressure to stabilise, thus ensuring a steady TIMS calibration.
1. Use timsControl to load a performance evaluation method - for instance a dda-PASEF or dia-PASEF method. The method should have an ion mobility range that matches the ion mobility range of the method intended to be use in the study. For proteomics experiments, we typically use an ion mobility range from 0.7 to 1.3 1/K₀, hence the 1/K₀ start and end values can be set to 0.7 and 1.3, respectively (Figure 1: 6, 7). This consistency in ion mobility range allows for the integration of quality control (QC) runs into the sample table as reference points without necessitating recalibration of the TIMS tunnel.
2. To specifically calibrate a narrow ion mobility range, activate the locked sign at 1/K₀ end (Figure 1: 7).
3. Adjust the 1/K₀ start from 0.7 to 0.85. This alters the ion mobility range from 0.7-1.3 1/K₀ to 0.85-1.45 1/K₀. The aim here is to shift the ion mobility range without modifying the interval, enabling all three calibrants to be used for linear calibration while maintaining a constant TIMS potential.
4. Wait until the TIC in Chromatogram View is stable. This can take up to 15 minutes.
5. Switch the scan mode to 'MS', set MS averaging to 30 and deactivate the polygon heatmap (Figure 1: 4, 9, 14).
6. In timsControl, navigate to 'calibration', then 'mobility'.
7. **Not included in video** From reference lists, select the list '[ESI] Tuning Mix ES-TOF (ESI)' that contains the calibrant masses 622, 922, 1221.
8. Specify the linear mode and 5% as detection range and ±0.1 Da as width (Figure 2).
9. Proceed by selecting 'calibrate' (Figure 2).
10. To verify that the calibrants have been picked correctly at the center, click on them in the reference list.
11. If they are not picked in the center, make adjustments by clicking on the peak in the TIMS view window.
12. If the score is at 100%, press accept.
13. Select "Method" > "Load Recent", select the same method, and then click "Discard changes" in the pop-up window.
14. Set MS averaging to 1.


## Expected Results
- The score in the tab "Calibration" should be at 100%


## Figures
### Figure 1: TimsControl settings

### Figure 2: Ion mobility calibration

## Tables
Table 1: Gas Flow Parameters for UltraSource

| Instrument Type | Calibrant 922 Voltage [V] |
|----------------|---------------------------|
| timsTOF Pro, SCP | 160 |
| timsTOF HT, Ultra | 200 |

## References
1. Skowronek, P., Wallmann, G., Wahle, M. et al. An accessible workflow for high-sensitivity proteomics using parallel accumulation–serial fragmentation (PASEF). Nat Protoc (2025). https://doi.org/10.1038/s41596-024-01104-w
2. TODO: Refer to user manual of timsTof
3. TODO: Maybe upload video which shows calibration in action
