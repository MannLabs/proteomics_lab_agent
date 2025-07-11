# Notebooks

## Testing prompting approaches for lab video to protocol conversion
Experimenting with various prompting techniques to supply a LLM with the required background information to convert lab videos into protocols.

- Zero-shot prompting: 1_videoToProtocol_withoutAddedKnowledge.ipynb
- Few-shot learning: 2_videoToProtocol_withFewShotLearning.ipynb
- In context learning: 3_videoToProtocol_withInContextLearning.ipynb
- Chain-of-thought prompting: 4_videoToProtocol_ChainOfThoughtLogic.ipynb
- Chain-of-agents prompting: 5_videoToProtocol_ChainOfAgentsLogic.ipynb

Conclusion: Chain-of-thought prompting is most efficient and accurate to convert lab videos to protocols. Could be improved by introducing the "Protocol Check" from chain-of-agents prompting.

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
