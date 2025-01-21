"""
file name: triq_wrapper.py
author: Handy
date: 11 June 2024
"""
import subprocess as sp
import os
from .ir2dag import parse_ir
import time, json
import mysql.connector
from commons import Config

conf = Config()

triq_path = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(triq_path)
grandparent_dir = os.path.dirname(parent_dir)

#out_path = os.path.expanduser("./")
#dag_path = os.path.expanduser("./")
#map_path = os.path.expanduser("./")

out_path = grandparent_dir
dag_path = grandparent_dir
map_path = grandparent_dir

base_name = "output"
map_name = "init_mapo.map"
dag_name = base_name + ".in"
out_name = base_name + ".qasm"
dag_file_path = os.path.join(dag_path, dag_name)
out_file_path = os.path.join(out_path, out_name)
map_file_path = os.path.join(map_path, map_name)


def read_file(file_path):
    success = False
    while not success:
        try:
            with open(file_path, "r") as file:
                # Read the contents of the file and store them in the variable
                file_contents = file.read()
        except FileNotFoundError:
            print(f"File not found: {file_path}")
        except Exception as e:
            print(f"An error occurred: {str(e)}")

        success = True

    return file_contents

def create_dir(path):
    isExist = os.path.exists(path)
    if not isExist:
        # Create a new directory because it does not exist
        os.makedirs(path)

def generate_qasm(qasm_str, hardware_name, measurement_type):
    tmp_hw_name = hardware_name

    # parse qasm into .in
    parse_ir(qasm_str, os.path.join(dag_path, dag_name))

    # call triq
    call_triq = [os.path.join(triq_path, "triq"), 
                dag_file_path, 
                out_file_path, tmp_hw_name, str(0), map_file_path, measurement_type]
    
    #out_file=open("log/output.log",'w+')
    
    if not os.path.exists(os.path.join(triq_path, "log/")):
        os.makedirs(os.path.join(triq_path, "log/"))

    out_file=open(os.path.join(triq_path, "log/output.log"),'w+')

    p = sp.Popen(call_triq, stdout=out_file, text=True, shell=False)    
    p.communicate()
    p.terminate()
    p.wait()
    p.kill()

    result_qasm = read_file(out_file_path)

    return result_qasm

def run(qasm_str, hardware_name, measurement_type = "normal"):
    """
    Parameters:
        qasm_path:
        hardware_name:
    """
    
    result_qasm = generate_qasm(qasm_str, hardware_name, measurement_type)

    if (os.path.isfile(dag_file_path)):
        os.remove(dag_file_path)

    if (os.path.isfile(out_file_path)):
        os.remove(out_file_path)


    return result_qasm

def get_mapping():
    """

    """

    #log_path = os.path.expanduser("./log/output.log")
    log_path = os.path.join(triq_path, "log/output.log")
    

    mapping_dict = None
    with open(log_path, "r") as file:
        mapping_dict = json.load(file)


    return mapping_dict

def generate_initial_mapping_file(init_maps):
    string_maps = ', '.join(map(str, init_maps))
    # print("Initial mapping path :", string_maps)
    f = open(map_file_path, "w+")
    f.write(string_maps)
    f.close()

def generate_realtime_calibration_data(hw_name = conf.hardware_name):
    # Connect to the MySQL database
    conn = mysql.connector.connect(**conf.mysql_config)
    cursor = conn.cursor()

    # get last calibration id
    cursor.execute('''SELECT calibration_id, 2q_native_gates FROM ibm i
INNER JOIN hardware h ON i.hw_name = h.hw_name
WHERE i.hw_name = %s ORDER BY calibration_datetime DESC LIMIT 0, 1;
                    ''', (hw_name, ))
    results = cursor.fetchall()
    calibration_id, native_gates_2q = results[0]

    # get 1 qubit gate error
    cursor.execute('''SELECT calibration_id, qubit, 1 - x_error as fidelity_1q 
                   FROM ibm_one_qubit_gate_spec 
                   WHERE calibration_id = %s;
                    ''', (calibration_id, ))
    # print(calibration_id)
    results = cursor.fetchall()
    count = len(results)
    if count > 0:
        #f = open("./config/" + hw_name + "_real_S.rlb", "w+")
        f = open(os.path.join(grandparent_dir, "./config/" + hw_name + "_real_S.rlb"), "w+")
        
        f.write("{}\n".format(count))
        for res in results:
            calibration_id, qubit, fidelity_1q = res
            f.write("{} {} \n".format(qubit, fidelity_1q))

        f.close()

    # get 2 qubit gate error
    cursor.execute('''SELECT calibration_id, qubit_control, qubit_target, ROUND(1 - ''' + native_gates_2q + '''_error, 6) as fidelity_2q
                   FROM ibm_two_qubit_gate_spec 
                   WHERE calibration_id = %s ;
                    ''', (calibration_id, ))
    # AND ''' + native_gates_2q + '''_error != 1
    results = cursor.fetchall()
    count = len(results)
    if count > 0:
        #f = open("./config/" + hw_name + "_real_T.rlb", "w+")
        f = open(os.path.join(grandparent_dir, "./config/" + hw_name + "_real_T.rlb"), "w+")
        f.write("{}\n".format(count))
        for res in results:
            calibration_id, qubit_control, qubit_target, fidelity_2q = res

            if fidelity_2q <= 0:
                fidelity_2q = 0.001

            f.write("{} {} {} \n".format(qubit_control, qubit_target, fidelity_2q))

        f.close()

    # get readout error
    cursor.execute('''SELECT calibration_id, qubit, 1 - readout_error as readout_fidelity
                   FROM ibm_qubit_spec 
                   WHERE calibration_id = %s;
                    ''', (calibration_id, ))
    results = cursor.fetchall()
    count = len(results)
    if count > 0:
        #f = open("./config/" + hw_name + "_real_M.rlb", "w+")
        f = open(os.path.join(grandparent_dir, "./config/" + hw_name + "_real_M.rlb"), "w+")
        f.write("{}\n".format(count))
        for res in results:
            calibration_id, qubit, readout_fidelity = res
            f.write("{} {}\n".format(qubit, readout_fidelity))

        f.close()

    conn.close()
