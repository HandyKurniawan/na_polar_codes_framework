# TriQ 

This program is the modified version of this [project](https://github.com/prakashmurali/TriQ) where we adapted the feature of mid-circuit 
measurements and routing algorithm of Floyd-Warshall. Also, modification is needed to adapt to the Qiskit version 1.1.0.

## Calibration Data

TriQ requires calibration data to compile a quantum circuit. Here are the steps to set the config:

1. Retrieve calibration data from IBM. For example, here is the JSON file generated for ibm_sherbrooke

```python
json_url = "https://api-qcon.quantum-computing.ibm.com/api/Backends/ibm_sherbrooke/properties"
response = requests.get(json_url)
```

2. Retrieve the two-qubit gates error rate from the JSON file. For ibm_sherbrooke, you will find the ECR gate for the two-qubit gates.
The error rates will be under the `gates` properties with the name `ecr`. Once this is done,
the [config](https://github.com/HandyKurniawan/na_polar_codes_framework/blob/main/config/ibm_sherbrooke_real_T.rlb) file of the two-qubit gates needs to be updated.

3. Retrieve the readout error rate from the JSON file. For ibm_sherbrooke, you will find the ECR gate for the two-qubit gates.
The error rates will be under the `qubits` properties with the name `readout_error`. Once this is done,
the [config](https://github.com/HandyKurniawan/na_polar_codes_framework/blob/main/config/ibm_sherbrooke_real_M.rlb) file of the readout error rate needs to be updated.

With these steps, you are ready to use TriQ with the updated hardware information config. 

## Script

The script to retrieve the calibration data can be seen [here](https://github.com/HandyKurniawan/na_polar_codes_framework/blob/main/wrappers/triq_wrapper/retrieve_calibration_data.py).

The process to update the TriQ's config with the latest calibration data has been integrated into the framework. However, to update it independently, you can run this [script](https://github.com/HandyKurniawan/na_polar_codes_framework/blob/main/update_configs.py)

