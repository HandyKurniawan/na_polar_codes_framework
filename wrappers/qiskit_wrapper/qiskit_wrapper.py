"""
file name: qiskit_wrapper.py
author: Handy
date: 13 June 2024
"""
from qiskit import QuantumCircuit, transpile
from qiskit_aer.noise import NoiseModel
from qiskit_aer import AerSimulator
from qiskit.transpiler.preset_passmanagers import generate_preset_pass_manager
from commons import normalize_counts, Config
from qiskit.providers.models import BackendProperties
import json
import copy
from qiskit.qasm2 import dumps
import time


conf = Config()

class QiskitCircuit:
    def __init__(self, qasm, name = "circuit", metadata = {}):
        qc = None
        if isinstance(qasm, str):
            try:
                qc = QuantumCircuit.from_qasm_file(qasm)
            except Exception as e:
                try: 
                    qc = QuantumCircuit.from_qasm_str(qasm)
                except Exception as ex:
                    raise ValueError("Input circuit must be a string path to QASM file, QASM string or a QuantumCircuit object")
                
        if not (isinstance(qasm, str) or isinstance(qc, QuantumCircuit)):
            raise ValueError("Input must be a string or a QuantumCircuit object")

        self.qasm_original = dumps(qc)
        self.circuit_original = qc

        qc = transpile_to_basis_gate(qc)
        self.circuit: QuantumCircuit = qc
        self.qasm = dumps(qc)
        self.name = name
        self.circuit.name = name
        self.circuit.metadata = metadata
        self.gates = dict(qc.count_ops())
        self.total_gate = sum(qc.count_ops().values()) # - self.gates["measure"]
        self.depth = qc.depth()

    def get_native_gates_circuit(self, backend, simulator = False):
        if simulator:
            return transpile(self.circuit.decompose(), backend, basis_gates=["u3", "cx"], optimization_level=0, layout_method="trivial")
        else:
            return transpile(self.circuit.decompose(), backend, basis_gates=backend.basis_gates, optimization_level=0, layout_method="trivial")
            # return transpile(self.circuit.decompose(), backend=backend, optimization_level=0)
        
    def transpile_to_target_backend(self, backend):
        return transpile(self.circuit, backend=backend, optimization_level=0, layout_method="trivial")
    
    def get_qasm(self):
        return self.qasm

# Function to import and optimize a QASM circuit
def optimize_qasm(input_qasm, backend, optimization, initial_layout = None):
    # Load the input QASM circuit
    circuit = QuantumCircuit.from_qasm_str(input_qasm)

    tmp_start_time  = time.perf_counter()

    # Transpile and optimize the circuit
    pm = generate_preset_pass_manager(optimization_level=optimization,
                                        backend=backend,
                                        initial_layout=initial_layout
                                        )
    transpiled_circuit = pm.run(circuit)
    
    initial_mapping = get_initial_layout_from_circuit(transpiled_circuit)
        
    tmp_end_time = time.perf_counter()
    compilation_time = tmp_end_time - tmp_start_time

    # Convert the optimized circuit back to QASM
    optimized_qasm = dumps(transpiled_circuit)

    return optimized_qasm, compilation_time, initial_mapping



def get_initial_layout_from_circuit(qc):
    virtual_bits = qc.layout.initial_layout.get_virtual_bits()
    initial_layout_dict = {}
    initial_layout = []
    
    for key, value in virtual_bits.items():
        if "'q'" in "{}".format(key):
            initial_layout_dict[key._index] = value 
    
    for i in range(len(initial_layout_dict.keys())):
        initial_layout.append(initial_layout_dict[i])
    
    return initial_layout

def get_initial_mapping_sabre(input_qasm, backend):
    
    circuit = QuantumCircuit.from_qasm_str(input_qasm)

    pm = generate_preset_pass_manager(optimization_level=3,
                                        backend=backend
                                    )
    sabre_qc = pm.run(circuit)
    initial_layout = get_initial_layout_from_circuit(sabre_qc)

    return initial_layout

def transpile_to_basis_gate(circuit, backend = None ):
    
    # transpiled_circuit = transpile(circuit, optimization_level=0, basis_gates=backend.basis_gates)
    transpiled_circuit = transpile(circuit, optimization_level=0, basis_gates=["u3", "cx"])

    return transpiled_circuit

#region Noisy Simulator

def get_noisy_simulator(backend, error_percentage = 1, noiseless = False, method="automatic"):
    _backend = copy.deepcopy(backend)
    _properties = _backend.properties()
    _prop_dict = _properties.to_dict()
    
    # update readout error
    for i in _prop_dict["qubits"]:
        for j in i:
            if (j["name"] in ("readout_error", "prob_meas0_prep1", "prob_meas1_prep0")):
                new_val = j["value"] * error_percentage
                if new_val > 1:
                    new_val = 1
                j["value"] = 0
            elif (j["name"] in ("T1", "T2")):
                if error_percentage == 0:
                    new_val = j["value"]  / 0.00001
                else:
                    new_val = j["value"]  / error_percentage
                
                j["value"] = new_val
    
    # Update single qubit error
    for i in _prop_dict["gates"]:
        if(i["gate"] != "ecr"):
            pars = i["parameters"]
        
            for par in pars:
                if (par["name"] == "gate_error"):
                    new_val = par["value"] * error_percentage
                    if new_val > 1:
                        new_val = 1
                    par["value"] = 0
    
    # Update Two Qubit Error
    for i in _prop_dict["gates"]:
        if(i["gate"] == "ecr"):
            pars = i["parameters"]
    
            for par in pars:
                if (par["name"] == "gate_error"):
                    new_val = par["value"] * error_percentage
                    if new_val > 1:
                        new_val = 1
                    par["value"] = new_val
    
    new_properties = BackendProperties.from_dict(_prop_dict)
    new_prop_dict = new_properties.to_dict()
    new_prop_json = json.dumps(new_prop_dict, indent = 0, default=str) 
    new_prop_json = new_prop_json.replace("\n", "")

    coupling_map = _backend.configuration().coupling_map
    
    noise_model = NoiseModel.from_backend_properties(new_properties, dt = 0.1)
    
    if noiseless or error_percentage == 0.0:
        sim_noisy = AerSimulator()
    else:
        sim_noisy = AerSimulator(configuration=_backend.configuration(), properties=new_properties,
                                noise_model=noise_model, method = method
                                )
        sim_noisy.set_options(
            noise_model=noise_model,
            method = method
            )
    
    return noise_model, sim_noisy, coupling_map

#endregion
