# proteomics_specialist

The [Mann Labs at the Max Planck Institute of Biochemistry](https://www.biochem.mpg.de/mann) developed proteomics_specialist (also called AI Proteomics Advisor), a multimodal, agentic AI framework that aims to democratizes mass spectrometry-based proteomics through personalized laboratory assistance and automated documentation. To access all the hyperlinks in this document, please view it on [GitHub](https://github.com/MannLabs/proteomics_specialist).

* [**About**](#about)
* [**License**](#license)
* [**Installation**](#installation)
  * [**Developer installer**](#developer)
* [**Usage**](#usage)
  * [**Python and jupyter notebooks**](#python-and-jupyter-notebooks)
* [**Troubleshooting**](#troubleshooting)
* [**FAQ**](#faq)
* [**Citations**](#citations)
* [**How to contribute**](#how-to-contribute)
* [**Changelog**](#changelog)

---
## About

Mass spectrometry-based proteomics has advanced significantly in the last decade, yet its widespread adoption remains constrained by complex instrumentations & software that requires extensive expertise. We identified documentation and knowledge transfer as key bottlenecks in proteomics accessibility and developed an AI Proteomics Advisor to address these challenges.

The AI Proteomics Advisor is a multimodal agentic framework that combines Mann Labs' proteomics expertise with Google's cloud infrastructure. The framework incorporates lab-specific knowledge through multimodal chain-of-thought prompting and a custom knowledge base containing laboratory protocols. It also leverages Google's Agent Development Kit, Gemini, and Vertex AI services, integrated with local MCP servers including Alphakraken for retrieving QC results and Confluence for managing lab-internal protocols.

### Key Features

It provides:
* **Personalized guidance** based on user expertise levels
* **Automatic protocol generation:** Transforms notes, photos, or laboratory videos with expert voice-over explanations into Nature-style protocols, significantly lowering documentation barriers for researchers.
* **Automated laboratory notes generation and error detection:** Generates error-flagging laboratory notes by comparing video footage with baseline protocol procedures.

---
## License

proteomics_specialist was developed by the [Mann Labs at the Max Planck Institute of Biochemistry](https://www.biochem.mpg.de/mann) and is freely available with an [Apache License 2.0](LICENSE.txt). External Python packages (available in the [requirements](requirements) folder) have their own licenses, which can be consulted on their respective websites.

---
## Installation

* [**Developer installer:**](#developer) Choose this installation if you are familiar with CLI tools, [conda](https://docs.conda.io/en/latest/), and Python. This installation allows access to all available features of proteomics_specialist and even allows to modify its source code directly. Generally, the developer version of proteomics_specialist outperforms the precompiled versions.

### Developer

proteomics_specialist can also be installed in editable (i.e. developer) mode with a few `bash` commands. This allows to fully customize the software and even modify the source code to your specific needs. When an editable Python package is installed, its source code is stored in a transparent location of your choice. While optional, it is advised to first (create and) navigate to e.g. a general software folder:

```bash
mkdir ~/folder/where/to/install/software
cd ~/folder/where/to/install/software
```

***The following commands assume you do not perform any additional `cd` commands anymore***.

Next, download the proteomics_specialist repository from GitHub either directly or with a `git` command. This creates a new proteomics_specialist subfolder in your current directory.

```bash
git clone https://github.com/MannLabs/proteomics_specialist.git
```

For any Python package, it is highly recommended to use a separate [conda virtual environment](https://docs.conda.io/en/latest/), as otherwise *dependency conflicts can occur with already existing packages*.

```bash
conda create --name proteomics_specialist python=3.11 -y
conda activate proteomics_specialist
```

Finally, proteomics_specialist and all its [dependencies](requirements) need to be installed.

```bash
pip install -e "./proteomics_specialist"
```

***By using the editable flag `-e`, all modifications to the [proteomics_specialist source code folder](proteomics_specialist) are directly reflected when running proteomics_specialist. Note that the proteomics_specialist folder cannot be moved and/or renamed if an editable version is installed.***

---
## Usage

### Jupyter notebooks

The ‘nbs’ folder in the GitHub repository contains Jupyter Notebooks on using proteomics_specialist as a Python package. The following notebooks have a dual purpose: they function as tutorials and provide the basis for paper figures.

#### Workflow for converting videos to protocols
- Experimenting with various prompting techniques to supply a LLM with the required background information to convert lab videos into protocols.
    File: 1_videoToProtocol_Evaluation.ipynb
- Analyzing the evaluaiton results to generate statistics which techniques work well
    File: 2_videoToProtocol_results.ipynb

#### Workflow for generatig laboratory notes from videos:
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


---
## Troubleshooting

In case of issues, check out the following links:

* [FAQ](https://github.com/MannLabs/proteomics_specialist#faq): This section provides answers to issues of general interest.
* [Issues](https://github.com/MannLabs/proteomics_specialist/issues): Try a few different search terms to find out if a similar problem has been encountered before.

---
## FAQ
- Where to find test file?

---
## Citations

We are currently writting the manuscript.

---
## How to contribute

If you like this software, you can give us a [star](https://github.com/MannLabs/proteomics_specialist/stargazers) to boost our visibility! All direct contributions are also welcome. Feel free to post a new [issue](https://github.com/MannLabs/proteomics_specialist/issues) or clone the repository and create a [pull request](https://github.com/MannLabs/proteomics_specialist/pulls) with a new branch. For even more interactive participation, check out the [the Contributors License Agreement](misc/CLA.md).

### Notes for developers

#### pre-commit hooks
It is highly recommended to use the provided pre-commit hooks, as the CI pipeline enforces all checks therein to pass in order to merge a branch.

The hooks need to be installed once by
```bash
pip install -r requirements_development.txt
pre-commit install
```
You can run the checks yourself using:
```bash
pre-commit run --all-files
```

##### The `detect-secrets` hook fails
To set up a secret in your repository:
```bash
pip install detect-secrets
```
1. Generate a secrets.ini file with the secret and add secrets.ini to .gitignore
2. Run `detect-secrets scan --exclude-files testfiles --exclude-lines '"(hash|id|image/\w+)":.*' > .secrets.baseline` to scan your repository and create a .secrets.baseline file
(check `.pre-commit-config.yaml` for the exact parameters)
3. Run `detect-secrets audit .secrets.baseline` and check if the detected 'secret' is actually a secret
4. Commit the latest version of `.secrets.baseline`
