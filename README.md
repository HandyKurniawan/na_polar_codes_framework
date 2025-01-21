# Noise-aware Compilation for State Preparation of Quantum Polar Codes (NAPC)
This repository contains the implementation of the proposed architecture from the paper "Implementing Quantum Polar Codes in a Superconducting Processor: From State Preparation to Decoding". 

![screen](https://github.com/HandyKurniawan/na_polar_codes_framework/blob/main/img/proposed_architecture.png)

## Table of contents

- [Setup](#setup)
- [Usage example](#usage-example)
- [Acknowledgments](#acknowledgments)
- [Contact information](#contact-information)

## Setup

### Installation

Note: This installation guide will work for Ubuntu 20.04 and Python 3.11.5

#### Clone Github

First, you need to clone the project to get all the necessary files

``` terminal
git clone https://github.com/HandyKurniawan/na_polar_codes_framework.git
cd na_polar_codes_framework
```

#### MariaDB

To set up the database, follow these steps:

1. Install MariaDB:
   
``` terminal
sudo apt update
sudo apt install mariadb-server
sudo systemctl start mariadb
sudo systemctl enable mariadb
```

2. Secure your MariaDB installation:

``` terminal
sudo mysql_secure_installation
```

3. Create a database and user:

Login with the root account to the database

``` terminal
mysql -u root -p
```

Then you can create a new user from here

``` mysql
CREATE USER 'user_1'@'%' IDENTIFIED BY '1234';
GRANT ALL PRIVILEGES ON *.* TO 'user_1'@'%';
GRANT ALL PRIVILEGES ON *.* TO 'user_1'@'localhost' IDENTIFIED BY '1234' WITH GRANT OPTION;
FLUSH PRIVILEGES;
CREATE DATABASE  IF NOT EXISTS `framework`;
exit;
```

4. Import table structures:

``` terminal
mysql -u user_1 -p framework < mariadb/framework_structure.sql
mysql -u user_1 -p framework < mariadb/data.sql
```
Note: These commands need to be run one by one, and the password for user_1 is 1234

Now your database is ready.

#### Framework

First, you need to go to the home folder of the project (\na_polar_codes_framework)

Note: If you have an older version (or if you don't have it) of Python please upgrade (install) it first:

``` terminal
sudo add-apt-repository ppa:deadsnakes/ppa    
sudo apt update  
sudo apt install python3.11
```

Install dependencies and set up the Python environment:

``` terminal
sudo apt-get update
sudo apt-get install python3.xx-venv 
sudo apt-get install libmuparser2v5
sudo apt-get install libz3-dev
python3.xx -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```
`Python3.xx` is depends on what Python3.xx version you have

#### Config

Now, you need to update the `config.ini` file to change the config for the database, and the path for the TriQ before continue

```terminal
[MySQLConfig]
user = user_1
password = 1234
host = localhost
database = framework
...
```

You can also set the default value in `config.ini` to compile the circuit:

```terminal
[QuantumConfig]
; put your IBM token here
token = put_your_ibm_token_here
; Which hardware to run the quantum circuit
hardware_name = ibm_sherbrooke
; Base folder to put the qasm files
base_folder = ./circuits/adder/
; Total number of shots
shots = 4000
; Number of duplication running the same circuits
runs = 1
...
```

#### Calibration Data

We need to update Triq's config based on the latest calibration data to properly run it. The script to retrieve calibration data from IBM can be seen [here](https://github.com/HandyKurniawan/na_polar_codes_framework/tree/main/wrappers/triq_wrapper) with file name `retrieve_calibration_data.py`. The calibration data will be saved in the database.

Now, you are good to go 🚀


## Usage example

We include a [demo](https://github.com/HandyKurniawan/na_polar_codes_framework/blob/main/demo.ipynb) Jupiter notebook for the full implementation of quantum polar codes of length N=18 and N=32, with options to run in the simulation and the real backends. Note: An IBM token is needed to run the demo.

### Example of running code of length N=16 (n=3) for logical |+> 

First, you need to import the installed framework, **NAPC**. The token is also needed since you need to run the simulator with the calibration-based noise model from IBM.

```python
from NAPC import NAPC, conf

# update with your IBM Token
token = "put_your_ibm_token_here"
```
Then, you need to initialize the NAPC object. _runs_ is a parameter to duplicate the circuits x numbers of times, and _token_ is the IBM token. 

```python
# initialize the object using the provided token
q = NAPC(runs=conf.runs, token=token)
```
Since noise-aware compilation needs the latest calibration data, you need to always check the latest calibration data and update TriQ configs through this function: `update_hardware_configs`

```python
# command to run the update TriQ's reliability matrix for the noise-aware routing
q.update_hardware_configs()
```

The framework will pick all the qasm files in the selected folders. In this case, it is the example of polar codes for logical + with length N=16 (n=3). This will return the paths of the files under the selected folders. 

```python
file_path="./QEC/polar_code/n3/x"
qasm_files = q.get_qasm_files_from_path(file_path)
```
TriQ has been updated to make it possible to apply mid-circuit measurement. For this purpose, you need to specify which qasm files need a mid-circuit measurement or not. All the other settings are:

- normal: only measurement at the end
- polar: for middle measurement circuit
- polar_meas: for polar with measurement
- polar_mix: for polar with measurement (no middle measurement)

See file [run_simulation.py](https://github.com/HandyKurniawan/na_polar_codes_framework/blob/main/run_simulation.py) to see which code lengths are needed for which triq measurement type.

```python
# this is the setup to enable mid-circuit measurement for TriQ
triq_measurement_type="polar_meas"
```
Now, you need to declare the physical error rate scaling factor, where **0** is noiseless, and **1** is standard noise. It can be set up from 0 to 1.

```python
# choosing the noise level
noise_levels = [0.1, 1.0]
```
And the final configuration part is to set the backend

```python
# then we setup the backend and run the simulator
q.set_backend(program_type="sampler", shots=shots)
```

To run the program to the **Simulator**, you can use this function

```python
q.run_simulator("sampler", qasm_files, compilations, noise_levels, shots)
```

while if you want to run in the **Real backend**, you can use this function

```python
q.send_to_real_backend("sampler", qasm_files, compilations, shots=shots)
```

When the result is ready, you can calculate or retrieve the result with this function. Note: for the simulator, the result will be simulated in this function.

```python
# get the result and calculate the metric
q.get_qiskit_result("simulator")
```
**Notes: choice of backend and number of shots can be changed from the `config.ini` file.**

### Accessing the result in the database

The full example can be seen in the [demo](https://github.com/HandyKurniawan/na_polar_codes_framework/blob/main/demo.ipynb) Jupiter notebook

```python
conn = mysql.connector.connect(**mysql_config)
cursor = conn.cursor()

sql = """
SELECT header_id, circuit_name, compilation_name, noise_level, 
polar_count_accept, polar_count_logerror, polar_count_undecided, success_rate_polar, total_two_qubit_gate,
initial_mapping
FROM result WHERE header_id = 2;
""".format(1, "ibm_sherbrooke")

 # insert to circuit
cursor.execute(sql)

results = cursor.fetchall()

cursor.close()
conn.close()
```


|header_id | circuit_name | compilation_name   |  noise_level |   count_accept |   count_logerror |   count_undecided |   success_polar |   total_gate_cx | initial_mappings |
|---|---------------------|--------------------|------|----------------|------------------|-------------------|-----------------|-----------------|------------------------------|
| 2 | polar_all_meas_n3_x | qiskit_3           |  0.1 |            996 |                4 |                 0 |        0.004016 |              11 | 123, 121, 122, 120, 118, 119 |
| 2 | polar_all_meas_n3_x | qiskit_3           |  1   |            944 |                4 |                 0 |        0.004237 |              11 | 123, 121, 122, 120, 118, 119 |
| 2 | polar_all_meas_n3_x | sabre_triq_lcd     |  0.1 |            998 |                4 |                 0 |        0.004008 |              11 | 123, 121, 122, 120, 118, 119 |
| 2 | polar_all_meas_n3_x | sabre_triq_lcd     |  1   |            951 |                4 |                 0 |        0.004206 |              11 | 123, 121, 122, 120, 118, 119 |




## Acknowledgments

This work was supported by the QuantERA project EQUIP (grants PCI2022-133004 and PCI2022-132922, funded by the Agencia Estatal de Investigación, Ministerio de Ciencia e Innovación, Gobierno de España, MCIN/AEI/10.13039/501100011033, and  ANR-22-QUA2-0005-01, funded by the Agence Nationale de la Recherche, France), and by the European Union "NextGenerationEU/PRTR". This research is part of the project PID2023-147059OB-I00 funded by MCIU/AEI/10.13039/501100011033/FEDER, UE. Handy Kurniawan acknowledges support from the Comunidad de Madrid under grant number PIPF-2023/COM-30051. Carmen G. Almudéver acknowledges support from the Spanish Ministry of Science, Innovation, and Universities through the Beatriz Galindo program 2020 (BG20-00023) and the European ERDF PID2021-123627OB-C51. We acknowledge the use of IBM Quantum services for this work. The views expressed are those of the authors and do not reflect the official policy or position of IBM or the IBM Quantum team.

## Contact information

If you have any questions, feel free to contact handykur@ucm.es

