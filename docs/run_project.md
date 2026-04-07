# Installation

There are 3 ways to use PaddleSpeech. According to the degree of difficulty, the 3 ways can be divided into Easy, Medium, and Hard. You can choose one of the 3 ways to install PaddleSpeech.

| Way     | Function                                                                                           | Support                                                                                                        |
|---------|----------------------------------------------------------------------------------------------------|----------------------------------------------------------------------------------------------------------------|
| Easy    | (1) Use command-line functions of PaddleSpeech. (2) Experience PaddleSpeech on Ai Studio.          | Linux, Mac (not support M1 chip), Windows (For more information, see #1195)                                    |
| Medium  | Support major functions such as using ready-made examples and using PaddleSpeech to train your model. | Linux, Mac (not support M1 chip, not support training models), Windows (not support training models)          |
| Hard    | Support full function of PaddleSpeech, including using join ctc decoder with kaldi(asr2), training n-gram language model, Montreal-Forced-Aligner, and so on. And you are more able to be a developer! | Ubuntu                                                                                                         |

## Prerequisites

- Python >= 3.7
- PaddlePaddle latest version (please refer to the Installation Guide)
- C++ compilation environment

> **Tip:** For Linux and Mac, do not use command `sh` instead of command `bash` in installation document.
>
> **Tip:** We recommend you to install paddlepaddle from https://mirror.baidu.com/pypi/simple and install paddlespeech from https://pypi.tuna.tsinghua.edu.cn/simple.

## Easy: Get the Basic Function (Support Linux, Mac, and Windows)

If you are new to PaddleSpeech and want to experience it easily without your machine, we recommend you to use AI Studio to experience it. There is a step-by-step tutorial for PaddleSpeech, and you can use the basic function of PaddleSpeech with a free machine.

If you want to use the command line function of PaddleSpeech, you need to complete the following steps to install PaddleSpeech. For more information about how to use the command line function, you can see the cli.

### Install Conda

Conda is a management system of the environment. You can go to miniconda (select a version py>=3.7) to download and install conda. Then install conda dependencies for PaddleSpeech:

```bash
conda install -y -c conda-forge sox libsndfile bzip2
```

### Install C++ Compilation Environment

(If you already have a C++ compilation environment, you can skip this step.)

#### Windows

You need to install Visual Studio to make the C++ compilation environment.

https://visualstudio.microsoft.com/visual-cpp-build-tools/

You can also see #1195 for more help.

#### Mac

```bash
brew install gcc
```

#### Linux

```bash
# centos
sudo yum install gcc gcc-c++
# ubuntu
sudo apt install build-essential
# Others
conda install -y -c gcc_linux-64=8.4.0 gxx_linux-64=8.4.0
```

### Install PaddleSpeech

Some users may fail to install kaldiio due to the default download source. You can install pytest-runner first:

```bash
pip install pytest-runner -i https://pypi.tuna.tsinghua.edu.cn/simple
```

Then you can use the following commands:

```bash
pip install paddlepaddle -i https://mirror.baidu.com/pypi/simple
pip install paddlespeech -i https://pypi.tuna.tsinghua.edu.cn/simple
```

You can also specify the version of paddlepaddle or install the develop version:

```bash
# install 2.4.1 version. Note: 2.4.1 is just an example, please follow the minimum dependency of paddlepaddle for your selection
pip install paddlepaddle==2.4.1 -i https://mirror.baidu.com/pypi/simple
# install develop version
pip install paddlepaddle==0.0.0 -f https://www.paddlepaddle.org.cn/whl/linux/cpu-mkl/develop.html
```

> **Note:** If you encounter a problem downloading nltk_data while using PaddleSpeech, it may be due to poor network. We suggest you download the nltk_data provided by us and extract it to your `${HOME}`.
>
> **Note:** If you fail to install paddlespeech-ctcdecoders, you only cannot use deepspeech2 model inference. For other models, it doesn't matter.

## Medium: Get the Major Functions (Support Linux, Mac, and Windows - not support training)

If you want to get the major functions of PaddleSpeech, you need to do the following steps:

### Git Clone PaddleSpeech

You need to git clone this repository first:

```bash
git clone https://github.com/PaddlePaddle/PaddleSpeech.git
cd PaddleSpeech
```

### Install Conda

Conda is a management system of the environment. You can go to miniconda to select a version (py>=3.7). For Windows, you can follow the installing guide step by step. For Linux and Mac, you can use the following commands:

```bash
# download miniconda
wget https://repo.continuum.io/miniconda/Miniconda3-latest-Linux-x86_64.sh -P tools/
# install miniconda
bash tools/Miniconda3-latest-Linux-x86_64.sh -b
# conda init
$HOME/miniconda3/bin/conda init
# activate conda
bash
```

Then you can create a conda virtual environment using the following command:

```bash
conda create -y -p tools/venv python=3.8
```

Activate the conda virtual environment:

```bash
conda activate tools/venv
```

Install conda dependencies for PaddleSpeech:

```bash
conda install -y -c conda-forge sox libsndfile swig bzip2
```

---

# Chinese Document to Audio Converter - User Guide

## Overview

This tool converts Chinese text documents to audio using PaddleSpeech TTS. It supports both direct text input and file processing.

## Installation Requirements

```bash
# Clone the repository (if applicable)
git clone <repository-url>
cd chinese-tts-converter

# Install dependencies
pip install paddlepaddle paddlespeech
# Additional dependencies may be required
```

## Basic Usage

### 1. Command Line Interface

**Direct text input:**
```bash
python main.py --text "你好，这是一个测试。" --output test.wav
```

**File input:**
```bash
python main.py --file input.txt --output output.wav
```

### 2. Voice Profile Selection

The current version supports basic voice selection:

```bash
# Use female voice profile
python main.py --file document.txt --output female_output.wav --profile female

# Use male voice profile
python main.py --file document.txt --output male_output.wav --profile male

# Use default voice
python main.py --file document.txt --output default_output.wav --profile default
```

### 3. Utility Commands

**List available options:**
```bash
python main.py --list-options
```

**Run system test:**
```bash
python main.py --test
```

### Example Command

```bash
python main.py --file C:\Users\Amaan\Documents\github_projects\tts_project\subtitles\chinese_text.txt --output C:\Users\Amaan\Documents\github_projects\tts_project\data\Modern_Woman_HORRIFIED_When_She_Discovers_Why_Her_Grandfathers_Generation_Had_Successful_Marriages.wav --profile male
```