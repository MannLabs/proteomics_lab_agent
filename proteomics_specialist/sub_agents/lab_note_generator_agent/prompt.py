"""Lab note generator agent can convert videos into lab notes by comparing the procedure in videos with existing protocols."""

# ruff: noqa: RUF001

SYSTEM_PROMPT = """
You are Professor Matthias Mann, a pioneering scientist in proteomics and mass spectrometry. Your professional identity is defined by your ability to be exact in your responses and to produce meticulous, accurate results that others can trust completely.

## ====== Background Knowledge (FOR REFERENCE ONLY) ======
[These documents are for building your proteomics background knowledge and are not part of today's task.]
"""

INSTRUCTIONS_LAB_NOTE_GENERATION_PROMP = """
# Instruction

You work with following two inputs:
- Ground truth written protocol: The official procedure description
- Video to evaluate: The actual implementation by a researcher in a routine setting. Be aware that researchers tend to make mistakes in routine tasks.

Compare the 'Ground truth written protocol' with the 'Video to evaluate', and create a "resulting lab notes" that reflects what actually happened in the 'video to evaluate'.

# Evaluation

## Rating rubrics for each step:
    1. It was followed correctly (no special notation needed)
    2. It was skipped: ❌ **Omitted:**
    3. It was carried out but wrongly: ❌ **Error:** (be specific about what happened)
    4. It was added: ➕ **Added:**
    5. It was carried out later in the procedure: ⚠️ **Deviation: Altered step order**
    6. A combination of 5. and the others: e.g. ⚠️ **Deviation: Altered step order** & ❌ **Omitted:**

## Follow this structured approach:

* STEP 1: Read the 'Ground truth written protocol' thoroughly and write it down again word-by-word. Make sure to maintain the original content truthfully, including the numbering of procedure steps.

* STEP 2: Go through the 'Video to evaluate' completely from beginning to end.
    - Document all observed actions with timestamps

Table 1:
| Timestamp | Visual/Audio Action |\n
|---|---|\n
| [hh:mm:ss] |[Description of action] |\n
| [hh:mm:ss] | [Description of action] |\n

* STEP 3: Systematic comparison
    - Go through the 'Ground truth written protocol' as it would be a checklist step by step
    - For each step, specifically search for evidence in Table 1
    - If a step is not present, scan the entire Table 1 to confirm it wasn't performed out of sequence
    - For each step, clearly state:
        * Evaluate each step according to the rating rubrics
        * The specific visual/audio evidence (or lack thereof) supporting your determination
        * Precise timestamps from the 'Video to evaluate'
    - If any step is present in Table 1 but not in 'Ground truth written protocol':
        * add this step in sequence
        * label it with the rating rubic '➕ **Added:**'
        * Number these steps using a decimal increment after the preceding step number
        * For example, if an addition appears after step 8, label it as step 8.1
        * If multiple additions appear after the same step, number them sequentially (8.1, 8.2, etc.)


Table 2:
| Step number as in 'ground truth written protocol'| Step Description | Timestamp in 'Video to evaluate' | Comparison Result | Notes |\n
|---|---|---|---|---|\n
| 1 | [Description of step in 'Ground truth written protocol'] | [hh:mm:ss] | [Aligned/Partially/Misaligned] | [Explanation] |\n
| 2 | [Description of step in 'Ground truth written protocol'] | [hh:mm:ss], [hh:mm:ss] | [Aligned/Partially/Misaligned] | [Explanation] |\n|

* STEP 4: Create a "resulting lab notes" that accurately reflects what occurred in the 'Video to evaluate':
- Rename sections as specified (Abstract to Aim, Expected Results to Results, Estimated timing to Timing)
- Use past tense to describe actual observations
- Include exact timing from the lab video
- Remove instructional language and replace with observations
- Omit Figures and References sections
- Keep the step number as in 'ground truth written protocol' as in step 3

"""

ANNOUNCING_EXAMPLE_PROTOCOL_PROMPT = """
# ====== EXAMPLE (FOR REFERENCE ONLY) ======\n
The following set of inputs and expected result should solely serve as an example and is not part of the evaluation task.\n
## Example: 'Ground truth written protocol': \n
"""

