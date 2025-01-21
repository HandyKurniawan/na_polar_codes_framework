import mysql.connector
import numpy as np
import json

from qiskit import *
from qiskit.result import *
from qiskit_ibm_runtime import QiskitRuntimeService, RuntimeJob, RuntimeJobV2
from qiskit.primitives import PrimitiveResult
from commons import (Config, get_count_1q, get_count_2q, convert_to_json, 
    get_initial_mapping_json, normalize_counts, convert_dict_int_to_binary, reverse_string_keys, 
    convert_dict_binary_to_int
)

import wrappers.qiskit_wrapper as qiskit_wrapper
import wrappers.polar_wrapper as polar_wrapper
import wrappers.database_wrapper as database_wrapper

from wrappers.qiskit_wrapper import QiskitCircuit

from qiskit.qasm2 import dumps
from qiskit_aer import AerSimulator

conf = Config()

def check_result_availability(job: (RuntimeJob | RuntimeJobV2), header_id):
    
    print("Job status :", job.status())

    if(job.errored() or job.cancelled()):
        database_wrapper.update_result_header_status_by_header_id(header_id, "error")
        return False

    if(not job.done()):
        return False

    if(job.done()):
        return True

def get_result(job: (RuntimeJob | RuntimeJobV2)):        
    try:
        conn = mysql.connector.connect(**conf.mysql_config)
        cursor = conn.cursor()

        job_id = job.job_id()

        # get list of detail_id here
        cursor.execute('''SELECT d.id, h.shots FROM result_header h 
INNER JOIN result_detail d ON h.id = d.header_id
WHERE h.status = %s AND h.job_id = %s;''', ('pending', job_id, ))
        results_details = cursor.fetchall()

        if (type(job.result()) is PrimitiveResult):
            # quasi_dists = job.result().quasi_dists
            job_results = job.result()

            avg_result = {}
            std_json = {}
            qasm_dict = {}
            no_of_optimization = len(results_details)
            no_of_result = len(job_results)
            runs = int(no_of_result / no_of_optimization)
            idx_1, idx_2 = 0, 0

            for idx, res in enumerate(results_details):
                detail_id, shots = res
                avg_result[detail_id] = []
                std_json[detail_id] = []
                qasm_dict[detail_id] = []
                sum_result = {}
                std_dev = {}
                std_dict = {}

                # to initialize the dict
                for j in range(runs):
                    res_dict = convert_dict_binary_to_int(job_results[idx_1].data.c.get_counts())

                    for key, value in res_dict.items():
                        key_bin = key
                        sum_result[key_bin] = 0
                        std_dict[key_bin] = 0
                        std_dev[key_bin] = []
                        
                    idx_1 += 1

                # to put them together
                for j in range(runs):
                    res_dict = convert_dict_binary_to_int(job_results[idx_2].data.c.get_counts())
                    
                    for key, value in res_dict.items():
                        key_bin = key
                        sum_result[key_bin] += (value / shots)
                        std_dev[key_bin].append((value / shots))
                        
                    idx_2 += 1
                    
                for key, value in sum_result.items():
                    sum_result[key] /= runs
                    std_dict[key] = np.std(std_dev[key])

                avg_result[detail_id] = convert_to_json(sum_result)
                std_json[detail_id] = convert_to_json(std_dict)
                qasm_dict[detail_id] = dumps(job.inputs["pubs"][idx_2-1][0])

            for idx, res in enumerate(results_details):
                detail_id, shots = res
                job_results = avg_result[detail_id]
                job_results_std = std_json[detail_id]
                qasm = qasm_dict[detail_id]
                mapping_json = get_initial_mapping_json(qasm)

                # check if the result_backend_json is already there, just update
                cursor.execute('SELECT detail_id FROM result_backend_json WHERE detail_id = %s', (detail_id,))
                existing_row = cursor.fetchone()

                if existing_row:
                    cursor.execute('''UPDATE result_backend_json SET quasi_dists = %s, quasi_dists_std = %s, qasm = %s, 
                    shots = %s, mapping_json = %s WHERE detail_id = %s;''',
                    (job_results, job_results_std, qasm, shots, mapping_json, detail_id))
                else:
                    cursor.execute('''INSERT INTO result_backend_json 
                                    (detail_id, quasi_dists, quasi_dists_std, qasm, shots, mapping_json) 
                                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)''',
                    (detail_id, job_results, job_results_std, qasm, shots, mapping_json))
                

                database_wrapper.update_result_header(cursor, job)

            conn.commit()
        
        else:
            pass

        cursor.close()
        conn.close()

    except Exception as e:
        print("Error for check result availability :", str(e))

