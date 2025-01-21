import wrappers.qiskit_wrapper as qiskit_wrapper
from NAPC import NAPC, conf

token = "put_your_ibm_token_here"

# select compilation techniques
compilations = ["qiskit_3", "triq_avg_sabre", "triq_lcd_sabre"]

# Setup the object
q = NAPC(runs=conf.runs, user_id=conf.user_id, token=token)

# update TriQ configs from calibration data
q.update_hardware_configs()