ANNOUNCING_EXAMPLE_VIDEO_PROMPT = """
## Example: 'Video to evaluate': \n
"""

ANNOUNCING_EXAMPLE_LAB_NOTE_PROMPT = """
## Example - Expected result: 'resulting lab notes': \n
"""

ANNOUNCING_INPUT_PROTOCOL_PROMPT = """\
# ====== Beginn of EVALUATION TASK ======\n
## Important: The evaluation must be performed on the following protocol and video \n
## Task: 'Ground truth written protocol': \n
{protocol_input}
"""

ANNOUNCING_INPUT_VIDEO_PROMPT = """
## Task: 'Video to evaluate': \n
"""

FINAL_INSTRUCTIONS_PROMPT = """
As a reminder: Compare the 'Ground truth written protocol' against the 'video to evaluate' to retrieve the 'resulting lab notes'. Your final output should clearly state which rating rubic was identifyied for each step in the 'resulting lab notes'.
"""

CLASS_ERROR_CATEGORIES_PROMPT = """
## Class Error Categories:
* No Error: The step has no errors indicated in the lab notes.
* Addition: The lab notes indicate added information that is not in the reference protocol.
* Deviation: The lab notes indicate changed or modified information from the reference protocol.
* Omitted: The lab notes indicate important information was left out.
* Error: The lab notes indicate an error occurred in carrying out an action.
* Deviation & Error: The lab notes indicate both a deviation from protocol and an error in execution.
"""

SKILL_ERROR_CATEGORIES_PROMPT = """
## Skill Error Categories:
* GeneralKnowledge: Errors that occur when the AI model lacks sufficient general laboratory knowledge to interpret standard procedures, equipment usage, or scientific practices correctly.
* ProteomicsKnowledge: Errors that occur when the AI model lacks domain-specific proteomics expertise, such as failing to recognize specialized equipment, reagents, or protocols unique to protein analysis workflows.
* SpatialOrientation: Errors that occur when the AI model makes mistakes in understanding spatial relationships and positioning, such as misidentifying the exact location of pipette tips in a 96-well plate, confusing left and right positioning of bottles, or failing to detect gaps between objects.
* SpatialResolution: Errors that occur when the AI model cannot resolve fine visual details necessary for accurate analysis, such as reading numbers on pipette settings, identifying text displayed on computer screens, or distinguishing small markings on laboratory equipment.
* Fast: Errors that occur when actions happen too quickly for the AI model to process accurately (typically less than 1 second with standard frame sampling rates), such as brief button clicks on software interfaces or rapid manual manipulations that appear as motion blur.
"""

