from NAPC import NAPC, conf

token = "put_your_ibm_token_here"

q = NAPC(runs=conf.runs, user_id=conf.user_id, token=token)

print("Get Result Simulator...")
q.get_qiskit_result("simulator")

print("Get Result...")
q.get_qiskit_result("real")