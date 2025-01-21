import requests
import datetime
import mysql.connector
import numpy as np

def insert_calibration_data():
    now = datetime.datetime.now()

    try:
        # MySQL connection parameters
        mysql_config = {
            'user': 'user_1',
            'password': '1234',
            'host': 'localhost',
            'database': 'framework'
        }

        # Connect to the MySQL database
        conn = mysql.connector.connect(**mysql_config)
        cursor = conn.cursor()

        hw_provider = "IBM"

        # get all the backends
        cursor.execute('SELECT hw_name, 2q_native_gates FROM calibration_data.hardware WHERE hw_provider = %s AND status IS NULL ', (hw_provider, ))

        # Fetch all the rows from the result set
        results = cursor.fetchall()

        cursor.close()
        conn.close()

        #results = [["ibm_prague", ""]]

        # Loop through the results
        for result in results:
            hw_name, native_gates = result

            try:

                # Define the URL of the JSON file you want to download
                json_url = "https://api-qcon.quantum-computing.ibm.com/api/Backends/"+ hw_name +"/properties"

                # Send an HTTP GET request to the URL
                response = requests.get(json_url)

                # Check if the request was successful (status code 200)
                if response.status_code == 200:
                    # Parse the JSON content from the response
                    json_data = response.json()
                        
                    calibration_datetime = datetime.datetime.strptime(json_data['last_update_date'], "%Y-%m-%dT%H:%M:%SZ")
                    #print(calibration_datetime)

                    # Connect to the MySQL database
                    conn = mysql.connector.connect(**mysql_config)
                    cursor = conn.cursor()
                    
                    # Check if the calibration_datetime already exists in the table
                    cursor.execute('SELECT calibration_id FROM ibm WHERE calibration_datetime = %s AND hw_name = %s', (calibration_datetime, hw_name, ))
                    existing_row = cursor.fetchone()

                    if existing_row:
                        print(hw_name, "Calibration datetime ("+ str(calibration_datetime) +") already exists (calibration_id: " + str(existing_row[0]) + "). Skipping insertion.", now.strftime("%Y-%m-%d %H:%M:%S"))
                        conn.close()
                        continue
                    
                    # Insert the data into the "rigetti" table
                    cursor.execute('INSERT INTO ibm (calibration_datetime, hw_name, data_source) VALUES (%s, %s, "json")',
                                (calibration_datetime, hw_name))
                    calibration_id = cursor.lastrowid
                    
                    print(hw_name, "Data ("+ str(calibration_datetime) +") inserted with ID:", calibration_id, now.strftime("%Y-%m-%d %H:%M:%S"))
                
                    #print(qubit_spec)
                    for g in json_data['gates']:
                        #print(g["gate"], g["qubits"], len(g["qubits"]))
                        
                        qubit_control = None
                        qubit_target = None
                        if (len(g["qubits"]) == 1):
                            qubit_control = g["qubits"][0]
                            qubit_target = g["qubits"][0]
                        else:
                            qubit_control = g["qubits"][0]
                            qubit_target = g["qubits"][1]
                        
                        p = g["parameters"]
                        
                        if (g["gate"] == "reset"):
                            pGateError = 0
                            pGateLength = p[0]["value"]
                        else: 
                            pGateError = p[0]["value"] if not np.isnan(p[0]["value"]) else None
                            pGateLength = p[1]["value"] 
                        
                        #pDate = datetime.datetime.strptime(p[0]["date"], "%Y-%m-%dT%H:%M:%SZ")
                        pDate = str.replace(p[0]["date"], "Z", "")
                        # Insert data into "rigetti_qubit_spec" table

                        cursor.execute('''
                            INSERT INTO ibm_gate_spec (
                                calibration_id,
                                qubit_control,
                                qubit_target,
                                gate_name,
                                date,
                                gate_error,
                                gate_length
                            ) VALUES (%s, %s, %s, %s, %s, %s, %s)
                        ''', (
                            calibration_id,
                            qubit_control,
                            qubit_target,
                            g["gate"],
                            pDate,   # calibration date for gate error
                            pGateError,  # value of gate error
                            pGateLength,   # value of gate length
                        ))
                

                    for qubit, q in enumerate(json_data['qubits']):
                        pT1 = None
                        pT2 = None
                        pfrequency = None
                        panharmonicity = None
                        preadout_error = None
                        pprob_meas0_prep1 = None
                        pprob_meas1_prep0 = None
                        preadout_length = None
                        pT1_date = None
                        pT2_date = None
                        pfrequency_date = None
                        panharmonicity_date = None
                        preadout_error_date = None
                        pprob_meas0_prep1_date = None
                        pprob_meas1_prep0_date = None
                        preadout_length_date = None

                        for p in q:
                            if (p["name"] == "T1"):
                                pT1 = p["value"] if not np.isnan(p["value"]) else None
                                pT1_date = str.replace(p["date"], "Z", "")

                            if (p["name"] == "T2"):
                                pT2 = p["value"] if not np.isnan(p["value"]) else None
                                pT2_date = str.replace(p["date"], "Z", "")

                            if (p["name"] == "frequency"):
                                pfrequency = p["value"] if not np.isnan(p["value"]) else None
                                pfrequency_date = str.replace(p["date"], "Z", "")

                            if (p["name"] == "anharmonicity"):
                                panharmonicity = p["value"] if not np.isnan(p["value"]) else None
                                panharmonicity_date = str.replace(p["date"], "Z", "")

                            if (p["name"] == "readout_error"):
                                preadout_error = p["value"] if not np.isnan(p["value"]) else None
                                preadout_error_date = str.replace(p["date"], "Z", "")

                            if (p["name"] == "prob_meas0_prep1"):
                                pprob_meas0_prep1 = p["value"] if not np.isnan(p["value"]) else None
                                pprob_meas0_prep1_date = str.replace(p["date"], "Z", "")

                            if (p["name"] == "Tprob_meas1_prep01"):
                                pprob_meas1_prep0 = p["value"] if not np.isnan(p["value"]) else None
                                pprob_meas1_prep0_date = str.replace(p["date"], "Z", "")

                            if (p["name"] == "readout_length"):
                                preadout_length = p["value"] if not np.isnan(p["value"]) else None
                                preadout_length_date = str.replace(p["date"], "Z", "")


                        cursor.execute('''
                            INSERT INTO ibm_qubit_spec (
                                calibration_id,
                                qubit,
                                T1,
                                T2,
                                frequency,
                                anharmonicity,
                                readout_error,
                                prob_meas0_prep1,
                                prob_meas1_prep0,
                                readout_length,
                                T1_date,
                                T2_date,
                                frequency_date,
                                anharmonicity_date,
                                readout_error_date,
                                prob_meas0_prep1_date,
                                prob_meas1_prep0_date,
                                readout_length_date
                            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                            ''', (
                                calibration_id,
                                qubit,
                                pT1,
                                pT2,
                                pfrequency,
                                panharmonicity,
                                preadout_error,
                                pprob_meas0_prep1,
                                pprob_meas1_prep0,
                                preadout_length,
                                pT1_date,
                                pT2_date,
                                pfrequency_date,
                                panharmonicity_date,
                                preadout_error_date,
                                pprob_meas0_prep1_date,
                                pprob_meas1_prep0_date,
                                preadout_length_date
                            ))

                    # Commit the changes and close the connection
                    conn.commit()
                
                else:
                    print("Failed to retrieve JSON. Status code:", response.status_code)
                    cursor.close()
                    conn.close()

            except Exception as e:
                print("=====>", hw_name, "Error :", str(e))

        

    except Exception as e:
        print("An error occurred:", str(e))

    

if __name__ == "__main__":
    insert_calibration_data()