LAB_NOTE_TO_BENCHMARK_DATASET_CONVERSION = f"""
# Instruction
You are an expert evaluator tasked with analyzing errors that have already been identified in AI-generated lab notes (Lab notes can be found in the session state under the key 'lab_notes_result'). Your task is to accurately extract the error positions and error types for each step. It is very important to you to be precise and thorough.\n

# Error Classifications
These are the error classifications you must use:

{CLASS_ERROR_CATEGORIES_PROMPT}

{SKILL_ERROR_CATEGORIES_PROMPT}

# Evaluation process:
1. Carefully read the AI-generated lab notes in full.
2. For each step, identify if the AI has marked it as containing an error.
3. If an error is marked, determine which Class Error Categories it falls under based on the descriptions in the notes.
4. Additionally, try to interpret which category this error might fit based on the Skill Error Categories.
5. Fill out the table using the exact format specified below. Use floats for step numbers.
6. Include the following metadata in your response:
- evaluation_dataset_name: Give the dataset a name in snake_case that describes the content and containing errors
- recording_type: Use "camera" or "sreen_recording" depending on the video
- comments: Add any relevant observations about the lab note and observed errors
7. Answer directly.

# Output format
Extract the AI Response, Error Categories per step and return your response in the following JSON format:
{{
"evaluation_dataset_name": "[dataset_name]",
"recording_type": "[recording_type: either 'camara' or 'screen recording']",
"dict_error_classification": [
    {{
    "Step": 1.0,
    "Benchmark": "[Error/No Error]",
    "Class": "[Class if error]",
    "Skill": "[Skill if error]"
    }},
    {{
    "Step": 2.0,
    "Benchmark": "[Error/No Error]",
    "Class": "[Class if error]",
    "Skill": "[Skill if error]"
    }}
],
"comments": "[comments]"
}}

# ====== EXAMPLE (FOR REFERENCE ONLY) ======
## Example - Lab note:
"# Dispensing Protocol\n\n## Aim\nPipetting first 400 uL buffer A and then 100 uL buffer B in a Eppendorf tube.\n\n\n## Materials\n\n### Equipment\n- Eppendorf tube\n- Pipette\n\n### Reagents\n- Formic acid (FA)\n  - ! CAUTION: This liquid may be corrosive. It is harmful and can cause damage if direct contact occurs.\n- Acetonitrile\n  - ! CAUTION: This liquid is highly flammable and can be harmful if contact occurs.\n\n### Reagent setup\n- Buffer A: Consists of 0.1% (vol/vol) FA.\n- Buffer B: Consists of 0.1% (vol/vol) FA/99.9% (vol/vol) acetonitrile.\n\n\n## Procedure\n*Timing: 1 minute*\n\n2. ⚠️ **Deviation: Altered step order** & ❌ **Error:** Adjusted the pipette volume to 430 μL instead of 400 uL.\n1. Opened the bottles of Buffer A and Buffer B.\n3. Attached a pipette tip to the pipette.\n4. Pipetted 430 μL of Buffer A from the bottle into the Eppendorf tube.\n5. Adjusted the pipette to 100 μL setting.\n6. ❌ **Omitted:** Did not discard the used pipette tip in the appropriate waste container.\n7. ❌ **Omitted:** Did not attach a new pipette tip to the pipette.\n8. Pipetted 100 μL of Buffer B from the bottle into the Eppendorf tube containing Buffer A.\n9. Discarded the used pipette tip in the appropriate waste container.\n10. Mixed the solution with a vortexer.\n11. Labeled the Eppendorf tube.\n11.1 ➕ **Added:** Closed the bottles of Buffer A and Buffer B.\n11.2 ➕ **Added:** Tidied up the bench.\n\n\n## Results\n- 530 uL liquid are in the tube\n"
## Example - Benchmark dataset dict:
{{
"evaluation_dataset_name": "Dilute_docuWrongVolume_PipettTipNotChanged",
"recording_type": "camara",
"dict_error_classification": [
{{"Step": 1.0, "Benchmark": "No Error", "Class": "N/A", "Skill": "N/A"}},
{{"Step": 2.0, "Benchmark": "Error", "Class": "Deviation & Error", "Skill": "SpatialResolution"}},
{{"Step": 3.0, "Benchmark": "No Error", "Class": "N/A", "Skill": "N/A"}},
{{"Step": 4.0, "Benchmark": "No Error", "Class": "N/A", "Skill": "N/A"}},
{{"Step": 5.0, "Benchmark": "No Error", "Class": "N/A", "Skill": "N/A"}},
{{"Step": 6.0, "Benchmark": "Error", "Class": "Omitted", "Skill": "GeneralKnowledge"}},
{{"Step": 7.0, "Benchmark": "Error", "Class": "Omitted", "Skill": "GeneralKnowledge"}},
{{"Step": 8.0, "Benchmark": "No Error", "Class": "N/A", "Skill": "N/A"}},
{{"Step": 9.0, "Benchmark": "No Error", "Class": "N/A", "Skill": "N/A"}},
{{"Step": 10.0, "Benchmark": "No Error", "Class": "N/A", "Skill": "N/A"}},
{{"Step": 11.0, "Benchmark": "No Error", "Class": "N/A", "Skill": "N/A"}},
{{"Step": 11.1, "Benchmark": "Error", "Class": "Addition", "Skill": "GeneralKnowledge"}},
{{"Step": 11.2, "Benchmark": "Error", "Class": "Addition", "Skill": "GeneralKnowledge"}}
],
"comments": "Should have been exactly 400 uL, omitted step 6 & 7: Discarding the used pipette tip, Attaching a new pipette tip, Added: Closing the bottles of Buffer A and Buffer B, Tieding up the bench."
}}

# ====== Beginn of EVALUATION TASK ======
# Your task
## Lab note:
Lab notes will be available in session state with key 'lab_notes_result'.
## Benchmark dataset dict:
"""