def process_simulator(service:QiskitRuntimeService, header_id, job_id, hw_name, noisy_simulator = None):
    print("Checking results for: ", job_id, "with header id :", header_id)
    

    conn = mysql.connector.connect(**conf.mysql_config)
    cursor = conn.cursor()

    backend = None
    
    if noisy_simulator == None:
        backend = service.backend(hw_name)
    else:
        backend = noisy_simulator
        print(backend.backend_name)

    cursor.execute('''SELECT d.id, q.updated_qasm, d.compilation_name, d.noise_level, h.shots 
FROM result_detail d
INNER JOIN result_header h ON d.header_id = h.id
INNER JOIN result_updated_qasm q ON d.id = q.detail_id 
LEFT JOIN result_backend_json j ON d.id = j.detail_id
WHERE h.status = %s AND h.job_id = %s AND d.header_id = %s AND j.quasi_dists IS NULL  ''', ('pending', job_id, header_id,))
    results_details = cursor.fetchall()

    for idx, res in enumerate(results_details):

        try:

            detail_id, updated_qasm, compilation_name, noise_level, shots = res

            qc = QiskitCircuit(updated_qasm)

            circuit = qc.transpile_to_target_backend(backend)

            noiseless = False
            if noise_level == 0.0:
                noiseless = True
                print("Preparing the noiseless simulator", compilation_name, noise_level, noiseless)
                sim_ideal = AerSimulator()
                job = sim_ideal.run(circuit, shots=shots)
            elif noisy_simulator != None:
                print("Preparing the noisy simulator", backend.backend_name, compilation_name, noise_level, noiseless)
                job = backend.run(circuit, shots=shots)

            elif conf.user_id == 8:
                print("Preparing the noisy CX simulator", backend.name, compilation_name, noise_level, noiseless)

                sim_noisy = qiskit_wrapper.generate_sim_noise_cx(backend, noise_level)

                job = sim_noisy.run(circuit, shots=shots)

            else:
                print("Preparing the noisy simulator", backend.name, compilation_name, noise_level, noiseless)
                noise_model, sim_noisy, coupling_map = qiskit_wrapper.get_noisy_simulator(backend, noise_level, noiseless)
                job = sim_noisy.run(circuit, shots=shots)

            result = job.result()  
            output = result.get_counts()
            output_normalize = normalize_counts(output, shots=shots)

            quasi_dists = convert_to_json(output_normalize)
            quasi_dists_std = ""
            qasm = dumps(circuit)
            mapping_json = get_initial_mapping_json(qasm)


            # check if the result_backend_json is already there, just update
            cursor.execute('SELECT detail_id FROM result_backend_json WHERE detail_id = %s', (detail_id,))
            existing_row = cursor.fetchone()

            if existing_row:
                cursor.execute('''UPDATE result_backend_json SET quasi_dists = %s, quasi_dists_std = %s, qasm = %s, 
                shots = %s, mapping_json = %s WHERE detail_id = %s;''',
                (quasi_dists, quasi_dists_std, qasm, shots, mapping_json, detail_id))
            else:
                cursor.execute('''INSERT INTO result_backend_json 
                                (detail_id, quasi_dists, quasi_dists_std, qasm, shots, mapping_json) 
                                VALUES (%s, %s, %s, %s, %s, %s)''',
                (detail_id, quasi_dists, quasi_dists_std, qasm, shots, mapping_json))

            conn.commit()

        except Exception as e:
            print("Error happened: ", str(e))

    cursor.execute('UPDATE result_header SET status = "executed", updated_datetime = NOW() WHERE id = %s', (header_id,))
    conn.commit()

    cursor.close()
    conn.close()
    

