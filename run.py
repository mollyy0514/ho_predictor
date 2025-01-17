import os
import subprocess
from multiprocessing import Process

def run_device(device, password):
    """
    Function to run the Python script with a specific device parameter.
    """
    try:
        command = f"echo {password} | sudo -S python3 runner.py -d {device}"
        subprocess.run(command, shell=True, check=True)
    except subprocess.CalledProcessError as e:
        print(f"Error running device {device}: {e}")

def main(device_list):
    
    # Read the password from the file
    with open("password.txt", "r") as file:
        password = file.read().strip()
    
    # List to keep track of processes
    processes = []
    
    # Create and start a process for each device
    for device in device_list:
        print(f"Starting device {device}...")
        process = Process(target=run_device, args=(device, password))
        process.start()
        processes.append(process)
    
    # Wait for all processes to complete
    for process in processes:
        process.join()
    
    print("All processes have completed.")

if __name__ == "__main__":
    # List of devices
    device_list = ["sm02", "sm05"]
    main(device_list)
