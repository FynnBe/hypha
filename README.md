# Python Plugin Engine
The plugin engine used for running python plugins in https://imjoy.io

## Installation
  Download the latest ImJoyApp [here](https://github.com/oeway/ImJoy-Python/releases).

  Follow the instructions according to different operating systems.

## Installation (alternative solution)
  If you you have trouble in using the above ImJoyApp, do the following:
  * Download and install [Miniconda with Python 3.7](https://conda.io/miniconda.html) (or [Anaconda with Python 3.6](https://www.anaconda.com/download/) if you prefer a full installation). If you have installed any of these, please skip this step.
  * Start a **Terminal**(Mac and Linux) or **Anaconda Prompt**(Windows), then run the following command:

    ```conda -V && pip install -U git+https://github.com/oeway/ImJoy-Python#egg=imjoy```
  * If you encountered any error related to `git` or `pip`, try to run : `conda install -y git pip` before the above command. (Otherwise, please check **FAQs**.)
  * You can also use the same command if you want to upgrade the Plugin Engine to the latest version.

  To use it after the installation:
  * Run `python -m imjoy` in a **Terminal** or **Anaconda Prompt**, and keep the window running.
  * Go to https://imjoy.io, connect to the plugin engine. For the first time, you will be asked to fill a token generated by the plugin engine from the previous step.
  * Now you can start to use plugins written in Python.

## Upgrading

  Normally, the Plugin Engine will upgrade itself when it starts.
  In case you have problem with starting or upgrading the App, try to manually upgrade it by running the following command in a **Terminal**(Mac and Linux) or **Anaconda Prompt**(Windows):
  ```
  PATH=~/ImJoyApp/bin:$PATH pip install -U git+https://github.com/oeway/ImJoy-Python#egg=imjoy
  ```

## Accessing the ImJoyApp Conda environment
If you installed the Plugin Engine with the [ImJoyApp](https://github.com/oeway/ImJoy-Python/releases), it will setup an Miniconda environment located in `~/ImJoyApp`.

To access the environment on Linux and Mac, you just need to add `~/ImJoyApp/bin` to your `$PATH`:
```
export PATH=~/ImJoyApp/bin:$PATH

# now you can use `conda`, `pip`, `python` provided by the ImJoyApp 
which conda

```
For windows, you can use powershell to add the ImJoyApp to `$env.Path`:
```
$env:Path = '%systemdrive%%homepath%\ImJoyApp;%systemdrive%%homepath%\ImJoyApp\Scripts;' + $env:Path;
```

## More details and FAQs in [Docs](http://imjoy.io/docs/#/user-manual)
