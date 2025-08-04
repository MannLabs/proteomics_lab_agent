"""Prompts."""

# ruff: noqa: RUF001

EXTRACTION_PROMPT = """\
    # Instruction
    You are an expert evaluator tasked with analyzing errors that have already been identified in AI-generated lab notes. Your task is to accurately extract the error positions and error types for each step. It is very important to you to be precise and thorough.\n

    These are the error classifications you must use:
    {CLASS_ERROR_CATEGORIES_PROMPT}
    * N/A: Used only when a step number is not present in the lab notes.

    # Evaluation process:
    1. Carefully read the AI-generated lab notes in full.
    2. For each step in the specified range {docu_steps}, identify if the AI has marked it as containing an error.
    3. If an error is marked, determine which classification it falls under based on the descriptions in the notes.
    4. For Added steps (usually marked with ➕ **Added:**):
    * These typically appear with decimal step numbers (like 8.1, 8.2) in the lab notes
    * ALWAYS include these decimal-numbered steps in your evaluation table, even if they appear outside the {docu_steps} range
    * Place them in the correct sequence in your table (after their parent step)
    5. If a step number that should be within the {docu_steps} range is completely missing from the lab notes:
    * Include it in your table with "N/A" in both the "AI Response" and "AI Class" columns
    6. Fill out the table using the exact format specified below.
    7. Answer direct.

    # Output format
    Extract the AI Response, AI Class per step and return your response in the following JSON format:
    {{
    "steps": [
        {{
        "step": 1.0,
        "ai_response": "[Error/No Error]",
        "ai_class": "[Class if error]"
        }},
        {{
        "step": 2.0,
        "ai_response": "[Error/No Error]",
        "ai_class": "[Class if error]"
        }}
    ]
    }}

    # ====== EXAMPLE (FOR REFERENCE ONLY) ======
    ## Example: AI-Generated lab notes
    # DNA Extraction Protocol Observation
    *Timing: 35 minutes*

    ## Procedure

    1. The researcher retrieved the cell culture samples from the incubator and placed them on the bench [00:01:15-00:01:45].

    2. ⚠️ **Deviation: Altered step order** & ❌ **Error:** The researcher added 500 μL of lysis buffer to each microcentrifuge tube *before* transferring the cell samples [00:02:10-00:03:05]. (Protocol specified adding cells first, then buffer).

    3. The researcher transferred 200 μL of cell culture to each microcentrifuge tube containing lysis buffer [00:03:30-00:04:45].

    4. ❌ **Error:** The tubes were incubated at 65°C for 5 minutes [00:05:10-00:10:15]. (Protocol specified incubation at 56°C).

    5. 200 μL of 100% ethanol was added to each lysate and mixed by pipetting [00:10:45-00:12:20].

    6. ❌ **Omitted:** The researcher did not centrifuge the lysate briefly to remove drops from the lid as specified in the protocol [00:12:20-00:12:35].

    7. The lysate was transferred to DNA purification columns placed in collection tubes [00:13:10-00:15:05].

    8. The columns were centrifuged at 10,000 x g for 1 minute [00:15:30-00:16:45].

    8.1 ➕ **Added:** The researcher labeled each collection tube with sample ID and date [00:17:00-00:17:45]. (This step was not in the original protocol).

    9. ❌ **Omitted:** The researcher did not discard the flow-through and reuse the collection tube as specified in the protocol [00:17:45-00:18:00].

    10. ⚠️ **Deviation:** The flow-through was discarded and *a new collection tube* was used for the next step [00:21:30-00:22:15]. (Protocol specified reusing the same collection tube).

    ## Example: Classification Table

    {{
    "steps": [
        {{
        "step": 1.0,
        "ai_response": "No Error",
        "ai_class": "N/A"
        }},
        {{
        "step": 2.0,
        "ai_response": "Error",
        "ai_class": "Deviation & Error"
        }},
        {{
        "step": 3.0,
        "ai_response": "No Error",
        "ai_class": "N/A"
        }},
        {{
        "step": 4.0,
        "ai_response": "Error",
        "ai_class": "Error"
        }},
        {{
        "step": 5.0,
        "ai_response": "No Error",
        "ai_class": "N/A"
        }},
        {{
        "step": 6.0,
        "ai_response": "Error",
        "ai_class": "Omitted"
        }},
        {{
        "step": 7.0,
        "ai_response": "No Error",
        "ai_class": "N/A"
        }},
        {{
        "step": 8.0,
        "ai_response": "No Error",
        "ai_class": "N/A"
        }},
        {{
        "step": "8.1",
        "ai_response": "Error",
        "ai_class": "Addition"
        }},
        {{
        "step": 9.0,
        "ai_response": "Error",
        "ai_class": "Omitted"
        }},
        {{
        "step": 10.0,
        "ai_response": "Error",
        "ai_class": "Deviation"
        }}
    ]
    }}

    # ====== Beginn of EVALUATION TASK ======
    ## AI-Generated lab notes
    {lab_notes}
    ## Classification Table
    """

EVAL_SET_CONVERTER_PROMPT = """/
You are an expert data extractor analyzing a conversation log between a user and an AI assistant.
The log details the AI generating lab notes from a video based on a scientific protocol.

From the complete conversation log provided below, you must extract two specific pieces of information:

1.  **The full 'ground truth' scientific protocol**: This is the reference protocol the AI uses. It is often presented early in the conversation. If available choose the one labeled 'Ground Truth Written Protocol'. Allternative look at a large text block. Find the most complete version.

2.  **The final, corrected 'ground truth' lab notes**: This is the version of the lab notes AFTER all user corrections have been applied. It is usually the last complete version of the lab notes shown or mentioned before the conversation ends. It might be in the assistant's final response or in a command to save the notes.

Return your findings as a single JSON object matching the provided schema. Do not include any other text or explanation.

CONVERSATION LOG:
---
---
{full_conversation_text}
---
"""
