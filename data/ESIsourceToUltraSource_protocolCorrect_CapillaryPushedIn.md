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
Estimated timing: less than 10 minute

### Switch timsTOF to standby
1. Verfy if the instrument is in standing by mode. If not press the on/off button to switch from operate mode to standy by mode  (Figure 1).
2. Verify if the syringe is inactive in the tab 'Source' under 'Syringe Pump'. If not click on 'Stop'.
3. In the 'source' and 'source type' sections of timsControl, choose 'CaptiveSpray' but do not activate it yet.

### Remove ESI source
4. Disconnect the peak connector of the sample tubing (Figure 2).
5. Disconnect the nebulizer N₂ line. 
6. Remove the source door. Hinge it out like a regular door.
7. Put on laboratory gloves.
8. Remove the spray shield, and capillary cap.  
   ! CAUTION: The spray shield and capillary cap are hot.
9. Inspect the capillary position. If it appears to be partially pulled out, gently push it back into proper position without blocking the gas flow.

### Mount UltraSource
10. Hinge the UltraSource door in and close it (Figure 3). 
11. Slide the UltraSource housing onto the source door and secure it by flipping the handles located at the top right and bottom left by 180°. 
12. Connect the filter tubing to the source.

### Connect column and sample line
13. This protocol assumes that an IonOpticks column is already inserted into the UltraSource of the timsTOF Ultra. 
14. Verify if the LC sample line has a black NanoViper adapter attached. If not, locate an adapter and securely attach it to the sample line.
15. Remove any access liquid at the top of the nanoViper of the sample line for instance by snipping it off.
16. Hold the column fititng of the IonOpticks column with a pliers.
17. Hand-tighten the NanoViper of the LC sample line with the column fitting (Figure 3).
   CRITICAL STEP: Be careful not to overtighten the connection between the IonOpticks column and the timsTOF Ultra. Otherwise you can damage the column and the LC sample line.
18. Draw the oven closer to the UltraSource, secure it with the screw on the bottom of the oven (Figure 2).
19. Remove the NanoViper adapter so that the oven can be tightly closed.
20. Lift and place the metal grounding screw at the column-sample line connection to establish proper ESI spray grounding with the column oven.
21. Close the lid of the oven.
22. Connect the oven to the electrical power supply.
23. Set the temperature at 50°C for IonOpticks columns, as indicated by three illuminated LEDs on the column oven. Blincking light indicates that the oven is heating up.
    CRITICAL STEP: Ensure that the IonOpticks column is not left connected to the LC for an extended period unless the mass spectrometer is in operate mode; otherwise, debris may accumulate on the emitter, lead to spitting.

### Switch timsTOF to operate and idle flow
24. In timsCOntrol, activate the CaptiveSpray function in timsControl (Figure 1)
25. Transition the instrument to the operation mode by using the on/off button.
26. Navigate to Hystar and ensure that the idle flow is active. If not right-click on the Evosep logo, choosing 'preparation', and then selecting 'idle flow' and 'Run'.
27. Return to timsControl.
28. Check the MS signal. It should be around 2.5x10^7.
29. Monitor the internal pressures in the timsTOF device. The funnel pressur is acceptable within a 9-11 mbar range.Aim for a 10 mbar funnel pressure. Adjust the 'funnel pressure' wheel if necessary. Turn counter clock-wise to reduce the pressure.

## Expected Results
- In timsControl, signal intensity should be above 10^7
- Stable signal in in timsControl (in the windows for Mobilogram (timsView) and mass spectrum)

## Figures
**Figure 1: TimsControl settings before changing source.**

**Figure 2: Apollo ESI source and gas flow pressure control wheels.**

**Figure 3: UltraSource.**

## References
1. Skowronek, P., Wallmann, G., Wahle, M. et al. An accessible workflow for high-sensitivity proteomics using parallel accumulation–serial fragmentation (PASEF). Nat Protoc (2025). https://doi.org/10.1038/s41596-024-01104-w 
2. timsTOF user manual