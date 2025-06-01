# Notebooks

## Workflow for converting videos to protocols
- Experimenting with various prompting techniques to supply a LLM with the required background information to convert lab videos into protocols. 
    File: 1_videoToProtocol_Evaluation.ipynb
- Analyzing the evaluaiton results to generate statistics which techniques work well
    File: 2_videoToProtocol_results.ipynb

## Workflow for generatig laboratory notes from videos:
The following notebooks are the proof-of-concept workflow for generating laboratory notes from videos.

- Protocol Selection and Accuracy Evaluation:
    Identify the protocol that best matches the procedure shown in the video
    File: 1_videoToLabNotes_ProtocolFinder.ipynb
- Lab Notes Generation and Error Analysis:
    Compare video with ground-truth protocol to generate lab notes and identify procedural errors
    Automatically evaluate lab note assistant's error detection against benchmark dataset
    File: 2_videoToLabNotes_CompareVideoWithProtocol.ipynb
- Benchmark Results Analysis:
    Generate comprehensive statistics for benchmark evaluation results
    File: 3_videoToLabNotes_results.ipynb
