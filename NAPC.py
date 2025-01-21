"""
file name: NAPC.py
author: Handy
date: 11 June 2024
"""
import wrappers.triq_wrapper as triq_wrapper
import wrappers.qiskit_wrapper as qiskit_wrapper
import wrappers.database_wrapper as database_wrapper
import glob, os
from commons import Config
from wrappers.qiskit_wrapper import QiskitCircuit
from qiskit_ibm_runtime import QiskitRuntimeService, Session
from qiskit_ibm_runtime import SamplerV2 as Sampler
from qiskit_ibm_runtime.options import SamplerOptions

from datetime import datetime
import mysql.connector
import time


from scheduler import check_result_availability, get_result, process_simulator, get_metrics

conf = Config()
debug = conf.activate_debugging_time

class NAPC:
    def __init__(self, runs=1, 
                 user_id = 1,
                 token=conf.qiskit_token,
                 skip_db=False,
                 hw_name = conf.hardware_name
                 ):

        self.session: Session = None
        self.service: QiskitRuntimeService = None
        self.real_backend = None
        self.backend = None
        self.program: (Sampler) = None

        self.conn = None
        self.cursor = None    

        self.circuit_name = None
        self.qasm = None 
        self.qasm_original = None 
        self.runs = runs
        
        self.header_id = None
        self.user_id = user_id
        self.token = token

        self.open_database_connection()


        self.set_service(hardware_name=hw_name, token=token)
        
        self.update_hardware_configs(hw_name)


    def open_database_connection(self):
        self.conn = mysql.connector.connect(**conf.mysql_config)
        self.cursor = self.conn.cursor()

    def close_database_connection(self):
        self.conn.commit()
        self.cursor.close()
        self.conn.close()

    def update_hardware_configs(self, hw_name = conf.hardware_name): 
        if debug: tmp_start_time  = time.perf_counter()
        triq_wrapper.generate_realtime_calibration_data(hw_name=hw_name)
        if debug: tmp_end_time = time.perf_counter()
        if debug: print("Time for update hardware configs: {} seconds".format(tmp_end_time - tmp_start_time))

    def set_service(self, hardware_name=conf.hardware_name, token=None):
        print("Connecting to quantum service...")
        if debug: tmp_start_time  = time.perf_counter()

        if token == None: token = self.token
        print("Saving IBM Account...")
        QiskitRuntimeService.save_account(channel="ibm_quantum", token=token, overwrite=True)
        self.service = QiskitRuntimeService(channel="ibm_quantum", token=token)
        
        print(f"Retrieving the real backend information of {hardware_name}...")
        self.real_backend = self.service.get_backend(hardware_name)
        
        if debug: tmp_end_time = time.perf_counter()
        if debug: print("Time for setup the services: {} seconds".format(tmp_end_time - tmp_start_time))

    def set_backend(self, program_type="sampler", backend=None, shots=conf.shots):
        
        if debug: tmp_start_time  = time.perf_counter()

        if backend == None: 
            self.backend = self.real_backend
        else:
            self.backend = backend
        
        if program_type == "sampler":
            options = SamplerOptions(
                default_shots=shots
            )
            self.program = Sampler(mode=self.backend, options=options) 

        
        if debug: tmp_end_time = time.perf_counter()
        if debug: print("Time for setup the backends: {} seconds".format(tmp_end_time - tmp_start_time))

    def get_circuit_properties(self, qasm_source):
        if "OPENQASM" in qasm_source:
            self.circuit_name = "Circuit_" + datetime.now().strftime("%Y%m%d%H%M%S")
        else:
            self.circuit_name = qasm_source.split("/")[-1].split(".")[0]

        qc = QiskitCircuit(qasm_source, name=self.circuit_name)
        self.qasm = qc.qasm
        self.qasm_original = qc.qasm_original
            
        database_wrapper.update_circuit_data(self.conn, self.cursor, qc)

        return qc


    def apply_qiskit(self, 
                     qasm = None,
                     compilation_name = "qiskit_3",
                     noise_level=None
                     ):

        if qasm is None:
            qasm = self.qasm

        qiskit_optimization_level = 3
        
        
        updated_qasm, compilation_time, initial_mapping = qiskit_wrapper.optimize_qasm(
            qasm, self.real_backend, qiskit_optimization_level)


        database_wrapper.insert_to_result_detail(self.conn, self.cursor, self.header_id, self.circuit_name, conf.noisy_simulator, noise_level, 
                                                    compilation_name, compilation_time, updated_qasm, initial_mapping)
            
        return updated_qasm, initial_mapping

    def apply_triq(self, compilation_name, qasm=None, layout="mapo", noise_level=None):   
        if qasm is None:
            qasm = self.qasm

        hardware_name = conf.hardware_name + "_" + "real"

        tmp_start_time  = time.perf_counter()

        initial_mapping = qiskit_wrapper.get_initial_mapping_sabre(
                qasm, self.real_backend)
        
        triq_wrapper.generate_initial_mapping_file(initial_mapping)

        updated_qasm = triq_wrapper.run(qasm, hardware_name, measurement_type=conf.triq_measurement_type)
        tmp_end_time = time.perf_counter()

        final_mapping = triq_wrapper.get_mapping()

        compilation_time = tmp_end_time - tmp_start_time
        
        compilation_name = layout + "_" + compilation_name
        
        database_wrapper.insert_to_result_detail(self.conn, self.cursor, self.header_id, self.circuit_name, conf.noisy_simulator, noise_level, 
                                                    compilation_name, compilation_time, updated_qasm, initial_mapping, final_mapping)

        return updated_qasm, initial_mapping

        
    def send_qasm_to_real_backend(self, program_type):
        if debug: tmp_start_time  = time.perf_counter()

        results_1 = database_wrapper.get_header_with_null_job(self.cursor)
        print("Total send to real backend :", len(results_1))
        for res_1 in results_1:
            header_id, qiskit_token, shots, runs = res_1

            # Set backend
            self.set_backend(program_type=program_type, shots=shots)

            results = database_wrapper.get_detail_with_header_id(self.cursor, header_id)
            
            success = False
            list_circuits = []

            for res in results:
                detail_id, updated_qasm, compilation_name = res

                qc = QiskitCircuit(updated_qasm)

                if compilation_name not in ("qiskit_3", "qiskit_0") or "nc" not in compilation_name:
                    circuit = qc.transpile_to_target_backend(self.real_backend)
                else:
                    circuit = qc.circuit_original

                for i in range(runs):
                    list_circuits.append(circuit)
                
            print("Total no of circuits :",len(list_circuits))
            while not success:
                try:

                    print("Sending to {} with batch id: {} ... ".format(conf.hardware_name, header_id))
                    job_id = None

                    if isinstance(self.program, Sampler):

                        job = self.program.run(list_circuits)
                        job_id = job.job_id()


                    success = True

                    # update to result detail
                    print("Sent!")
                    self.cursor.execute('UPDATE result_header SET job_id = %s, status = "pending", updated_datetime = NOW() WHERE id = %s', (job_id, header_id))

                    self.conn.commit()

                except Exception as e:
                    print(f"An error occurred: {str(e)}. Will try again in 30 seconds...")

                    for i in range(30, 0, -1):
                        time.sleep(1)
                        print(i)

        if debug: tmp_end_time = time.perf_counter()
        if debug: print("Time for sending to real backend: {} seconds".format(tmp_end_time - tmp_start_time))

    def run_on_noisy_simulator_local(self):
        if debug: tmp_start_time  = time.perf_counter()
        
        results_1 = database_wrapper.get_header_with_null_job(self.cursor)
        print("Total send to local simulator :", len(results_1))
        for res_1 in results_1:
            header_id, qiskit_token, shots, runs = res_1
            
            success = False

            while not success:
                try:

                    print("Running to {} with batch id: {} ... ".format("Local Simulator", header_id))

                    success = True

                    # update to result detail
                    print("Sent!")
                    self.cursor.execute('UPDATE result_header SET job_id = %s, status = "pending", updated_datetime = NOW() WHERE id = %s', ("simulator", header_id))

                    self.conn.commit()

                except Exception as e:
                    print(f"An error occurred: {str(e)}. Will try again in 30 seconds...")

                    for i in range(30, 0, -1):
                        time.sleep(1)
                        print(i)

        if debug: tmp_end_time = time.perf_counter()
        if debug: print("Time for sending to local simulator: {} seconds".format(tmp_end_time - tmp_start_time)) 

    def get_qasm_files_from_path(self, file_path = conf.base_folder):
        print(file_path)
        return glob.glob(os.path.expanduser(os.path.join(file_path, "*.qasm")))

    def compile(self, qasm, compilation_name, noise_level=None):

        updated_qasm = ""
        initial_mapping = ""
        if "qiskit" in compilation_name:
            updated_qasm, initial_mapping = self.apply_qiskit(qasm=qasm,  compilation_name=compilation_name, noise_level=noise_level)
        elif "triq" in compilation_name:
            tmp = compilation_name.split("_")
            layout = tmp[2]
            compilation = tmp[0] + "_" + tmp[1]
            updated_qasm, initial_mapping = self.apply_triq(qasm=qasm, compilation_name=compilation, layout=layout, noise_level=noise_level)

        return updated_qasm, initial_mapping
    

