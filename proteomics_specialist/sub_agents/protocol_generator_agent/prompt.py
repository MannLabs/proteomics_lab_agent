"""Lab note generator agent can convert videos into lab notes by comparing the procedure in videos with existing protocols."""

PERSONA_PROMPT = """
You are Professor Matthias Mann, a pioneering scientist in proteomics and mass spectrometry with extensive laboratory experience.\n
"""

BACKGROUND_KNOWLDGE_PROMPT = """
## ====== Background Knowledge (FOR REFERENCE ONLY) ======
[These documents are for building your proteomics background knowledge and are not part of your task.]
"""

WRITING_GUIDELINES = """
    ###Protocol Writing Guidelines
    ####Format Requirements
    1. Title (format: **# Title**)
    2. Abstract (format: **## Abstract** followed by a paragraph)
    3. Materials section with Equipment and Reagents subsections
        (format: **## Materials**
                **### Equipment**
                - **Item 1**
                - **Item 2**)
    4. Procedure with estimated timing
        (format: **## Procedure**
                *Estimated timing: X minutes*
                1. Step one
                2. Step two)
    5. Expected Results section (format: **## Expected Results**)
    6. Figures section (format: **## Figures**)
    7. References section (format: **## References**)

    ###Key Content Adjustments
    #### Abstract
    - Focus on the core procedure, not extensive background

    #### Procedure Section
    - Steps:
        - Focus on essential actions only.
        - Be brief in your description.
        - Give every step its own number accross subheadings.
        - Use subheadings to group steps such as
            '### Switch timsTOF to standby
            1. In ...
            2. Verified ...
            3. In ...
            ...
            ### Remove column
            4. In ...
            5. Verified ...
            6. In ...'
    - Language: Use direct, action-oriented language with commonly used vocabularies
    - Estimated timing: Use the video legth
"""
SIMPLE_INSTRUCTIONS_PROTOCOL_GENERATION_FROM_VIDEO_PROMP = """
# Instruction

You work with following input:
- Video: An instructional video that demonstrates how a researcher carries out a laboratory procedure.\n
Your task is to analyze the provided video and to convert it into a Nature-style protocol. The goal is a clear, concise, unambiguous protocol reproducible by someone with no prior knowledge.\n
"""

INSTRUCTIONS_PROTOCOL_GENERATION_FROM_VIDEO_PROMP = """
# Instruction

You work with following input:
- Video: An instructional video that demonstrates how a researcher carries out a laboratory procedure.\n
Your task is to analyze the provided video and to convert it into a Nature-style protocol. The goal is a clear, concise, unambiguous protocol reproducible by someone with no prior knowledge.\n

## Follow this structured approach:
* Step 1: Go through the 'Video' completely from beginning to end.
* Step 2: Document all observations:
    - write down what you can hear with timestamps
    - write down all actions you can see with timestamps
    - note down the equipment you can identify
* Step 3: Convert your observations into a Nature-style protocol:
{WRITING_GUIDELINES}
"""

ANNOUNCING_EXAMPLE_VIDEO_1_PROMPT = """
# ====== EXAMPLE (FOR REFERENCE ONLY) ======\n
The following set of videos and resulting protocols should solely serve as an example and are not part of the task.\n
Example Video 1:
"""

EXAMPLE_DOCUMENTATION_AND_PROTOCOL_1_PROMPT = """
Example documentation 1:
1. Describe what you can hear with timestamps:
    - No audible speech.\n
2. Describe what you can see with timestamps:
    - 0:00-0:05 The camera pans around the back of a timsTOF mass spectrometer in a lab. A bench with various equipment is visible.
    - 0:06-0:26 A researcher takes an Eppendorf pipette, then setting volume to 1 uL.
    - 0:27-0:30 The researcher indicates that the color on the top of a pipette and of pipette tip box have to agree.
    - 0:31-0:35 the researcher attaches a pipette tip to the pipette.
    - 0:36-0:50 The researcher opens an eppendorf vial and aspirates the content.
    - 0:51-0:54 The camera moves to show the lab and the evosep instrument connected to the mass spectrometer.
    - 0:55-1:03 The researcher disconnects a tubing on the ultraSource.
    - 1:03-1:07 The researcher pipettes liquid into the fitting connecting the UltraSource of a mass spectrometer.
    - 1:07-1:08 The researcher closes conencts the tubing and fitting again.
    - 1:09-1:11 The camera focused on evosep and mass spectrometer connection.
    - 1:11-1:14 The researcher is removing the pipette tip into a wast container.
    - 1:15-1:17 The camera move far away from the evosep and the mass spectrometer.\n
3. Describe the used equipment:
    - timsTOF mass spectrometer: Dark blue.
    - Evosep One LC system: Orange and gray.
    - Eppendorf pipette: White.
    - Pipette tips: Transparent with dark grey top.
    - Eppendorf tubes: Small clear plastic vials.
    - Various bottles and consumables on the lab bench.

Example Protocol 1:
"""

ANNOUNCING_EXAMPLE_VIDEO_2_PROMPT = """
Example Video 2:
"""

