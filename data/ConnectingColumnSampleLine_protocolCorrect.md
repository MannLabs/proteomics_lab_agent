# Connecting IonOpticks Column & sample line of Evosep

## Abstract
This protocol explains how to connect an IonOpticks column inserted into a timsTOF Ultra with an sample line of an Evosep.


## Materials

### Equipment
- IonOpticks Column
- timsTOF Ultra Mass Spectrometer
  - Equipped with UltraSource ion source
  - Equipped with column oven for temperature control
- Evosep One LC System
  - with sample line
- NanoViper Adapter (black)
- Pliers


## Procedure
*Estimated timing: 3 minutes*

1. Verfy that the instrument is in standing by mode. If not press the on/off button to switch from operate mode to standing by mode.

### Connect column and sample line
2. Verify that an IonOpticks column is already inserted into the UltraSource of the timsTOF Ultra. 
3. Attach a black NanoViper adapter to the LC sample line.
4. Remove any access liquid at the top of the nanoViper of the sample line for instance by snipping it off.
5. Hold the column fititng of the IonOpticks column with a pliers.
6. Hand-tighten the NanoViper of the LC sample line with the column fitting (Figure 1).
   CRITICAL STEP: Be careful not to overtighten the connection between the IonOpticks column and the timsTOF Ultra. Otherwise you can damage the column and the LC sample line.
7. Remove the NanoViper adapter so that the oven can be tightly closed.
8. Draw the oven closer to the UltraSource, secure it with the screw on the bottom of the oven (Figure 2).
9. Lift and place the metal grounding screw at the column-sample line connection to establish proper ESI spray grounding with the column oven.
10. Close the lid of the oven.
11. Verify the temperature at 50°C for IonOpticks columns, as indicated by three illuminated LEDs on the column oven, respectively.

### Switch timsTOF to operate and idle flow
12. In timsControl, transition the instrument to the operation mode by using the on/off button.
13. Navigate to Hystar and ensure that the idle flow is active. If not right-click on the Evosep logo, choosing 'preparation', and then selecting 'idle flow' and 'Run'.
14. Return to timsControl. Check the MS signal. It should be around 2.5x10^7.


## Expected Results
- In timsControl, signal intensity should be above 10^7
- Stable signal in in timsControl (in the windows for Mobilogram (timsView) and mass spectrum)


## Figures
**Figure 1: Connection of a sample line of a LC system with a separation column and emitter.**

**Figure 2: UltraSource.**


## References
1. Skowronek, P., Wallmann, G., Wahle, M. et al. An accessible workflow for high-sensitivity proteomics using parallel accumulation–serial fragmentation (PASEF). Nat Protoc (2025). https://doi.org/10.1038/s41596-024-01104-w