#region Run
    def run_simulator(self, program_type, qasm_files, compilations, noise_levels, shots, 
                      hardware_name = conf.hardware_name):
        """
        
        """
        print("Start running the simulator...")
        
        # this function always run on a simulator
        conf.noisy_simulator = True

        # init header
        self.header_id = database_wrapper.init_result_header(self.cursor, self.user_id, hardware_name = hardware_name,
                                                                 token=self.token, shots=shots, program_type=program_type)

        for idx, qasm in enumerate(qasm_files):
            qc = self.get_circuit_properties(qasm_source=qasm)

            for comp in compilations:

                for noise_level in noise_levels:
                    print(comp, noise_level)
                    noise_model, noisy_simulator, coupling_map = qiskit_wrapper.get_noisy_simulator(self.real_backend, noise_level)

                    # set the backend and the program
                    self.set_backend(program_type=program_type, backend=noisy_simulator, shots=shots)

                    updated_qasm, initial_mapping = self.compile(qasm=qc.qasm_original, compilation_name=comp, noise_level=noise_level)

        # Send to local simulator
        self.run_on_noisy_simulator_local()
                  

        # return df
    
    def send_to_real_backend(self, program_type, qasm_files, compilations, shots=conf.shots, hardware_name = conf.hardware_name):
        # Update the database
        conf.hardware_name = hardware_name

        # init header
        self.header_id = database_wrapper.init_result_header(self.cursor, self.user_id, hardware_name=hardware_name, token=self.token, shots=shots)

        for qasm in qasm_files:
            skip = False
            if "polar" in qasm:
                skip = True

            qc = self.get_circuit_properties(qasm_source=qasm)
            
            for comp in compilations:
                print("Compiling circuit: {} for compilation: {}".format(self.circuit_name, comp))
                self.compile(qasm=qc.qasm_original, compilation_name=comp)


        # Send to backend
        self.send_qasm_to_real_backend(program_type)
            
                
