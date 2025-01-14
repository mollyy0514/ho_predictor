import os
import json
import subprocess
import multiprocessing
import numpy as np
class TestActor:
    def __init__(self) -> None:
        pass
    def do_action(self, dev, pred_output):
        pairs = [dev, {"rlf": pred_output}, {"lte_cls": 0}, {"nr_cls": 0}, {}, []]
        script_folder = os.path.dirname(os.path.abspath(__file__))
        parent_folder = os.path.dirname(script_folder)
        local_file_path = os.path.join('/home/wmnlab/Data', f'record_pair.json')
        android_file_path = os.path.join('/sdcard/Data', f'record_pair.json')
        send_proc = multiprocessing.Process(target=self.send_pairs_to_phone, args=(pairs, parent_folder, local_file_path, android_file_path, dev))
        send_proc.start()

    def send_pairs_to_phone(pairs, parent_folder, local_file_path, android_file_path, dev):
        try:
            def convert_item(item):
                if isinstance(item, (np.float32, np.float64)):
                    return float(item)
                elif isinstance(item, dict):
                    return {key: (float(value) if isinstance(value, (np.float32, np.float64)) else value) for key, value in item.items()}
                return item

            converted_list = [convert_item(item) for item in pairs]

            # Step 1: Overwrite the local file with the new string
            with open(local_file_path, 'w') as f:
                json.dump(converted_list, f)

            d2s_path = os.path.join(parent_folder, 'device_setting.json')
            with open(d2s_path, 'r') as f:
                device_to_serial = json.load(f)
                # Step 2: Use adb to push the file to the Android device
                # processes = []
                adb_push_cmd = f"adb -s {device_to_serial[dev]} push {local_file_path} {android_file_path}"
                process = subprocess.Popen(adb_push_cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                # processes.append(process)

        except subprocess.CalledProcessError as e:
            print(f"An error occurred while executing adb commands: {e}")
        except Exception as e:
            print(f"An error occurred: {e}")