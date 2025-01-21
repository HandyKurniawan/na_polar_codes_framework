import json
import configparser
import re
import os
from dateutil import tz
from datetime import datetime

class Config:
    def __init__(self):
        self.config_parser = configparser.ConfigParser()
        
        base_dir = os.path.dirname(os.path.abspath(__file__))
        parent_dir = os.path.dirname(base_dir)
        grandparent_dir = os.path.dirname(parent_dir)
        
        config_path = os.path.join(parent_dir, "config.ini")
        
        self.config_parser.read(config_path)

        self.mysql_config = {
            'user': self.config_parser['MySQLConfig']['user'],
            'password': self.config_parser['MySQLConfig']['password'],
            'host': self.config_parser['MySQLConfig']['host'],
            'database': self.config_parser['MySQLConfig']['database']
        }

        self.bit_format = self.config_parser['MathConfig']['bit_format']

        self.activate_debugging_time = True if self.config_parser['GeneralConfig']['activate_debugging_time'] == "1" else False

        quantum_config_name = "QuantumConfig"

        self.hardware_name = self.config_parser[quantum_config_name]['hardware_name']
        self.base_folder = self.config_parser[quantum_config_name]['base_folder']
        self.shots = int(self.config_parser[quantum_config_name]['shots'])
        self.qiskit_token = self.config_parser[quantum_config_name]['token']
        self.runs = int(self.config_parser[quantum_config_name]['runs'])
        self.user_id = int(self.config_parser[quantum_config_name]['user_id'])
        self.triq_measurement_type = self.config_parser[quantum_config_name]['triq_measurement_type']
        self.noisy_simulator = True if self.config_parser[quantum_config_name]['noisy_simulator'] == "1" else False
        
conf = Config()


def read_file(file_path):
    try:
        with open(file_path, "r") as file:
            return file.read()
    except FileNotFoundError as e:
        print(f"File not found: {file_path}")
    except Exception as e:
        print(f"An error occurred: {str(e)}")

def convert_to_json(dictiontary):
    return json.dumps(dictiontary, indent = 0) 

def normalize_counts(result_counts, is_json=False, shots=50000):
    if is_json:
        result_counts = json.loads(result_counts)

    result_counts = convert_dict_binary_to_int(result_counts)
    
    return {key: value / shots for key, value in result_counts.items()}

def is_decimal_number(s):
    try:
        float(s)
        return True
    except ValueError:
        return False

def is_binary_number(s):
    return all(char in '01' for char in s)

def convert_dict_binary_to_int(bin_dict):
    tmp = {}
    for key, value in bin_dict.items():
        if is_binary_number(key):
            new_key = "{}".format(int(key, 2))
            tmp[new_key] = value
    int_dict = tmp

    return int_dict

def convert_dict_int_to_binary(int_dict, n):
    tmp = {}
    
    bit_format = "0:0{}b".format(n)
    bit_format = "{" + bit_format + "}"
    
    for key, value in int_dict.items():
        int_key = int(key)
        new_key = bit_format.format(int_key)
        tmp[new_key] = value
    bin_dict = tmp

    return bin_dict

def reverse_string_keys(original_dict):
    reversed_dict = {}
    
    for key, value in original_dict.items():
        if isinstance(key, str):
            reversed_key = key[::-1]
        else:
            reversed_key = key  # Keep the key unchanged if it's not a string
            
        reversed_dict[reversed_key] = value

    return reversed_dict

def pad_fractional_seconds(datetime_str):
    # Split the string into date-time and timezone parts
    if '.' in datetime_str:
        date_part, frac_part = datetime_str.split('.')
        frac_seconds, tz = frac_part.split('Z')
        # Pad the fractional seconds to 6 digits
        padded_frac_seconds = frac_seconds.ljust(6, '0')
        # Reconstruct the datetime string
        padded_datetime_str = f"{date_part}.{padded_frac_seconds}Z"
    else:
        # If there are no fractional seconds, add them
        date_part, tz = datetime_str.split('Z')
        padded_datetime_str = f"{date_part}.000000Z"
    
    return padded_datetime_str

def convert_utc_to_local(datetime_utc):
    datetime_utc = pad_fractional_seconds(datetime_utc)

    to_zone = tz.tzlocal()

    datetime_local = datetime.fromisoformat(datetime_utc.replace('Z', '+00:00')).astimezone(to_zone)
    datetime_local = datetime_local.strftime("%Y%m%d%H%M%S")

    return datetime_local

def calculate_time_diff(time_start, time_end):
    time_start = pad_fractional_seconds(time_start)
    time_end = pad_fractional_seconds(time_end)

    start_datetime = datetime.fromisoformat(time_start.replace('Z', '+00:00'))
    end_datetime = datetime.fromisoformat(time_end.replace('Z', '+00:00'))
    time_difference = end_datetime - start_datetime

    return time_difference.total_seconds()    

def get_measure_lines(updated_qasm):
    lines = updated_qasm.split('\n')
    measure_lines = [line for line in lines if re.match(r'^\s*measure', line)]
    return measure_lines

def get_initial_mapping_json(updated_qasm):
    initial_mappings = []
    measure_lines = get_measure_lines(updated_qasm)
    for line in measure_lines:
        qubits = re.findall(r'q\[(\d+)\] -> c\[(\d+)\]', line)
        if len(qubits) == 1:
            initial_mappings.append((int(qubits[0][0]), int(qubits[0][1])))

    mapping = {}
    for i, j in initial_mappings:
        mapping[j] = i

    mapping_json = json.dumps(mapping, default=str)

    return mapping_json

def get_count_1q(qc):
    count_1q = 0
    for key, value in dict(qc.count_ops()).items():
        if key != 'cx' and key != "cy" and key != "cz" and key != "ch" and key != "crz" and key != "cp" and key != "cu" and key != "swap" and key != "ecr" and key != "measure":
            count_1q += value

    return count_1q

def get_count_2q(qc):
    count_2q = 0
    for key, value in dict(qc.count_ops()).items():
        if key == 'cx' or key == "cy" or key == "cz" or key == "ch" or key == "crz" or key == "cp" or key == "cu" or key == "swap" or key == "ecr":
            count_2q += value

    return count_2q