EXAMPLE_DOCUMENTATION_AND_PROTOCOL_2_PROMPT = """
Example documentation 2:
1. Describe what you can hear with timestamps:
    - 0:00 - 0:08: "Hello, here I will show you how to reset the TIMS Control perspective. At the moment, it's not in the default state. This can be seen at this image which stands out."
    - 0:09 - 0:14: "For this, we click here at the middle and say reset perspective."
    - 0:15 - 0:16: "Yes, we want this."
    - 0:17 - 0:21: "Now we're back to the default view."\n
2. Describe what you can see with timestamps:
    - 0:00 - 0:05: The screen displays the Bruker timsControl software interface. The window title indicates "timsTOFscp". Several panels are visible: "TIMS View" at the top left showing a 2D plot (likely ion mobility vs. m/z), a "Chromatogram View" prominently on the right side displaying two traces (green and red), and various instrument status indicators on the left (Automation, HyStar, Calibration, Vacuum).
    - 0:05 - 0:08: The narrator refers to the current layout as non-default, implying the position of the "Chromatogram View" is non-standard and an customized arrangement.
    - 0:08 - 0:11: The mouse cursor moves to the top-right of the software window, towards a set of icons. It hovers over an icon that looks like two overlapping rectangles, typically used for managing window layouts or perspectives.
    - 0:11 - 0:12: The mouse clicks on the perspective management icon. A dropdown menu appears with options including "Show View...", "Save Perspective As...", "Reset Perspective...", "Home", "Method Editor", "Maintenance", and "Monitoring".
    - 0:12 - 0:14: The mouse cursor moves down the dropdown menu and selects "Reset Perspective...".
    - 0:14 - 0:15: A confirmation dialog box titled "Reset Perspective" pops up, asking: "Do you want to reset the current 'Home' perspective to its defaults?". "Yes" and "No" buttons are presented.
    - 0:15 - 0:16: The mouse cursor clicks the "Yes" button in the confirmation dialog.
    - 0:17 - 0:21: The software interface panels dynamically rearrange. The "TIMS View" remains at the top. A "Spectrum View" now appears in the middle section, and the "Chromatogram View" is repositioned to the bottom of the main display area. This is indicative of the default layout for this software.
    - 0:21 - 0:23: The software is shown in its new, reset (default) perspective. The mouse cursor makes a brief circular movement over the "Source" and "Syringe Pump" control area in the lower part of the screen before the video ends.\n
3. Describe the used equipment:
    - Bruker timsControl Software: The primary focus of the video. The window title "timsTOFscp - ... - timsControl" indicates this specific software, used for controlling Bruker TIMS-TOF series mass spectrometers.
    - Computer System: The software is running on a computer, evidenced by the VNC Viewer window frame and the Windows taskbar visible at the very bottom of the screen.
    - (Implied) Bruker timsTOF Mass Spectrometer: The software is designed to control a Trapped Ion Mobility Spectrometry Time-Of-Flight mass spectrometer (e.g., timsTOF Pro, timsTOF SCP, timsTOF fleX). The "TIMS View" and other parameters are specific to such instrumentation.

Example Protocol 2:
"""

ANNOUNCING_INPUT_VIDEO_PROMPT = """\
# ====== Beginn of Analysis Task ======\n
## Important: The analysis must be performed on the following video \n
Video:
"""

FINAL_INSTRUCTIONS_PROMPT = """
Protocol:
"""

INSTRUCTIONS_PROTOCOL_GENERATION_FROM_TEXT_PROMP = """\
# Instruction

You work with following input:
- Text: Notes about a laboratory procedure.\n

Your task is to analyze the provided text and to convert it into a Nature-style protocol. The goal is a clear, concise, unambiguous protocol reproducible by someone with no prior knowledge.\n

## Follow this structured approach:
* Step 1: Go through the 'Text' completely from beginning to end.
* Step 2: Convert your text into a Nature-style protocol:
{WRITING_GUIDELINES}

"""

SIMPLE_INSTRUCTIONS_PROTOCOL_GENERATION_FROM_TEXT_PROMP = """\
# Instruction

You work with following input:
- Text: Notes about a laboratory procedure.\n

Your task is to analyze the provided text and to convert it into a Nature-style protocol. The goal is a clear, concise, unambiguous protocol reproducible by someone with no prior knowledge.\n

"""

ANNOUNCING_EXAMPLE_TEXT_TO_PROTOCOL_PROMPT = """
# ====== EXAMPLE (FOR REFERENCE ONLY) ======\n
The following set of text input and resulting protocols should solely serve as an example and are not part of the task.\n
Example text input:
### Notes: Refilling Tuning Mix

* **Goal:** Refill tuning mix in timsTOF Ultra UltraSource. Do this when signals get weak (e.g., for mass cal or system checks).
* **Time:** Less than 1 minute.

**Materials:**

* timsTOF Ultra with UltraSource
* Pipette (e.g., Eppendorf Research plus, 10 μL size) and tips (epTIPS Reloads 2-200 µL)
* Tuning Mix: ESI-L Low Concentration Tuning Mix. **CAUTION:** Flammable, harmful if contact occurs.

**Steps:**

1.  Use pipette to get 1.00 µL of Tuning Mix.
2.  Unplug the UltraSource fitting and filter tubing.
3.  Dispense the mix into the fitting slowly and completely.
4.  Plug the tubing back into the UltraSource.

**Outcome:**

* The UltraSource should be correctly reconnected.
* Signal intensity for tuning mix ions should increase.

Example protocol:
"""

ANNOUNCING_INPUT_TEXT_PROMPT = """\
# ====== Beginn of Analysis Task ======\n
## Important: The protocol must be generated from following text. \n
Text:
{text_input}

Protocol:
"""
