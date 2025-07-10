# proteomics_specialist

The [Mann Labs at the Max Planck Institute of Biochemistry](https://www.biochem.mpg.de/mann) developed proteomics_specialist, a tool that ... To access all the hyperlinks in this document, please view it on [GitHub](https://github.com/MannLabs/proteomics_specialist).

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

...

---
## License

proteomics_specialist was developed by the [Mann Labs at the Max Planck Institute of Biochemistry](https://www.biochem.mpg.de/mann) and is freely available with an [Apache License 2.0](LICENSE.txt). External Python packages (available in the [requirements](requirements) folder) have their own licenses, which can be consulted on their respective websites.

---
## Installation

* [**Developer installer:**](#developer) Choose this installation if you are familiar with CLI tools, [conda](https://docs.conda.io/en/latest/), and Python. This installation allows access to all available features of proteomics_specialist and even allows to modify its source code directly. Generally, the developer version of proteomics_specialist outperforms the precompiled versions.

### Project Structure

```
proteomics_specialist/
...
├── proteomics_specialist/   # Rout agent that can for instance connect to a remote MCP server such as AlphaKraken
│   ├── agent.py             # The ADK agent configured for a remote MCP
│   ├── prompt.py            # The prompt for the ADK agent
│   └── __init__.py
├── .env                     # For GOOGLE_API_KEY (ensure it's in .gitignore if repo is public) & a MONGODB_CONNECTION_STRING (for accessing the alphakraken database)
└── readme.md                # This file
```

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

## Setup Instructions

### 1. Prerequisites
- Python 3.11 or newer
- Access to a terminal or command prompt

### 2. Create and Activate Virtual Environment

It's highly recommended to use a virtual environment to manage project dependencies.

```bash
# Create a virtual environment (e.g., named .venv)
python3 -m venv .venv
```

Activate the virtual environment:

On macOS/Linux:
```bash
source .venv/bin/activate
```

On Windows:
```bash
.venv\Scripts\activate
```

### 3. Install Dependencies

Install proteomics_specialist and all its [dependencies](requirements):

```bash
pip install -e "./proteomics_specialist"
```

***By using the editable flag `-e`, all modifications to the [proteomics_specialist source code folder](proteomics_specialist) are directly reflected when running proteomics_specialist. Note that the proteomics_specialist folder cannot be moved and/or renamed if an editable version is installed.***

### 4. Set Up Gemini API Key (for the ADK Agent)

The ADK agent in this project uses a Gemini model. You'll need a Gemini API key.

1.  Create or use an existing [Google AI Studio](https://aistudio.google.com/) account.
2.  Get your Gemini API key from the [API Keys section](https://aistudio.google.com/app/apikeys).
3.  Set the API key as an environment variable. Create a `.env` file in the **root of the `proteomics_specialist` project** (i.e., next to the `proteomics_specialist` folder and `readme.md`):

    ```env
    # .env
    GOOGLE_API_KEY=your_gemini_api_key_here
    ```
    The `agent.py` will load this key.


### 5. Establish MCP server with Docker

Docker allows applications to be packaged and run in isolated environments called containers. Some MCP servers are distributed as Docker images, making them easy to run across different operating systems.

1.   **Installation**: Download and install Docker Desktop from the [official Docker website](https://www.docker.com/products/docker-desktop/). Docker Desktop is available for Windows, macOS, and Linux and provides a graphical interface as well as command-line tools.
2.   **Post-Installation**: Ensure Docker Desktop is running after installation, as this starts the Docker daemon (the background service that manages containers).
3.   **Verification**: Open a terminal or command prompt and verify the Docker installation by typing:
    ```bash
    docker --version
    # Run a test to ensure mongodb-mcp Docker is working correctly:
    docker run --rm -i mongodb/mongodb-mcp-server:latest 
    ```
    The first command should display your Docker version. Running `docker run ...` will download and run the mongodb-mcp-server, confirming this Docker container is operational.
4.  Set the 'mongodb conection string' as an environment variable.
    ```secrets.ini
    # secrets.ini
    MONGODB_CONNECTION_STRING = your_mongodb_conection_string_here
    ```
    The `agent.py` will also load this key.

### 6. Update packages regularly
```
pip install --upgrade google-adk
pip install google-adk[eval]
```

## Running the Agent and MCP Server

The ADK agent (`proteomics_specialist/agent.py`) is configured to automatically start the MCP server when it initializes its MCP toolset.

To run the agent:

1.  Ensure your virtual environment is active and you are in the root directory of the `proteomics_specialist` project.
2.  Execute the agent script:

    ```bash
    adk run proteomics_specialist
    # or
    adk web
    ```

This will:
- Start the adk agent.
- The agent, upon initializing the `MCPToolset`.
- The `MCP server will start and listen for tool calls from the agent via stdio.
- The agent will then be ready to process your instructions (which you would typically provide in a client application or test environment that uses this agent).

You should see log output from both the agent (if any) and the MCP server (in `proteomics_specialist/mcp_server_activity.log`.


---
## Usage

* [**Python**](#python-and-jupyter-notebooks)

### Python and Jupyter notebooks

proteomics_specialist can be imported as a Python package into any Python script or notebook with the command `import proteomics_specialist`.

An ‘nbs’ folder in the GitHub repository contains Jupyter Notebooks as tutorials on using proteomics_specialist as a Python package.

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

TBD.

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


---
## Changelog

See the [HISTORY.md](HISTORY.md) for a complete overview of the changes made in each version.