def get_metrics(header_id, job_id):
    # print("")
    print("Getting qasm for :", header_id, job_id)
    conn = mysql.connector.connect(**conf.mysql_config)
    cursor = conn.cursor()

    try:
        cursor.execute('''SELECT j.detail_id, j.qasm, j.quasi_dists, j.quasi_dists_std, d.circuit_name, 
                       d.compilation_name, d.noise_level, j.shots 
                       FROM result_backend_json j
        INNER JOIN result_detail d ON j.detail_id = d.id
        INNER JOIN result_header h ON d.header_id = h.id
        WHERE h.status = %s AND h.job_id = %s AND h.id = %s AND j.quasi_dists IS NOT NULL;''', ("executed", job_id, header_id))
        results_details_json = cursor.fetchall()

        for idx, res in enumerate(results_details_json):
            detail_id, qasm, quasi_dists, quasi_dists_std, circuit_name, compilation_name, noise_level, shots = res

            n = 2
            lstate = "Z"
            if "polar_all_meas" in circuit_name:
                tmp = circuit_name.split("_")
                n = int(tmp[3][1])
                if len(tmp) == 5:
                    lstate = tmp[4].upper()
            elif "polar" in circuit_name:
                tmp = circuit_name.split("_")
                n = int(tmp[1][1])
                if len(tmp) == 3:
                    lstate = tmp[2].upper()
            
            quasi_dists_dict = json.loads(quasi_dists) 
            count_dict = {}
            if (round(sum(quasi_dists_dict.values())) <= 1):
                for key, value in quasi_dists_dict.items():
                    count_dict[key] = value * shots
            else:
                count_dict = quasi_dists_dict

            qc = QuantumCircuit.from_qasm_str(qasm)
            qc = qiskit_wrapper.transpile_to_basis_gate(qc)
            total_gate = sum(qc.count_ops().values())
            total_one_qubit_gate = get_count_1q(qc)
            total_two_qubit_gate = get_count_2q(qc)
            circuit_depth = qc.depth()

            count_accept = 0
            count_logerror = 0
            count_undecided = None
            decoding_time = None
            detection_time = None

            if "polar_all_meas" in circuit_name:
                print("get metrics: n =", n, ", lstate =", lstate)
                # total_qubit = (2**n) * (n)
                if lstate == "X":
                    if n == 2:
                        total_qubit = 8
                    elif n == 3:
                        total_qubit = 20
                    elif n == 4:
                        total_qubit = 40
                else:
                    if n == 2:
                        total_qubit = 6
                    elif n == 3:
                        total_qubit = 12
                    elif n == 4:
                        total_qubit = 48
                    
                count_dict_bin = convert_dict_int_to_binary(count_dict, total_qubit)
                tmp = count_dict_bin
                          
                count_accept, count_logerror, count_undecided, success_rate_polar, detection_time, decoding_time = polar_wrapper.get_logical_error_on_accepted_states(n, lstate, tmp)
                print(circuit_name, noise_level, compilation_name, count_accept, count_logerror, count_undecided, success_rate_polar)

            elif "polar" in circuit_name:
                print("get metrics: n =", n, ", lstate =", lstate)
                if lstate == "X":
                    if n == 2:
                        total_qubit = 4
                    elif n == 3:
                        total_qubit = 12
                    elif n == 4:
                        total_qubit = 24
                else:
                    if n == 2:
                        total_qubit = 0
                    elif n == 3:
                        total_qubit = 4
                    elif n == 4:
                        total_qubit = 32
                    
                quasi_dists_dict_bin = convert_dict_int_to_binary(quasi_dists_dict, total_qubit)
                tmp = reverse_string_keys(quasi_dists_dict_bin)

                success_rate_polar = polar_wrapper.get_q1prep_sr(n, lstate, tmp)
                print(circuit_name, noise_level, compilation_name, success_rate_polar)


            # check if the metric is already there, just update
            cursor.execute('SELECT detail_id FROM metric WHERE detail_id = %s', (detail_id,))
            existing_row = cursor.fetchone()

            if existing_row:
                cursor.execute("""UPDATE metric SET total_gate = %s, total_one_qubit_gate = %s, total_two_qubit_gate = %s, circuit_depth = %s, 
                success_rate_polar = %s, polar_count_accept = %s, polar_count_logerror = %s,
                polar_count_undecided = %s, detection_time = %s, decoding_time = %s 
                WHERE detail_id = %s; """, 
                (total_gate, total_one_qubit_gate, total_two_qubit_gate, circuit_depth, 
                success_rate_polar, count_accept, count_logerror, 
                count_undecided, detection_time, decoding_time, 
                detail_id))
                
            else:
                cursor.execute("""INSERT INTO metric(detail_id, total_gate, total_one_qubit_gate, total_two_qubit_gate, circuit_depth,  
                success_rate_polar, polar_count_accept, polar_count_logerror, 
                polar_count_undecided, detection_time, decoding_time)
                VALUES (%s, %s, %s, %s, %s,
                %s, %s, %s, 
                %s, %s, %s); """, 
                (detail_id, total_gate, total_one_qubit_gate, total_two_qubit_gate, circuit_depth, 
                success_rate_polar, count_accept, count_logerror, 
                count_undecided, detection_time, decoding_time))

            conn.commit()

        database_wrapper.update_result_header_status_by_header_id(header_id, 'done')

    except Exception as e:
        print("Error in getting the metrics : ", e)
    
    conn.commit()
    cursor.close()
    conn.close()
