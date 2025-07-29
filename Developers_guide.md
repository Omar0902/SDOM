# GUIDELINES FOR DEVELOPING SDOM


## Table of Contents
- [GUIDELINES FOR DEVELOPING SDOM](#guidelines-for-developing-sdom)
- [clone SDOM repo](#clone-sdom-repo)
- [Setting up your enviroment](#setting-up-your-enviroment)
    - [Install uv](#install-uv)
    - [Install your local SDOM python module and pytest](#install-your-local-sdom-python-module-and-pytest)
- [Running tests locally](#running-tests-locally)
- [General Source code structure](#general-source-code-structure)


# clone SDOM repo
- Open VS code and use file -> open folder and select the folder where you want to copy the repo.
- Clone in your local the python version of SDOM repo:
```powershell
git clone https://github.com/Omar0902/SDOM.git
```

# Setting up your enviroment
## Install uv
- Install uv [(A python manager for virtual enviroments, installing packages etc)](https://pypi.org/project/uv/). 
```powershell
pip install uv
```
For further instructions click in the link above.

- Create a virtual enviroment ".venv"
```powershell
uv venv .venv
```
This command creates a new Python virtual environment in the `.venv` directory.

## Install your local SDOM python module and pytest
- To be able to run the tests locally and develop SDOM source code, install your local SDOM module by runing in your powershell terminal (Modify the folder address approprietly):
```powershell
uv pip install -e "C:\YOUR_PATH\SDOM"
```

- It will install also the SDOM dependencies. You should see something like this:

```powershell
 uv pip install -e "C:\YOUR_PATH\SDOM"
Resolved 9 packages in 1.90s
      Built sdom @ file:///C:/YOUR_PATH/SDOM
Prepared 1 package in 1.68s
Installed 9 packages in 1.60s
 + numpy==2.3.2
 + pandas==2.3.1
 + ply==3.11
 + pyomo==6.9.2
 + python-dateutil==2.9.0.post0
 + pytz==2025.2
 + sdom==0.0.1 (from file:///C:/YOUR_PATH/SDOM)
 + six==1.17.0
 + tzdata==2025.2
```

- Also, install pytests.py to be able to run the tests locally:
```powershell
uv pip install pytest
```

# Running tests locally
The SDOM python version source code have a folder called "tests". This folder contains all the scripts that contain the unit tests. 

- **Before to push and/or do a pull request please run all the tests scripts and make sure all the tests are passing sucessfully.**

- To run a test python script you can use:
```powershell
pytest tests/TEST_SCRIPT_NAME.py
```
- For instance to run the tests of the script called "test_no_resiliency_optimization_cases.py" you should run
```powershell
pytest tests/test_no_resiliency_optimization_cases.py
```
- This is an example of what you should see:
```powershell
pytest tests/test_no_resiliency_optimization_cases.py
================================================================== test session starts ==================================================================
platform win32 -- Python 3.12.4, pytest-8.4.1, pluggy-1.6.0
rootdir: C:\Users\smachado\repositories\pySDOM\SDOM
configfile: pyproject.toml
plugins: anyio-4.8.0, hydra-core-1.3.2
collected 2 items                                                                                                                                                                                                       

tests\test_no_resiliency_optimization_cases.py ..                                                                                                                                                                 [100%]

================================================================== 2 passed in 2.71s ===================================================================
```

# General Source code structure
To be updated....
Below is a diagram illustrating the general folder and script structure of the SDOM repository:

```
SDOM/
├── sdom/                # Main SDOM source code package
│   ├── __init__.py
│   ├── core.py
│   ├── utils.py
│   └── ...              # Other modules
├── tests/               # Unit tests for SDOM
│   ├── __init__.py
│   ├── test_core.py
│   └── ...              # Other test scripts
├── docs/                # Documentation files
│   └── Developers_guide.md
├── requirements.txt     # Python dependencies
├── pyproject.toml       # Project metadata and build configuration
└── README.md            # Project overview
```

> **Note:** The actual structure may include additional files or folders depending on the project's evolution.