#endregion

    def get_qiskit_result(self, type=None, noisy_simulator=None):
        pending_jobs = database_wrapper.get_pending_jobs()
            
        tmp_qiskit_token = ""
        header_id, job_id, qiskit_token = None, None, None
        service = None
        
        print('Pending jobs: ', len(pending_jobs))
        for result in pending_jobs:
            header_id, job_id, qiskit_token, hw_name = result

            # print("processing...", header_id, job_id, qiskit_token)

            if type == "simulator" and job_id != "simulator":
                continue

            if type == "real" and job_id == "simulator":
                continue

            if tmp_qiskit_token == "" or tmp_qiskit_token != qiskit_token:
                QiskitRuntimeService.save_account(channel="ibm_quantum", token=qiskit_token, overwrite=True)
                service = QiskitRuntimeService(channel="ibm_quantum", token=qiskit_token)

            if job_id == "simulator":
                process_simulator(service, header_id, job_id, hw_name, noisy_simulator=noisy_simulator)
            else:
                job = service.job(job_id)
                print("Checking results for: ", job_id, "with header id :", header_id, qiskit_token)

                if check_result_availability(job, header_id):
                    get_result(job)

            tmp_qiskit_token = qiskit_token

        executed_jobs = database_wrapper.get_executed_jobs()
        print('Executed jobs :', len(executed_jobs))
        for result in executed_jobs:
            header_id, job_id = result
            try:
                get_metrics(header_id, job_id)
            except Exception as e:
                print("Error metric:", str(e))
