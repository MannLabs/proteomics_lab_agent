# protemics_specialist

The [Mann Labs at the Max Planck Institute of Biochemistry](https://www.biochem.mpg.de/mann) developed protemics_specialist, a tool that ... To access all the hyperlinks in this document, please view it on [GitHub](https://github.com/MannLabs/proteomics_specialist).

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

protemics_specialist was developed by the [Mann Labs at the Max Planck Institute of Biochemistry](https://www.biochem.mpg.de/mann) and is freely available with an [Apache License 2.0](LICENSE.txt). External Python packages (available in the [requirements](requirements) folder) have their own licenses, which can be consulted on their respective websites.

---
## Installation

* [**Developer installer:**](#developer) Choose this installation if you are familiar with CLI tools, [conda](https://docs.conda.io/en/latest/), and Python. This installation allows access to all available features of protemics_specialist and even allows to modify its source code directly. Generally, the developer version of protemics_specialist outperforms the precompiled versions.

### Developer

protemics_specialist can also be installed in editable (i.e. developer) mode with a few `bash` commands. This allows to fully customize the software and even modify the source code to your specific needs. When an editable Python package is installed, its source code is stored in a transparent location of your choice. While optional, it is advised to first (create and) navigate to e.g. a general software folder:

```bash
mkdir ~/folder/where/to/install/software
cd ~/folder/where/to/install/software
```

***The following commands assume you do not perform any additional `cd` commands anymore***.

Next, download the protemics_specialist repository from GitHub either directly or with a `git` command. This creates a new protemics_specialist subfolder in your current directory.

```bash
git clone https://github.com/MannLabs/proteomics_specialist.git
```

For any Python package, it is highly recommended to use a separate [conda virtual environment](https://docs.conda.io/en/latest/), as otherwise *dependency conflicts can occur with already existing packages*.

```bash
conda create --name protemics_specialist python=3.8 -y
conda activate protemics_specialist
```

Finally, protemics_specialist and all its [dependencies](requirements) need to be installed.

```bash
pip install -e "./protemics_specialist"
```

By default this installs loose dependancies (no explicit versioning), although it is also possible to use stable dependencies (e.g. `pip install -e "./protemics_specialist[stable]"`).

***By using the editable flag `-e`, all modifications to the [protemics_specialist source code folder](protemics_specialist) are directly reflected when running protemics_specialist. Note that the protemics_specialist folder cannot be moved and/or renamed if an editable version is installed.***

---
## Usage

* [**Python**](#python-and-jupyter-notebooks)

### Python and Jupyter notebooks

protemics_specialist can be imported as a Python package into any Python script or notebook with the command `import protemics_specialist`.

An ‘nbs’ folder in the GitHub repository contains Jupyter Notebooks as tutorials on using protemics_specialist as a Python package.

---
## Troubleshooting

In case of issues, check out the following links:

* [FAQ](https://github.com/MannLabs/protemics_specialist#faq): This section provides answers to issues of general interest.
* [Issues](https://github.com/MannLabs/protemics_specialist/issues): Try a few different search terms to find out if a similar problem has been encountered before.

---
## FAQ
- Where to find test file?

---
## Citations

TBD.

---
## How to contribute

If you like this software, you can give us a [star](https://github.com/MannLabs/protemics_specialist/stargazers) to boost our visibility! All direct contributions are also welcome. Feel free to post a new [issue](https://github.com/MannLabs/protemics_specialist/issues) or clone the repository and create a [pull request](https://github.com/MannLabs/protemics_specialist/pulls) with a new branch. For even more interactive participation, check out the [the Contributors License Agreement](misc/CLA.md).


---
## Changelog

See the [HISTORY.md](HISTORY.md) for a complete overview of the changes made in each version.
