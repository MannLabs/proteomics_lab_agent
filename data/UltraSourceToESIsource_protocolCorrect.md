# Change source: UltraSource to ESI source


## Abstract
This protocol describes the procedure for switching from the UltraSource to the ESI source.


## Materials

### Equipment
- timsTOF Ultra Mass Spectrometer: 
  - Equipped with an UltraSource ion source
  - ESI source on the side to attach


## Procedure
**Estimated timing: less than 10 minute**

### Switch TimsControl to 'Standby' mode
1. Verify that the IonOpticks column from an Evosep System is disconnected. If not disconnect them.
   Critical step: This could be an opportune moment to perform the weekly LC system maintenance. 
2. In timsControl, verfy that the software is in standby mode
3. Navigate to the 'Source', then proceed to 'SourceType' and select 'ESI'. However, do not activate the source at this moment (Figure 1). 

### Remove UltraSource
4. Disconnect the power supply of the oven. 
5. Disconnect the filter tubing. 
6. Rotate the top right and bottom left handles of the UltraSource housing by 180 degrees. 
7. Slide off the UltraSource housing from both the source door and the glass capillary.
8. Set the UltraSource housing on the bench. 
   Critical step: Never attempt to open the source door while the UltraSource is connected with the glass capillary (Figure 2 H). Such an action will cause breakage of the glass capillary.
9. Remove the source door by opening it and unhinging it, similar to the motion of a normal door. 
10. Set it aside (Figure 2 H).

### Mount Apollo ESI source
11. Put on gloves.
12. Attach the capillary cap securely to the glass capillary (G in Figure 3) and the spray shield (E) to the desolvation stage housing. 
    Critical step: Try not to block the vacuum flow to avoid contamination of the timsTOF for instance by blocking the whole of the capillary cap. 
13. Hinging the ESI source (F) into position as it would be a door and close it. 
14. Connect the sample inlet (B) of the ESI source and the peak tubing lines, which originate from the syringe, by turning it clock-wise. 
15. Connect the nebulizer gas inlet (C) to the N₂ line. 

### Prepare the setup by loading the syringe with Tuning Mix
16. Remove old solvent. 
17. Withdraw new Tuning Mix liquid. 
18. Ensure it is devoid of air bubbles. 
19. Connect the syringe to the peak tubing of the sample line. 
20. Mount this syringe within the external syringe pump setup. The golden button allows to move the syringe holder to arrange the syringe as in Figure 3. 
21. Press some solved out of the syringe to fill the sample line.

### Switch TimsControl to 'Operate' mode
22. Activate the ESI source within the TimsControl software (Figure 1). 
23. Transition the instrument into 'operate' mode by clicking on the on/off symbol.
24. Begin flow at the syringe, ensuring that the following settings are in place in the tab 'Source' (Figure 1): Syringe: Hamilton 500 µL; Flow Rate: 3 µL/min. Press start. Keep the button next to start/stop pressed until a signal is observed in the 'Chromatogram View' and 'TIMS View' windows, which usually happens within 30 seconds.

## Expected Results
- Signal intensity should reach approximately 1.5x10^7
- Stable signal in in timsControl (in the windows for Mobilogram (timsView) and mass spectrum)

## Figures
Figure 1: TimsControl settings before changing source

Figure 2: UltraSource.

Figure 3: Apollo ESI source and gas flow pressure control wheels.

## References
1. Skowronek, P., Wallmann, G., Wahle, M. et al. An accessible workflow for high-sensitivity proteomics using parallel accumulation–serial fragmentation (PASEF). Nat Protoc (2025). https://doi.org/10.1038/s41596-024-01104-w 
2. TODO: timsTOF user manual