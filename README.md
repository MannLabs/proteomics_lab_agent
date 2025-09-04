# proteomics_specialist

The [Mann Labs at the Max Planck Institute of Biochemistry](https://www.biochem.mpg.de/mann) developed proteomics_specialist (also called AI Proteomics Advisor), a multimodal, agentic AI framework that aims to democratizes mass spectrometry-based proteomics through personalized laboratory assistance and automated documentation. To access all the hyperlinks in this document, please view it on [GitHub](https://github.com/MannLabs/proteomics_specialist).

* [**About**](#about)
* [**License**](#license)
* [**Installation**](#installation)
    * [**Project Structure**](#project-structure)
    * [**Download source code**](#download-source-code)
    * [**Setup instructions**](#setup-instructions)
    * [**Development**](#development)
    * [**Deployment**](#deployment)
* [**Jupyter notebooks**](#jupyter-notebooks)
* [**Troubleshooting**](#troubleshooting)
* [**FAQ**](#faq)
* [**Citations**](#citations)
* [**How to contribute**](#how-to-contribute)
* [**Changelog**](#changelog)

---
## About

Mass spectrometry-based proteomics has advanced significantly in the last decade, yet its widespread adoption remains constrained by complex instrumentations & software that requires extensive expertise. We identified documentation and knowledge transfer as key bottlenecks in proteomics accessibility and developed an AI Proteomics Agent to address these challenges.

The AI Proteomics Agent is a multimodal agentic framework that combines Mann Labs' proteomics expertise with Google's cloud infrastructure. The framework incorporates lab-specific knowledge through multimodal chain-of-thought prompting and a custom knowledge base containing laboratory protocols. It also leverages Google's Agent Development Kit, Gemini, and Vertex AI services, integrated with local MCP servers including Alphakraken for retrieving QC results and Confluence for managing lab-internal protocols.

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

### Project Structure

```
proteomics_specialist/
...
proteomics_specialist/
├── eval/                          # Evaluation scripts and test conversion utilities
├── nbs/                           # Jupyter notebooks for tutorials and figures
├── proteomics_specialist/         # Main agent package
│   ├── __init__.py
│   ├── agent.py                   # Root ADK agent orchestrating tools/subagents
│   ├── prompt.py                  # Root agent prompt
│   └── sub_agents/
│       └── instrument_agent/     # Sub-agent module
│           ├── __init__.py
│           ├── agent.py           # Local MCP server integration
│           └── prompt.py          # Subagent prompt
├── .env                           # Environment variables (from .env.example)
├── secrets.ini                    # Secrets configuration (from secrets.ini.example)
└── README.md                      # Project documentation
```

### Download source code

proteomics_specialist can be installed in editable (i.e. developer) mode with `bash` commands. This allows to fully customize the software and even modify the source code to your specific needs. When an editable Python package is installed, its source code is stored in a transparent location of your choice. While optional, it is advised to first (create and) navigate to e.g. a general software folder:

```bash
mkdir ~/folder/where/to/install/software
cd ~/folder/where/to/install/software
```

***The following commands assume you do not perform any additional `cd` commands anymore***.

Next, download the proteomics_specialist repository from GitHub either directly or with a `git` command. This creates a new proteomics_specialist subfolder in your current directory.

```bash
git clone https://github.com/MannLabs/proteomics_specialist.git
```

### Setup Instructions

#### 1. Prerequisites
- Python 3.12+
- Access to a terminal or command prompt

##### Google Cloud Infrastructure
- **Component**: Google Cloud Project with Cloud Storage Bucket & Service account keys
- **Purpose**:
    - Generate LLM responses via API calls
    - Store and serve video content for prompt processing
- **Text Setup Instructions**: [Creating projects](https://cloud.google.com/resource-manager/docs/creating-managing-projects) & [Creating cloud storage buckets](https://cloud.google.com/storage/docs/creating-buckets) & [Creating service account keys](https://cloud.google.com/iam/docs/keys-create-delete#iam-service-account-keys-create-console)
- **Video Setup Instructions**: [Video with guide: Step 2 & 3 beginning at 10:14](https://www.youtube.com/watch?v=bPtKnDIVEsg)
- **Required Services**:
    - Billing enabled
    - Cloud Storage API
    - Vertex AI
    - Service account keys

##### Knowledge Management System
- **Component**: Confluence with lab_knowledge_agent
- **Purpose**: Retrieve and save laboratory information
- **Setup Instructions**: [Getting started with confluence spaces](https://www.atlassian.com/software/confluence/resources/guides/get-started/set-up#learn-about-spaces)
- **Configuration Notes**:
    1. Create a dedicated Confluence space for lab_knowledge_agent
    2. Create two parent pages:
        - "Protocols" page
        - "Lab Notes" page
    3. Record the following for configuration: Space Key, Protocols Page ID, Lab Notes Page ID

##### Proteomics Analysis Platform
- **Component**: Alphakraken
- **Purpose**: Provides fully automated data processing and analysis system for mass spectrometry experiments
- **Setup Instructions**: [Alphakraken quick start guide](https://github.com/MannLabs/alphakraken?tab=readme-ov-file#quick-start)

#### 4. Configure settings
The `agent.py` will load the keys defined in .env and .env.secrets.

1. Set the environment variables. You can set them in your .env file (modify and rename .env.example file to .env). The `agent.py` will load the defined Google Cloud project to be able to access the Gemini model.
2. Set secrets. You can set them in your .env.secrets file (modify and rename .env.secrets.example file to .env.secrets).
3. Generate a Confluence API Token for Authentication (Cloud) - **Recommended**
    1. Go to https://id.atlassian.com/manage-profile/security/api-tokens
    2. Click **Create API token**, name it
    3. Copy the token immediately

#### 5. Establish MCP servers with Docker

Docker allows applications to be packaged and run in isolated environments called containers. Some MCP servers are distributed as Docker images, making them easy to run across different operating systems.

1.   **Installation**: Download and install Docker Desktop from the [official Docker website](https://www.docker.com/products/docker-desktop/). Docker Desktop is available for Windows, macOS, and Linux and provides a graphical interface as well as command-line tools.
2.   **Post-Installation**: Ensure Docker Desktop is running after installation, as this starts the Docker daemon (the background service that manages containers).
3.   **Verification**: Open a terminal or command prompt and verify the Docker installation by typing:
```bash
docker --version
```
4.  **Install the Alphakraken MCP server**: Clone the alphakraken repository:
```bash
git clone https://github.com/MannLabs/alphakraken.git
cd directory/of/alphakraken
git checkout mcp_http
docker build -t mcpserver_http -f mcp-server/Dockerfile .
# test that the mcpserver works
docker run -p 8089:8089 mcpserver_http
```

**Optional: Install sqlite**: The qc_memory agent is writting and reading a sqlite database. Install sqlite if you want to check the database entries.
Check if sqlite is already installed: `sqlite3 --version`
If not:
- **Ubuntu/Linux**: `sudo apt update && sudo apt install sqlite3`
- **macOS**: `brew install sqlite`
- **Windows**: `choco install sqlite`

Now you can either continue with development or deployment.


### Development

#### 1. Google authentication

Once you have created your project, [install the google cloud SDK](https://cloud.google.com/sdk/docs/install). Then run the following command to authenticate:
```bash
gcloud auth login
gcloud init
```
This allows the ADK agent in this project to use a Gemini model.

#### 2. Create and Activate Virtual Environment

It's highly recommended to use a virtual environment to manage project dependencies. Navigate to the folder with this code base. Create a virtual environment (e.g., named .venv)
```bash
python3 -m venv .venv
```

Activate the virtual environment:
1. On macOS/Linux:
```bash
source .venv/bin/activate
```
2. On Windows:
```bash
.venv\Scripts\activate
```

#### 3. Install dependencies

Install proteomics_specialist and all its [dependencies](requirements):
```bash
# Install main requirements
pip install -r requirements/requirements.txt

# Install development requirements (if you need dev dependencies)
pip install -r requirements/requirements_development.txt
```

#### 4. Running the Agent

You can run the agent locally using the `adk` command in your terminal:

* Run docker containers for mcp servers of alphakraken and confluence:
- `docker compose --env-file ./.env.secrets --env-file ./.env up confluence_mcp alphakraken_mcp` you can add `-d` flag to detach the containers from the shell session

* Open fresh terminal, ensure your virtual environment is active and you are in the root directory of the `proteomics_specialist` project.
1.  To run the agent from the CLI:
```bash
adk run proteomics_specialist
```
2.  To run the agent from the ADK web UI:
```bash
adk web
```
or to make a web server accessible from other devices on your network, not just locally:
```bash
adk web --host 0.0.0.0
```
Then select the `proteomics_specialist` from the dropdown.

This will:
- Start the adk root agent (`proteomics_specialist/agent.py`).
- The root agent can initialize the `MCPToolset` of subagents such as instrument_agent, qc_memory_agent or lab_knowledge_agent.
- The MCP servers will start automatically and listen for tool calls from the agents via stdio.
- The agents will then be ready to process your instructions (which you would typically provide in a client application or test environment that uses these agents).


### Deployment

The project can be deployed using Docker Compose. This approach containerizes all components for easier management and deployment.

The Docker deployment includes the following containers:
- python_lab_agent: Main proteomics specialist agent
- alphakraken_mcp: MCP server for proteomics analysis
- confluence_mcp: MCP server for knowledge management

#### Build Docker containers

```bash
docker compose --env-file ./.env.secrets --env-file ./.env build
```

#### Start the application

For troubleshooting (with logs visible):
```bash
docker compose --env-file ./.env.secrets --env-file ./.env up
```
For production (detached mode):
```bash
docker compose --env-file ./.env.secrets --env-file ./.env up -d
```

#### Stop deployment (when updating or maintenance)

```bash
# Stop all containers defined in docker-compose
docker container stop python_lab_agent alphakraken_mcp confluence_mcp
```

---
## Jupyter notebooks

The ‘nbs’ folder in the GitHub repository contains Jupyter Notebooks on using proteomics_specialist as a Python package. The following notebooks have a dual purpose: they function as tutorials and provide the basis for paper figures.

### Debugging MCP functionalities of agnets
- Notebook for developing / debugging database functions:
    File: database_test.ipynb

### Workflow for converting videos or text to protocols
- Notebook for developing / debugging the protocol generation pipeline within the ADK workflow
    File: protocolGeneration.ipynb

### Workflow for generatig laboratory notes from videos:
- Notebook for developing / debugging the lab note generation pipeline within the ADK workflow
    File: videoToLabNotes_adk_workflow.ipynb

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

#### `detect-secrets` hook
To set up a secret in your repository:
```bash
pip install detect-secrets
```
1. Generate a secrets.ini file with the secret. Take 'secrets.ini.example' as a template.
2. Run `detect-secrets scan --exclude-files testfiles --exclude-lines '"(hash|id|image/\w+)":.*' > .secrets.baseline` to scan your repository and create a .secrets.baseline file
(check `.pre-commit-config.yaml` for the exact parameters)
3. Run `detect-secrets audit .secrets.baseline` and check if the detected 'secret' is actually a secret
4. Commit the latest version of `.secrets.baseline`
