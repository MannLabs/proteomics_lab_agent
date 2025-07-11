# Change source: ESI source to UltraSource


## Abstract
This protocol describes the procedure for switching from the ESI source to UltraSource.


## Materials

### Equipment
- timsTOF Ultra Mass Spectrometer:
  - Equipped with an ESI ion source
  - UltraSource ion source ready to attach
- IonOpticks Column
- Evosep One LC System with sample line
- NanoViper Adapter (black)
- Pliers


## Procedure
*Estimated timing: less than 10 minute*

### Switch timsTOF to standby
1. In timsControl, verfy if the instrument is in standing by mode. If not press the on/off button to switch from operate mode to standy by mode  (Figure 1).
2. Verify that the syringe is inactive in the tab 'Source' under 'Syringe Pump'. If not click on 'Stop'.
3. In the 'source' and 'source type' sections of timsControl, choose 'CaptiveSpray' but do not activate it yet.

### Remove ESI source
4. At the instrument, disconnect the peak connector of the sample tubing (Figure 2).
5. Disconnect the nebulizer N₂ line.
6. Remove the ESI source housing by hinging it out like a regular door.
7. Put on laboratory gloves.
8. Remove the spray shield
   ! CAUTION: The spray shield is hot.
9. Remove the capillary cap.
   ! CAUTION: The capillary cap is hot.
10. Inspect the capillary position. If it appears to be partially pulled out, gently push it back into proper position without blocking the gas flow.

### Mount UltraSource
11. Hinge the UltraSource door in and close it (Figure 3).
12. Slide the UltraSource housing onto the source door and secure it by flipping the handles located at the top right and bottom left by 180°.
13. Connect the filter tubing to the source.

### Connect column and sample line
14. Verify that an IonOpticks column is already inserted into the UltraSource of the timsTOF Ultra.
15. Verify if the LC sample line has a black NanoViper adapter attached. If not, locate an adapter and securely attach it to the sample line.
16. Remove any access liquid at the top of the nanoViper of the sample line for instance by snipping it off.
17. Hold the column fititng of the IonOpticks column with a pliers.
18. Hand-tighten the NanoViper of the LC sample line with the column fitting (Figure 3).
   CRITICAL STEP: Be careful not to overtighten the connection between the IonOpticks column and the timsTOF Ultra. Otherwise you can damage the column and the LC sample line.
19. Draw the oven closer to the UltraSource, secure it with the screw on the bottom of the oven (Figure 2).
20. Remove the NanoViper adapter so that the oven can be tightly closed.
21. Lift and place the metal grounding screw at the column-sample line connection to establish proper ESI spray grounding with the column oven.
22. Close the lid of the oven.
23. Connect the oven to the electrical power supply.
24. Set the temperature at 50°C for IonOpticks columns, as indicated by three illuminated LEDs on the column oven. Blincking light indicates that the oven is heating up.
    CRITICAL STEP: Ensure that the IonOpticks column is not left connected to the LC for an extended period unless the mass spectrometer is in operate mode; otherwise, debris may accumulate on the emitter, lead to spitting.

### Switch timsTOF to operate and idle flow
25. In timsCOntrol, activate the CaptiveSpray function in timsControl (Figure 1)
26. Transition the instrument to the operation mode by using the on/off button.
27. Navigate to Hystar and ensure that the idle flow is active. If not right-click on the Evosep logo, choosing 'preparation', and then selecting 'idle flow' and 'Run'.
28. Return to timsControl and check the MS signal. It should be around 2.5x10^7.
29. Monitor the internal pressures in the timsTOF device. The funnel pressur is acceptable within a 9-11 mbar range. Aim for a 10 mbar funnel pressure. Adjust the 'funnel pressure' wheel if necessary by turning counter clock-wise to reduce the pressure.


## Expected Results
- In timsControl, signal intensity should be above 10^7
- Stable signal in timsControl (in the windows for Mobilogram (timsView) and mass spectrum)


## Figures
**Figure 1: TimsControl settings before changing source.**

**Figure 2: Apollo ESI source and gas flow pressure control wheels.**

**Figure 3: UltraSource.**


## References
1. Skowronek, P., Wallmann, G., Wahle, M. et al. An accessible workflow for high-sensitivity proteomics using parallel accumulation–serial fragmentation (PASEF). Nat Protoc (2025). https://doi.org/10.1038/s41596-024-01104-w
2. timsTOF user manual
