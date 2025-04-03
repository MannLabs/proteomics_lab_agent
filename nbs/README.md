# Notebooks

## Testing prompting approaches for lab video to protocol conversion
Experimenting with various prompting techniques to supply a LLM with the required background information to convert lab videos into protocols.

- Zero-shot prompting: 1_videoToProtocol_withoutAddedKnowledge.ipynb
- Few-shot learning: 2_videoToProtocol_withFewShotLearning.ipynb
- In context learning: 3_videoToProtocol_withInContextLearning.ipynb
- Chain-of-thought prompting: 4_videoToProtocol_ChainOfThoughtLogic.ipynb
- Chain-of-agents prompting: 5_videoToProtocol_ChainOfAgentsLogic.ipynb

Conclusion: Chain-of-thought prompting is most efficient and accurate to convert lab videos to protocols. Could be improved by introducing the "Protocol Check" from chain-of-agents prompting.
