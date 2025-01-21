from NAPC import NAPC, conf

token = "put_your_ibm_token_here"

def update_hardware_configs(hw_name):
    token = "put_your_ibm_token_here"

    conf.hardware_name = hw_name

    q = NAPC(runs=conf.runs, user_id=conf.user_id, token=token, hw_name=hw_name)
    conf.hardware_name = hw_name
    conf.triq_measurement_type = "polar_meas"
    
    # update TriQ configs from calibration data
    q.update_hardware_configs(hw_name=hw_name)


def run_simulation_one(hw_name, file_path, compilations, triq_measurement_type, repeat,
                       shots ):
    token = "put_your_ibm_token_here"

    conf.hardware_name = hw_name
    conf.triq_measurement_type = triq_measurement_type
    
    q = NAPC(runs=conf.runs, user_id=conf.user_id, token=token, hw_name=hw_name)
    conf.triq_measurement_type = triq_measurement_type
    conf.hardware_name = hw_name
    qasm_files = q.get_qasm_files_from_path(file_path)
    qasm_files = qasm_files*repeat
        
    q.set_backend(program_type="sampler", shots=shots)
    q.send_to_real_backend("sampler", qasm_files, compilations, hardware_name=hw_name, shots=shots)



def run_simulation_all(hw_name):
    
    update_hardware_configs(hw_name=hw_name)
    
    # # #region n2
    # Setup the object for n2_x
    run_simulation_one(hw_name, file_path="./QEC/polar_code/n2/x", 
                       compilations=["qiskit_3", "triq_avg_sabre", "triq_lcd_sabre"], triq_measurement_type="polar_meas", 
                       repeat=1, shots=10000 )

    # Setup the object for n2_z
    run_simulation_one(hw_name, file_path="./QEC/polar_code/n2/z", 
                       compilations=["triq_lcd_sabre", "triq_avg_sabre"], triq_measurement_type="polar_mix", 
                       repeat=1, shots=10000 )
    
    # Setup the object for n2_z_qiskit
    run_simulation_one(hw_name, file_path="./QEC/polar_code/n2/z_qiskit", 
                       compilations=["qiskit_3"], triq_measurement_type="polar_meas", 
                       repeat=1, shots=10000 )

    #end region n2

    # #region n3
    # Setup the object for n3_x
    run_simulation_one(hw_name, file_path="./QEC/polar_code/n3/x", 
                       compilations=["qiskit_3", "triq_avg_sabre", "triq_lcd_sabre"], triq_measurement_type="polar_meas", 
                       repeat=1, shots=10000 )

    # Setup the object for n3_z
    run_simulation_one(hw_name, file_path="./QEC/polar_code/n3/z", 
                       compilations=["triq_lcd_sabre", "triq_avg_sabre"], triq_measurement_type="polar_mix", 
                       repeat=1, shots=10000 )
    
    # Setup the object for n3_z_qiskit
    run_simulation_one(hw_name, file_path="./QEC/polar_code/n3/z_qiskit", 
                       compilations=["qiskit_3"], triq_measurement_type="polar_meas", 
                       repeat=1, shots=10000 )

    # #endregion n3

    # #region n4

    # # Setup the object for n4
    run_simulation_one(hw_name, file_path="./QEC/polar_code/n4/x", 
                       compilations=["qiskit_3"], triq_measurement_type="polar_meas", 
                       repeat=1, shots=1000 )
    
    run_simulation_one(hw_name, file_path="./QEC/polar_code/n4/x", 
                       compilations=["triq_lcd_sabre"], triq_measurement_type="polar_meas", 
                       repeat=1, shots=1000 )
    
    run_simulation_one(hw_name, file_path="./QEC/polar_code/n4/x", 
                       compilations=["triq_avg_sabre"], triq_measurement_type="polar_meas", 
                       repeat=1, shots=1000 )
    
    run_simulation_one(hw_name, file_path="./QEC/polar_code/n4/z", 
                       compilations=["qiskit_3"], triq_measurement_type="polar_meas", 
                       repeat=1, shots=1000 )
    
    run_simulation_one(hw_name, file_path="./QEC/polar_code/n4/z", 
                       compilations=["triq_lcd_sabre"], triq_measurement_type="polar_meas", 
                       repeat=1, shots=1000 )
    
    run_simulation_one(hw_name, file_path="./QEC/polar_code/n4/z", 
                       compilations=["triq_avg_sabre"], triq_measurement_type="polar_meas", 
                       repeat=1, shots=1000 )

    # #endregion n4



try:
    run_simulation_all("ibm_brisbane")
    pass

except Exception as e:
    print(f"An error occurred: {str(e)}. Will try again in 30 seconds...")

q = NAPC(runs=conf.runs, user_id=conf.user_id, token=token)

print("Get Result...")
q.get_qiskit_result("real")