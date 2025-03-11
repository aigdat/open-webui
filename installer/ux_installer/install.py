#!/usr/bin/env python3
# Copyright(C) 2024-2025 Advanced Micro Devices, Inc. All rights reserved.
# SPDX-License-Identifier: MIT

"""
AMD AI UX Installer

This module provides functionality to install AMD AI UX (Open WebUI).
Similar to lemonade-install, it can be invoked from the command line.
"""

import argparse
import os
import sys
import json
import datetime
import subprocess
import platform
import shutil
import tempfile

try:
    import requests
except ImportError:
    print("ERROR: Required package 'requests' is not installed")
    print("Installing requests package...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "requests"])
    import requests

# Global constants
PRODUCT_NAME = "AMD AI UX"
PRODUCT_NAME_CONCAT = "AMD_AI_UX"
GITHUB_REPO = "https://github.com/aigdat/open-webui.git"
CONDA_ENV_NAME = "amd_ai_ux_env"
PYTHON_VERSION = "3.11"
ICON_FILE = "gaia.ico"

# Global log file path
LOG_FILE_PATH = None


def log(message, print_to_console=True):
    """
    Logs a message to both stdout and the log file if specified.

    Args:
        message: The message to log
        print_to_console: Whether to print the message to console
    """
    # Get current timestamp
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    formatted_message = f"[{timestamp}] [{PRODUCT_NAME_CONCAT}-Installer] {message}"

    # Print to console if requested
    if print_to_console:
        print(formatted_message)

    # Write to log file if it's set
    if LOG_FILE_PATH:
        try:
            with open(LOG_FILE_PATH, "a", encoding="utf-8") as f:
                f.write(formatted_message + "\n")
        except Exception as e:
            print(f"WARNING: Failed to write to log file: {str(e)}")


def check_conda():
    """
    Checks if conda is installed and available in the PATH.

    Returns:
        tuple: (bool, str) - (is_installed, conda_executable_path)
    """
    log("Checking if conda is installed...")
    
    try:
        # Try to find conda in the PATH
        if platform.system() == "Windows":
            result = subprocess.run(["where", "conda"], 
                                   capture_output=True, 
                                   text=True, 
                                   check=False)
        else:
            result = subprocess.run(["which", "conda"], 
                                   capture_output=True, 
                                   text=True, 
                                   check=False)
        
        if result.returncode == 0:
            conda_path = result.stdout.strip().split("\n")[0]
            log(f"Conda found at: {conda_path}")
            return True, conda_path
        else:
            log("Conda not found in PATH")
            return False, None
            
    except Exception as e:
        log(f"Error checking for conda: {str(e)}")
        return False, None


def install_miniconda(install_dir):
    """
    Downloads and installs Miniconda.

    Args:
        install_dir: Directory where to install Miniconda

    Returns:
        tuple: (bool, str) - (success, conda_executable_path)
    """
    log("-------------")
    log("- Miniconda -")
    log("-------------")
    log("Downloading Miniconda installer...")
    
    try:
        # Determine the appropriate Miniconda installer based on the OS
        if platform.system() == "Windows":
            installer_url = "https://repo.anaconda.com/miniconda/Miniconda3-latest-Windows-x86_64.exe"
            installer_path = os.path.join(tempfile.gettempdir(), "Miniconda3-latest-Windows-x86_64.exe")
        elif platform.system() == "Darwin":  # macOS
            if platform.machine() == "arm64":  # Apple Silicon
                installer_url = "https://repo.anaconda.com/miniconda/Miniconda3-latest-MacOSX-arm64.sh"
            else:  # Intel Mac
                installer_url = "https://repo.anaconda.com/miniconda/Miniconda3-latest-MacOSX-x86_64.sh"
            installer_path = os.path.join(tempfile.gettempdir(), "Miniconda3-latest-MacOSX.sh")
        else:  # Linux
            installer_url = "https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh"
            installer_path = os.path.join(tempfile.gettempdir(), "Miniconda3-latest-Linux-x86_64.sh")
        
        # Download the installer
        log(f"Downloading from: {installer_url}")
        response = requests.get(installer_url, stream=True)
        response.raise_for_status()
        
        with open(installer_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        
        log(f"Downloaded installer to: {installer_path}")
        
        # Install Miniconda
        if platform.system() == "Windows":
            miniconda_path = os.path.join(os.path.expanduser("~"), "miniconda3")
            log(f"Installing Miniconda to: {miniconda_path}")
            
            # Run the installer silently
            result = subprocess.run([
                installer_path, 
                "/InstallationType=JustMe", 
                "/AddToPath=1", 
                "/RegisterPython=0", 
                "/S", 
                f"/D={miniconda_path}"
            ], check=False)
            
            if result.returncode != 0:
                log(f"Miniconda installation failed with code: {result.returncode}")
                return False, None
                
            conda_path = os.path.join(miniconda_path, "Scripts", "conda.exe")
        else:
            # Unix-like systems (Linux, macOS)
            miniconda_path = os.path.join(os.path.expanduser("~"), "miniconda3")
            log(f"Installing Miniconda to: {miniconda_path}")
            
            # Make the installer executable
            os.chmod(installer_path, 0o755)
            
            # Run the installer in batch mode
            result = subprocess.run([
                installer_path, 
                "-b", 
                "-p", 
                miniconda_path
            ], check=False)
            
            if result.returncode != 0:
                log(f"Miniconda installation failed with code: {result.returncode}")
                return False, None
                
            conda_path = os.path.join(miniconda_path, "bin", "conda")
        
        log("Miniconda installation completed successfully")
        
        # Initialize conda
        log("Initializing conda...")
        if platform.system() == "Windows":
            subprocess.run([conda_path, "init"], check=False)
        else:
            subprocess.run([conda_path, "init", "bash"], check=False)
            subprocess.run([conda_path, "init", "zsh"], check=False)
        
        return True, conda_path
        
    except Exception as e:
        log(f"Error installing Miniconda: {str(e)}")
        return False, None


def create_conda_env(conda_path, env_path, python_version=PYTHON_VERSION):
    """
    Creates a new conda environment with the specified Python version.

    Args:
        conda_path: Path to the conda executable
        env_path: Path where to create the environment
        python_version: Python version to install

    Returns:
        bool: True if successful, False otherwise
    """
    log("---------------------")
    log("- Conda Environment -")
    log("---------------------")
    
    try:
        log(f"Creating a Python {python_version} environment at: {env_path}")
        
        # Create the conda environment
        result = subprocess.run([
            conda_path, 
            "create", 
            "-p", 
            env_path,
            f"python={python_version}", 
            "-y"
        ], capture_output=True, text=True, check=False)
        
        if result.returncode != 0:
            log(f"Failed to create conda environment: {result.stderr}")
            return False
            
        log(f"Successfully created conda environment at: {env_path}")
        return True
        
    except Exception as e:
        log(f"Error creating conda environment: {str(e)}")
        return False


def download_latest_wheel(output_folder, output_filename=None):
    """
    Downloads the latest Open WebUI wheel file from GitHub releases.

    Args:
        output_folder: Folder where to save the wheel file
        output_filename: Optional specific filename for the downloaded wheel

    Returns:
        Path to the downloaded wheel file or None if download failed
    """
    log("******************************")
    log("* Open WebUI Download Module *")
    log("******************************")
    log("Downloading the latest Open WebUI wheel file...")

    # Create output folder if it doesn't exist
    os.makedirs(output_folder, exist_ok=True)

    # First try to get the latest release info from GitHub API
    api_url = "https://api.github.com/repos/aigdat/open-webui/releases/latest"
    log(f"Fetching latest release information from: {api_url}")

    try:
        response = requests.get(api_url, timeout=30)

        if response.status_code == 200:
            release_info = response.json()

            # Find the first .whl file in the assets
            wheel_asset = None
            for asset in release_info.get("assets", []):
                if asset["name"].endswith(".whl"):
                    wheel_asset = asset
                    break

            if wheel_asset:
                wheel_url = wheel_asset["browser_download_url"]
                wheel_name = wheel_asset["name"]
                log(f"Found wheel file: {wheel_name}")
                log(f"Download URL: {wheel_url}")

                # Use provided output filename or the original filename
                final_filename = output_filename if output_filename else wheel_name
                output_path = os.path.join(output_folder, final_filename)

                # Download the wheel file
                log(f"Downloading wheel file to: {output_path}")
                wheel_response = requests.get(wheel_url, timeout=60)

                if wheel_response.status_code == 200:
                    with open(output_path, "wb") as f:
                        f.write(wheel_response.content)

                    # Verify file size
                    file_size = os.path.getsize(output_path)
                    log(f"Downloaded file size: {file_size} bytes")

                    if file_size < 10000:
                        log(
                            "ERROR: Downloaded file is too small, likely not a valid wheel file"
                        )
                        return None

                    log(f"Successfully downloaded wheel file to: {output_path}")
                    return output_path
                else:
                    log(
                        f"Failed to download wheel file. Status code: {wheel_response.status_code}"
                    )
            else:
                log("No wheel file found in the latest release assets")
        else:
            log(
                f"Failed to fetch release information. Status code: {response.status_code}"
            )
            try:
                error_info = response.json()
                log(f"Error details: {json.dumps(error_info, indent=2)}")
            except Exception as e:
                log(f"Response content: {response.text} with error: {str(e)}")

    except Exception as e:
        log(f"Error during API request or download: {str(e)}")

    return None


def install_wheel(wheel_path, python_path):
    """
    Installs the wheel file using pip.

    Args:
        wheel_path: Path to the wheel file to install
        python_path: Path to the Python executable to use

    Returns:
        bool: True if installation was successful, False otherwise
    """
    log("******************************")
    log("* Wheel File Installation *")
    log("******************************")

    wheel_path = os.path.normpath(wheel_path)

    try:
        log(f"Installing wheel from: {wheel_path}")
        log("This may take a few minutes. Please wait...")

        # Run pip install command with real-time output
        process = subprocess.Popen(
            [python_path, "-m", "pip", "install", wheel_path, "--verbose"],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            universal_newlines=True,
        )

        # Display output in real-time
        for line in process.stdout:
            line = line.strip()
            if line:
                log(line)

        # Wait for process to complete and get return code
        return_code = process.wait()

        # Check if installation was successful
        if return_code == 0:
            log("Open WebUI wheel file successfully installed")
            log("Installation completed successfully")
            return True
        else:
            log("ERROR: Failed to install Open WebUI wheel file")
            log(f"Pip installation returned error code: {return_code}")
            return False

    except Exception as e:
        log(f"ERROR: Exception during pip installation: {str(e)}")
        return False


def create_shortcuts(install_dir, env_path):
    """
    Creates desktop shortcuts for AMD AI UX.

    Args:
        install_dir: Installation directory
        env_path: Path to the conda environment

    Returns:
        bool: True if successful, False otherwise
    """
    log("Creating shortcuts...")
    
    try:
        if platform.system() == "Windows":
            # Create desktop shortcut
            desktop_path = os.path.join(os.path.expanduser("~"), "Desktop")
            shortcut_path = os.path.join(desktop_path, "AMD-AI-UX.lnk")
            
            # Use PowerShell to create the shortcut
            ps_command = f"""
            $WshShell = New-Object -comObject WScript.Shell
            $Shortcut = $WshShell.CreateShortcut("{shortcut_path}")
            $Shortcut.TargetPath = "cmd.exe"
            $Shortcut.Arguments = "/C conda activate {env_path} > NUL 2>&1 && start \"\" http://localhost:8080"
            $Shortcut.Save()
            """
            
            # Write the PowerShell script to a temporary file
            ps_script_path = os.path.join(tempfile.gettempdir(), "create_shortcut.ps1")
            with open(ps_script_path, "w", encoding="utf-8") as f:
                f.write(ps_command)
            
            # Execute the PowerShell script
            result = subprocess.run(["powershell", "-ExecutionPolicy", "Bypass", "-File", ps_script_path], capture_output=True, text=True, check=False)
            
            # Log the result of the PowerShell script execution
            if result.returncode != 0:
                log(f"PowerShell script failed with return code: {result.returncode}")
                log(f"PowerShell script stdout: {result.stdout}")
                log(f"PowerShell script stderr: {result.stderr}")
            else:
                log("PowerShell script executed successfully")
            
            # Clean up
            os.remove(ps_script_path)
            
            log(f"Created desktop shortcut at: {shortcut_path}")
            return True
        else:
            # For Linux/macOS, create a desktop entry
            log("Shortcut creation not implemented for this platform")
            return True
            
    except Exception as e:
        log(f"Error creating shortcuts: {str(e)}")
        return False


def main():
    """Main installation function."""
    # Set up argument parser
    parser = argparse.ArgumentParser(description=f"{PRODUCT_NAME} Installer")
    parser.add_argument(
        "--install-dir",
        dest="install_dir",
        default=os.path.join(os.path.expanduser("~"), "AppData", "Local", PRODUCT_NAME_CONCAT) if platform.system() == "Windows" 
                else os.path.join(os.path.expanduser("~"), PRODUCT_NAME_CONCAT),
        type=str,
        help=f"Installation directory (default: %LOCALAPPDATA%\\{PRODUCT_NAME_CONCAT} on Windows, ~/AMD_AI_UX on Unix)",
    )
    parser.add_argument(
        "--no-shortcuts",
        dest="no_shortcuts",
        action="store_true",
        help="Do not create desktop shortcuts",
    )
    parser.add_argument(
        "-y", "--yes",
        dest="yes",
        action="store_true",
        help="Answer 'yes' to all questions",
    )

    # Parse the arguments
    args = parser.parse_args()

    # Normalize the installation directory path
    install_dir = os.path.normpath(args.install_dir)
    
    # Set up the log file
    global LOG_FILE_PATH
    LOG_FILE_PATH = os.path.join(install_dir, f"{PRODUCT_NAME_CONCAT}_install.log")
    
    # Create the installation directory if it doesn't exist
    os.makedirs(install_dir, exist_ok=True)
    
    # Start the installation process
    log("*** INSTALLATION STARTED ***")
    log(f"Installing {PRODUCT_NAME} to: {install_dir}")
    
    # Check if directory already exists and has content
    if os.path.exists(install_dir) and os.listdir(install_dir):
        log(f"An existing installation was found at: {install_dir}")
        
        if not args.yes:
            user_input = input("Would you like to remove it and continue with the installation? (y/n): ")
            if user_input.lower() != 'y':
                log("Installation cancelled by user")
                return 1
        else:
            log("Automatically removing existing installation due to '--yes' flag")
        
        # Remove existing installation
        log("Removing existing installation...")
        
        # Try to remove the conda environment first
        env_path = os.path.join(install_dir, CONDA_ENV_NAME)
        if os.path.exists(env_path):
            conda_installed, conda_path = check_conda()
            if conda_installed:
                subprocess.run([conda_path, "env", "remove", "-p", env_path, "-y"], check=False)
        
        # Remove the installation directory
        try:
            shutil.rmtree(install_dir)
            os.makedirs(install_dir, exist_ok=True)
            log("Deleted all contents of install directory")
        except Exception as e:
            log(f"Failed to remove existing installation: {str(e)}")
            log("Please close any applications using AMD AI UX and try again")
            return 1
    
    # Check if conda is installed
    conda_installed, conda_path = check_conda()
    
    if not conda_installed:
        log("Conda not installed")
        
        if not args.yes:
            user_input = input("Conda is not installed. Would you like to install Miniconda? (y/n): ")
            if user_input.lower() != 'y':
                log("Installation cancelled by user")
                return 1
        
        # Install Miniconda
        miniconda_success, conda_path = install_miniconda(install_dir)
        
        if not miniconda_success:
            log("Failed to install Miniconda. Installation will be aborted.")
            return 1
    
    # Create conda environment
    env_path = os.path.join(install_dir, CONDA_ENV_NAME)
    env_success = create_conda_env(conda_path, env_path, PYTHON_VERSION)
    
    if not env_success:
        log("Failed to create the Python environment. Installation will be aborted.")
        return 1
    
    # Determine the Python executable path in the conda environment
    if platform.system() == "Windows":
        python_path = os.path.join(env_path, "python.exe")
    else:
        python_path = os.path.join(env_path, "bin", "python")
    
    # Create wheels directory
    wheels_dir = os.path.join(install_dir, "wheels")
    os.makedirs(wheels_dir, exist_ok=True)
    
    # Download the wheel file
    wheel_path = download_latest_wheel(output_folder=wheels_dir)
    
    if not wheel_path or not os.path.isfile(wheel_path):
        log("Failed to download Open WebUI wheel file. Please check your internet connection and try again.")
        return 1
    
    # Install the wheel file
    install_success = install_wheel(wheel_path, python_path)
    
    if not install_success:
        log("Failed to install Open WebUI wheel file. Please check the logs for details.")
        return 1
    
    # Create shortcuts if not disabled
    if not args.no_shortcuts:
        shortcut_success = create_shortcuts(install_dir, env_path)
        if not shortcut_success:
            log("Warning: Failed to create shortcuts")
    
    # Installation completed successfully
    log("*** INSTALLATION COMPLETED ***")
    log(f"{PRODUCT_NAME} installation completed successfully!")
    log(f"You can start {PRODUCT_NAME} by running:")
    log(f"  conda activate {env_path}")
    log("  open-webui")
    log("Or by using the desktop shortcut if created")
    
    return 0


if __name__ == "__main__":
    sys.exit(main()) 