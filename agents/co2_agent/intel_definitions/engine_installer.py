"""
Engine Installer Utility
Handles installation of runtime engines (Python, Node.js, etc.) at specified versions.
Supports Windows, Linux, and macOS platforms.
"""

import subprocess
import sys
import os
import platform
from typing import Tuple, Dict, Any


class EngineInstaller:
    """Handles installation and verification of runtime engines."""
    
    @staticmethod
    def get_platform() -> str:
        """Get current platform: 'windows', 'linux', or 'darwin'."""
        system = platform.system()
        if system == "Windows":
            return "windows"
        elif system == "Linux":
            return "linux"
        elif system == "Darwin":
            return "darwin"
        else:
            return system.lower()
    
    @staticmethod
    def run_command(command: str, shell: bool = True, timeout: int = 60) -> Tuple[int, str, str]:
        """
        Execute a shell command and return exit code, stdout, stderr.
        
        Args:
            command: Shell command to execute
            shell: Whether to execute through shell
            timeout: Command timeout in seconds
            
        Returns:
            Tuple of (exit_code, stdout, stderr)
        """
        try:
            result = subprocess.run(
                command,
                shell=shell,
                capture_output=True,
                text=True,
                timeout=timeout
            )
            return result.returncode, result.stdout, result.stderr
        except subprocess.TimeoutExpired:
            return -1, "", "Command timed out"
        except Exception as e:
            return -1, "", str(e)

    @staticmethod
    def command_exists(command: str) -> bool:
        """Return True when a command is available on PATH."""
        check_command = f"where {command}" if EngineInstaller.get_platform() == "windows" else f"command -v {command}"
        exit_code, _, _ = EngineInstaller.run_command(check_command)
        return exit_code == 0

    @staticmethod
    def privileged_prefix() -> Tuple[bool, str, str]:
        """Return the command prefix needed for package installs."""
        if EngineInstaller.get_platform() == "windows":
            return True, "", ""

        if hasattr(os, "geteuid") and os.geteuid() == 0:
            return True, "", ""

        if EngineInstaller.command_exists("sudo"):
            return True, "sudo ", ""

        return (
            False,
            "",
            "Package installation requires root privileges or sudo, but sudo was not found.",
        )

    @staticmethod
    def _version_from_command(command: str) -> Tuple[bool, str]:
        exit_code, stdout, stderr = EngineInstaller.run_command(f"{command} --version")
        if exit_code != 0:
            return False, stderr.strip() or f"{command} not found"

        return True, (stdout or stderr).strip()

    @staticmethod
    def _uv_command() -> str:
        """Return a uv command if uv is already available."""
        exit_code, _, _ = EngineInstaller.run_command("python -m uv --version")
        if exit_code == 0:
            return "python -m uv"

        if EngineInstaller.command_exists("uv"):
            return "uv"

        return ""

    @staticmethod
    def _ensure_uv() -> Tuple[bool, str, str]:
        """Ensure uv is available for standalone Python installs."""
        uv_command = EngineInstaller._uv_command()
        if uv_command:
            return True, uv_command, "uv is available"

        print("[INFO] Installing uv for standalone Python version management...")
        exit_code, stdout, stderr = EngineInstaller.run_command(
            f"{sys.executable} -m pip install uv",
            timeout=300,
        )
        if exit_code != 0:
            return False, "", f"uv install failed: {(stderr or stdout).strip()}"

        uv_command = EngineInstaller._uv_command()
        if uv_command:
            return True, uv_command, "uv installed successfully"

        return False, "", "uv was installed but could not be executed"

    @staticmethod
    def _find_python_with_uv(version: str) -> Tuple[bool, str]:
        uv_command = EngineInstaller._uv_command()
        if not uv_command:
            return False, "uv not available"

        exit_code, stdout, stderr = EngineInstaller.run_command(
            f"{uv_command} python find {version}"
        )
        if exit_code == 0 and stdout.strip():
            return True, stdout.strip()

        return False, (stderr or stdout).strip() or f"Python {version} not found by uv"
    
    @staticmethod
    def is_python_installed(version: str = None) -> Tuple[bool, str]:
        """
        Check if Python is installed, optionally verify specific version.
        
        Args:
            version: Optional version to check (e.g., "3.10", "3.9")
            
        Returns:
            Tuple of (is_installed, message)
        """
        candidates = []
        if version:
            candidates.extend([f"python{version}", f"python{version.replace('.', '')}"])
            if EngineInstaller.get_platform() == "windows":
                candidates.append(f"py -{version}")
        candidates.extend(["python", "python3"])

        checked = []
        installed_version = None

        for command in candidates:
            ok, output = EngineInstaller._version_from_command(command)
            if not ok:
                checked.append(f"{command}: {output}")
                continue

            parsed_version = output.replace("Python ", "").strip()
            checked.append(f"{command}: Python {parsed_version}")

            if not version:
                return True, f"Python {parsed_version} is installed"

            major_minor = ".".join(parsed_version.split(".")[:2])
            if major_minor == version:
                return True, f"Python {parsed_version} is installed"

            installed_version = installed_version or parsed_version

        if not installed_version:
            return False, "Python not found"
        
        if version:
            uv_found, uv_message = EngineInstaller._find_python_with_uv(version)
            if uv_found:
                return True, f"Python {version} is installed via uv at {uv_message}"

            return (
                False,
                f"Python {installed_version} found, but {version} required. Checked: {'; '.join(checked)}",
            )
        
        return True, f"Python {installed_version} is installed"
    
    @staticmethod
    def is_nodejs_installed(version: str = None) -> Tuple[bool, str]:
        """
        Check if Node.js is installed, optionally verify specific version.
        
        Args:
            version: Optional version to check (e.g., "16.0.0", "18.0.0")
            
        Returns:
            Tuple of (is_installed, message)
        """
        exit_code, stdout, stderr = EngineInstaller.run_command("node --version")
        
        if exit_code != 0:
            return False, "Node.js not found"
        
        installed_version = stdout.strip().replace("v", "")
        
        if version:
            # Check if installed version matches requested version (major.minor)
            installed_major_minor = ".".join(installed_version.split(".")[:2])
            requested_major_minor = ".".join(version.split(".")[:2])
            if installed_major_minor == requested_major_minor:
                return True, f"Node.js {installed_version} is installed"
            else:
                return False, f"Node.js {installed_version} found, but {version} required"
        
        return True, f"Node.js {installed_version} is installed"
    
    @staticmethod
    def install_python(version: str) -> Tuple[bool, str]:
        """
        Install specific Python version.
        
        Args:
            version: Python version to install (e.g., "3.10", "3.9")
            
        Returns:
            Tuple of (success, message)
        """
        platform_name = EngineInstaller.get_platform()
        
        # Check if already installed
        is_installed, check_msg = EngineInstaller.is_python_installed(version)
        if is_installed:
            return True, check_msg
        
        if platform_name == "windows":
            return EngineInstaller._install_python_windows(version)
        elif platform_name == "linux":
            return EngineInstaller._install_python_linux(version)
        elif platform_name == "darwin":
            return EngineInstaller._install_python_mac(version)
        else:
            return False, f"Unsupported platform: {platform_name}"
    
    @staticmethod
    def _install_python_windows(version: str) -> Tuple[bool, str]:
        """Install Python on Windows using nuget or direct download."""
        try:
            # Try using nuget package manager
            # First check if nuget is available
            exit_code, _, _ = EngineInstaller.run_command("nuget")
            
            if exit_code == 0:
                # Use nuget to install Python
                package_name = f"python.{version}"
                print(f"[INFO] Installing Python {version} using nuget...")
                exit_code, stdout, stderr = EngineInstaller.run_command(
                    f"nuget install {package_name}"
                )
                
                if exit_code == 0:
                    return True, f"Python {version} installed successfully"
                else:
                    return False, f"Nuget install failed: {stderr}"
            
            # Fallback: Try using chocolatey if available
            exit_code, _, _ = EngineInstaller.run_command("choco --version")
            
            if exit_code == 0:
                print(f"[INFO] Installing Python {version} using Chocolatey...")
                exit_code, stdout, stderr = EngineInstaller.run_command(
                    f"choco install python --version={version} -y"
                )
                
                if exit_code == 0:
                    return True, f"Python {version} installed successfully via Chocolatey"
                else:
                    return False, f"Chocolatey install failed: {stderr}"
            
            # Fallback: Try pyenv if available
            exit_code, _, _ = EngineInstaller.run_command("pyenv --version")
            
            if exit_code == 0:
                print(f"[INFO] Installing Python {version} using pyenv...")
                exit_code, stdout, stderr = EngineInstaller.run_command(
                    f"pyenv install {version}"
                )
                
                if exit_code == 0:
                    return True, f"Python {version} installed successfully via pyenv"
                else:
                    return False, f"pyenv install failed: {stderr}"
            
            return False, "No package manager found (nuget, Chocolatey, or pyenv). Please install manually."
        
        except Exception as e:
            return False, f"Error installing Python: {str(e)}"
    
    @staticmethod
    def _install_python_linux(version: str) -> Tuple[bool, str]:
        """Install Python on Linux using apt or yum."""
        try:
            # Try apt first (Debian/Ubuntu)
            exit_code, _, _ = EngineInstaller.run_command("command -v apt-get")
            
            if exit_code == 0:
                can_install, prefix, privilege_error = EngineInstaller.privileged_prefix()
                if not can_install:
                    return False, privilege_error

                # Convert version to package name (e.g., 3.10 -> python3.10)
                package_name = f"python{version}"
                print(f"[INFO] Installing Python {version} using apt...")
                exit_code, stdout, stderr = EngineInstaller.run_command(
                    f"{prefix}apt-get update && DEBIAN_FRONTEND=noninteractive {prefix}apt-get install -y {package_name}",
                    timeout=300,
                )
                
                if exit_code == 0:
                    verified, verify_msg = EngineInstaller.is_python_installed(version)
                    if verified:
                        return True, verify_msg
                    return False, f"Python package installed but version check failed: {verify_msg}"
                else:
                    details = (stderr or stdout).strip()
                    uv_success, uv_message = EngineInstaller._install_python_with_uv(version)
                    if uv_success:
                        return True, uv_message
                    return False, f"apt install failed: {details}. uv fallback failed: {uv_message}"
            
            # Try yum (RedHat/CentOS)
            exit_code, _, _ = EngineInstaller.run_command("command -v yum")
            
            if exit_code == 0:
                can_install, prefix, privilege_error = EngineInstaller.privileged_prefix()
                if not can_install:
                    return False, privilege_error

                package_name = f"python{version}"
                print(f"[INFO] Installing Python {version} using yum...")
                exit_code, stdout, stderr = EngineInstaller.run_command(
                    f"{prefix}yum install -y {package_name}",
                    timeout=300,
                )
                
                if exit_code == 0:
                    verified, verify_msg = EngineInstaller.is_python_installed(version)
                    if verified:
                        return True, verify_msg
                    return False, f"Python package installed but version check failed: {verify_msg}"
                else:
                    details = (stderr or stdout).strip()
                    uv_success, uv_message = EngineInstaller._install_python_with_uv(version)
                    if uv_success:
                        return True, uv_message
                    return False, f"yum install failed: {details}. uv fallback failed: {uv_message}"
            
            # Try pyenv
            exit_code, _, _ = EngineInstaller.run_command("pyenv --version")
            
            if exit_code == 0:
                print(f"[INFO] Installing Python {version} using pyenv...")
                exit_code, stdout, stderr = EngineInstaller.run_command(
                    f"pyenv install {version}"
                )
                
                if exit_code == 0:
                    return True, f"Python {version} installed successfully via pyenv"
                else:
                    return False, f"pyenv install failed: {stderr}"
            
            uv_success, uv_message = EngineInstaller._install_python_with_uv(version)
            if uv_success:
                return True, uv_message

            return False, f"No package manager found (apt, yum, or pyenv). uv fallback failed: {uv_message}"
        
        except Exception as e:
            return False, f"Error installing Python: {str(e)}"

    @staticmethod
    def _install_python_with_uv(version: str) -> Tuple[bool, str]:
        ok, uv_command, message = EngineInstaller._ensure_uv()
        if not ok:
            return False, message

        print(f"[INFO] Installing Python {version} using uv...")
        exit_code, stdout, stderr = EngineInstaller.run_command(
            f"{uv_command} python install {version}",
            timeout=300,
        )
        if exit_code != 0:
            return False, (stderr or stdout).strip()

        found, path_or_error = EngineInstaller._find_python_with_uv(version)
        if found:
            return True, f"Python {version} installed successfully via uv at {path_or_error}"

        return False, f"uv install completed, but verification failed: {path_or_error}"
    
    @staticmethod
    def _install_python_mac(version: str) -> Tuple[bool, str]:
        """Install Python on macOS using Homebrew or pyenv."""
        try:
            # Try Homebrew first
            exit_code, _, _ = EngineInstaller.run_command("command -v brew")
            
            if exit_code == 0:
                # For Homebrew, version format might need adjustment
                package_name = f"python@{version}"
                print(f"[INFO] Installing Python {version} using Homebrew...")
                exit_code, stdout, stderr = EngineInstaller.run_command(
                    f"brew install {package_name}"
                )
                
                if exit_code == 0:
                    return True, f"Python {version} installed successfully"
                else:
                    # Try without @ if that fails
                    return False, f"Homebrew install failed: {stderr}"
            
            # Try pyenv
            exit_code, _, _ = EngineInstaller.run_command("pyenv --version")
            
            if exit_code == 0:
                print(f"[INFO] Installing Python {version} using pyenv...")
                exit_code, stdout, stderr = EngineInstaller.run_command(
                    f"pyenv install {version}"
                )
                
                if exit_code == 0:
                    return True, f"Python {version} installed successfully via pyenv"
                else:
                    return False, f"pyenv install failed: {stderr}"
            
            return False, "No package manager found (Homebrew or pyenv). Please install manually."
        
        except Exception as e:
            return False, f"Error installing Python: {str(e)}"
    
    @staticmethod
    def install_nodejs(version: str) -> Tuple[bool, str]:
        """
        Install specific Node.js version.
        
        Args:
            version: Node.js version to install (e.g., "18.0.0", "16.0.0")
            
        Returns:
            Tuple of (success, message)
        """
        platform_name = EngineInstaller.get_platform()
        
        # Check if already installed
        is_installed, check_msg = EngineInstaller.is_nodejs_installed(version)
        if is_installed:
            return True, check_msg
        
        if platform_name == "windows":
            return EngineInstaller._install_nodejs_windows(version)
        elif platform_name == "linux":
            return EngineInstaller._install_nodejs_linux(version)
        elif platform_name == "darwin":
            return EngineInstaller._install_nodejs_mac(version)
        else:
            return False, f"Unsupported platform: {platform_name}"
    
    @staticmethod
    def _install_nodejs_windows(version: str) -> Tuple[bool, str]:
        """Install Node.js on Windows using Chocolatey, nuget, or nvm."""
        try:
            # Try Chocolatey
            exit_code, _, _ = EngineInstaller.run_command("choco --version")
            
            if exit_code == 0:
                print(f"[INFO] Installing Node.js {version} using Chocolatey...")
                exit_code, stdout, stderr = EngineInstaller.run_command(
                    f"choco install nodejs --version={version} -y"
                )
                
                if exit_code == 0:
                    return True, f"Node.js {version} installed successfully"
                else:
                    return False, f"Chocolatey install failed: {stderr}"
            
            # Try nvm-windows
            exit_code, _, _ = EngineInstaller.run_command("nvm --version")
            
            if exit_code == 0:
                print(f"[INFO] Installing Node.js {version} using nvm...")
                exit_code, stdout, stderr = EngineInstaller.run_command(
                    f"nvm install {version}"
                )
                
                if exit_code == 0:
                    return True, f"Node.js {version} installed successfully via nvm"
                else:
                    return False, f"nvm install failed: {stderr}"
            
            return False, "No package manager found (Chocolatey or nvm). Please install manually."
        
        except Exception as e:
            return False, f"Error installing Node.js: {str(e)}"
    
    @staticmethod
    def _install_nodejs_linux(version: str) -> Tuple[bool, str]:
        """Install Node.js on Linux using nvm or package manager."""
        try:
            # Try nvm
            exit_code, _, _ = EngineInstaller.run_command("nvm --version")
            
            if exit_code == 0:
                print(f"[INFO] Installing Node.js {version} using nvm...")
                exit_code, stdout, stderr = EngineInstaller.run_command(
                    f"nvm install {version}"
                )
                
                if exit_code == 0:
                    return True, f"Node.js {version} installed successfully via nvm"
                else:
                    return False, f"nvm install failed: {stderr}"
            
            # Try apt (Debian/Ubuntu)
            exit_code, _, _ = EngineInstaller.run_command("command -v apt-get")
            
            if exit_code == 0:
                can_install, prefix, privilege_error = EngineInstaller.privileged_prefix()
                if not can_install:
                    return False, privilege_error

                print(f"[INFO] Installing Node.js {version} using apt...")
                exit_code, stdout, stderr = EngineInstaller.run_command(
                    f"{prefix}apt-get update && DEBIAN_FRONTEND=noninteractive {prefix}apt-get install -y nodejs",
                    timeout=300,
                )
                
                if exit_code == 0:
                    verified, verify_msg = EngineInstaller.is_nodejs_installed(version)
                    if verified:
                        return True, verify_msg
                    return False, f"Node.js package installed but version check failed: {verify_msg}"
                else:
                    return False, f"apt install failed: {(stderr or stdout).strip()}"
            
            return False, "No package manager found (nvm or apt). Please install manually."
        
        except Exception as e:
            return False, f"Error installing Node.js: {str(e)}"
    
    @staticmethod
    def _install_nodejs_mac(version: str) -> Tuple[bool, str]:
        """Install Node.js on macOS using Homebrew or nvm."""
        try:
            # Try Homebrew
            exit_code, _, _ = EngineInstaller.run_command("command -v brew")
            
            if exit_code == 0:
                print(f"[INFO] Installing Node.js {version} using Homebrew...")
                exit_code, stdout, stderr = EngineInstaller.run_command(
                    f"brew install node@{version}"
                )
                
                if exit_code == 0:
                    return True, f"Node.js {version} installed successfully"
                else:
                    return False, f"Homebrew install failed: {stderr}"
            
            # Try nvm
            exit_code, _, _ = EngineInstaller.run_command("nvm --version")
            
            if exit_code == 0:
                print(f"[INFO] Installing Node.js {version} using nvm...")
                exit_code, stdout, stderr = EngineInstaller.run_command(
                    f"nvm install {version}"
                )
                
                if exit_code == 0:
                    return True, f"Node.js {version} installed successfully via nvm"
                else:
                    return False, f"nvm install failed: {stderr}"
            
            return False, "No package manager found (Homebrew or nvm). Please install manually."
        
        except Exception as e:
            return False, f"Error installing Node.js: {str(e)}"
    
    @staticmethod
    def install_engine(engine: str, version: str) -> Dict[str, Any]:
        """
        Main entry point: Install an engine at specified version.
        
        Args:
            engine: Engine name (e.g., "python", "node", "nodejs")
            version: Engine version (e.g., "3.10", "18.0.0")
            
        Returns:
            Dict with keys: status (bool), message (str), engine (str), version (str), installed (bool)
        """
        if not engine or not version:
            return {
                "status": False,
                "message": "Engine and version are required",
                "engine": engine,
                "version": version,
                "installed": False
            }
        
        engine = engine.lower().strip()
        version = version.strip()
        
        if engine in ["python", "py"]:
            success, message = EngineInstaller.install_python(version)
            return {
                "status": success,
                "message": message,
                "engine": "python",
                "version": version,
                "installed": success
            }
        
        elif engine in ["nodejs", "node", "js"]:
            success, message = EngineInstaller.install_nodejs(version)
            return {
                "status": success,
                "message": message,
                "engine": "nodejs",
                "version": version,
                "installed": success
            }
        
        else:
            return {
                "status": False,
                "message": f"Unsupported engine: {engine}. Supported: python, nodejs",
                "engine": engine,
                "version": version,
                "installed": False
            }


if __name__ == "__main__":
    # Test: Install Python 3.10
    print("Testing engine installer...")
    result = EngineInstaller.install_engine("python", "3.10")
    print(f"Result: {result}")
