import os
import subprocess
import sys

def check_command(cmd):
    return subprocess.call(f"type {cmd}", shell=True,
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL) == 0

def install_pip_packages():
    subprocess.call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])

def start_docker_services():
    subprocess.call(["docker-compose", "up","-d"])

if __name__ == "__main__":
    print("🚀 Checking your environment...")

    if not check_command("docker"):
        print("❌ Docker is not installed! Please install Docker manually.")
        sys.exit(1)
    else:
        print("✅ Docker is installed.")
    if not check_command("docker-compose"):
        print("❌ Docker Compose not found! Installing...")
        subprocess.call(["brew", "install", "docker-compose"])

    print("📦 Installing required Python packages...")
    install_pip_packages()

    print("🐳 Starting Kafka and Zookeeper with Docker Compose...")
    start_docker_services()

    print("✅ Setup complete! You are ready to run the backend server.")

    print("🚀 Starting backend server...")
    subprocess.call(["uvicorn", "backend.main:app", "--reload"])
