"""
file name: polar_wrapper.py
author: Handy, Valentin
date: 13 June 2024
"""
import numpy as np
from . import __tools as tls
from . import __polarcodec as codec
from .__qpolarprep import q1prep as q1prep
import time

def get_q1prep_sr(n, lstate, results):
    # n = 4       # number of polarization steps (polar code length N = 2^n)
    # lstate = "X" # prepared logical state: may be "Z" (|0>) or "X" (|+>)
    
    # # measurement results file
    # # each line in the file contains the measurement results for one preparation experiment
    # mfile = 'polar_code_n{}_{}_simulator.txt'.format(n, lstate.lower())
    
    # zpos: last position frozen in zero, counting from zero! (0 <= zpos < N-1)
    # list of zpos values, assuming that logical |0> is prepared (lstate = "Z")
    #       n =   0   1   2  3  4  5   6   7   8   9   10 
    zpos_list = [-1, -1, 1, 3, 6, 7, 22, 15, 90, 31, 362]

    if lstate == "Z":
        # |0> is prepared: take zpos value from the list above
        zpos = zpos_list[n]
    elif lstate == "X":
        # |+> is prepared: zpos value from the list above -1
        zpos = zpos_list[n] -1
    else:
        raise TypeError("Illegal 'lstate' value")

    N     = 2**n     # polar code length
    mnum  = n*(N//2) # number of measurement results for each state preparation

    count_success = 0    # number of valid measurement results
    count_failure = 0    # number of invalid measurement results
    total_shots = sum(results.values())

    # ##################################################################
    # read measurement results from file, and check which ones are valid
    # ##################################################################
    for line, meas_counts in results.items():
        # print(line)
        # remove spaces at beginning and end of line
        mstr = line.strip()

        # init the measurement results array -- of length len(mstr)
        meas = np.zeros((len(mstr),), dtype=int) 

        # convert from string to np array
        for i in range(0, len(mstr)):
            meas[i] = ord(mstr[i]) - ord('0')	
            if meas[i] != 0 and meas[i] != 1:
                raise TypeError("Illegal measurement result: must be 0 or 1")


        # check if 'meas' are valid measurement results
        success, qstate_UV = q1prep(n, zpos, meas)
        if success == 1:
            count_success = count_success + meas_counts
            # print(meas)
        else:
            count_failure = count_failure + meas_counts

    # print("  number of valid measurement results = ", count_success, count_success / total_shots)
    # print("number of invalid measurement results = ", count_failure, count_failure / total_shots)
    # print("")

    return count_success / total_shots

def get_logical_error_on_accepted_states(n, lstate, results):
    # n = 4       # number of polarization steps (polar code length N = 2^n)
    # lstate = "X" # prepared logical state: may be "Z" (|0>) or "X" (|+>)
    
    # # measurement results file
    # # each line in the file contains the measurement results for one preparation experiment
    # mfile = 'polar_code_n{}_{}_simulator.txt'.format(n, lstate.lower())
    
    # zpos: last position frozen in zero, counting from zero! (0 <= zpos < N-1)
    # list of zpos values, assuming that logical |0> is prepared (lstate = "Z")
    #       n =   0   1   2  3  4  5   6   7   8   9   10 
    zpos_list = [-1, -1, 1, 3, 6, 7, 22, 15, 90, 31, 362]

    if lstate == "Z":
        # |0> is prepared: take zpos value from the list above
        zpos = zpos_list[n]
    elif lstate == "X":
        # |+> is prepared: zpos value from the list above -1
        zpos = zpos_list[n] -1
    else:
        raise TypeError("Illegal 'lstate' value")

    N     = 2**n     # polar code length
    mnum  = n*(N//2) # number of measurement results for each state preparation

    # count_discard/accept: number of states discarded/accepted during the state preparation protocol
    # in case of errors detected during state preparation, the state is discarded, otherwise it is accepted  
    count_accept  = 0    # number of accepted states (valid measurement results) -- was count_success in previous version
    count_discard = 0    # number of discarded states (invalid measurement results) -- was count_failure in previous version

    # count_logerror: number of logical errors on the accepted states
    # we check whether the undetected errors that may have survived on the accepted (prepared)  
    # state can be successfully corrected or not. when not, a logical error is counted
    count_logerror = 0 
    count_undecided = 0

    # This is repeating just for calculating the detection time
    tmp_start_time  = time.perf_counter()
    for line, meas_counts in results.items():
        # print(line)
        # remove spaces at beginning and end of line
        mstr = line.strip()

        # init the measurement results array -- of length len(mstr)
        meas = np.zeros((len(mstr),), dtype=int) 

        # convert from string to np array
        for i in range(0, len(mstr)):
            meas[i] = ord(mstr[i]) - ord('0')	
            if meas[i] != 0 and meas[i] != 1:
                raise TypeError("Illegal measurement result: must be 0 or 1")


        # check if 'meas' are valid measurement results
        success, qstate_UV = q1prep(n, zpos, meas[:N-1:-1])
        if success == 1:
            pass
        else:
            pass

    tmp_end_time = time.perf_counter()
    detection_time = tmp_end_time - tmp_start_time

    total_shots = sum(results.values())


    tmp_start_time  = time.perf_counter()
    # print("Total shots :", total_shots)
    # ##################################################################
    # read measurement results from file, and check which ones are valid
    # ##################################################################
    for line, meas_counts in results.items():
        # print(line)
        # remove spaces at beginning and end of line
        mstr = line.strip()

        # init the measurement results array -- of length len(mstr)
        meas = np.zeros((len(mstr),), dtype=int) 

        # convert from string to np array
        for i in range(0, len(mstr)):
            meas[i] = ord(mstr[i]) - ord('0')	
            if meas[i] != 0 and meas[i] != 1:
                raise TypeError("Illegal measurement result: must be 0 or 1")


        # check if 'meas' are valid measurement results
        success, qstate_UV = q1prep(n, zpos, meas[:N-1:-1])
        if success == 1:
            count_accept = count_accept + meas_counts
            # print(meas)
        else:
            count_discard = count_discard + meas_counts

        if success == 1:
            # ###############################################################
            # this part is new with respect to previous version of the script
            # ###############################################################
            # we check whether the  undetected errors  that may have survived on 
            # the accepted (prepared) state can be successfully corrected or not 
            
            if lstate.lower() == "z":    
                # |0> is prepared: logical information encoded at position zpos
                
                # qstate_U: the U part of qstate_UV 
                qstate_U = np.zeros((N,), dtype=int)
                qstate_U[:zpos] = qstate_UV[:zpos]
                
                # encode qstate_U -- encoding is done in place
                codec.polarenc(qstate_U)
                
                # add measurement resuts (data qubits, measured after state preparation)
                # print(meas[N-1::-1], meas[N-1:])
                qstate_U = np.mod(qstate_U + meas[N-1::-1], 2)
                
                # run polar decoder (logical information encoded at position zpos)
                # print(1-2*qstate_U, qstate_U)
                u_ipos = codec.polardec(1-2*qstate_U, zpos)
                
                if u_ipos == -1:
                    # undecided value (llr = 0): we count half an error, since a 
                    # random choice would give an error with probability 1/2
                    count_logerror = count_logerror + (0.5 * meas_counts); # count 1/2 logical error
                elif u_ipos != qstate_UV[zpos]:
                    # logical error (the decoded value is not the correct one)
                    count_logerror = count_logerror + (1 * meas_counts);   # count a logical error
                
            elif lstate.lower() == "x":  
                # |+> is prepared: logical information encoded at position zpos+1
                
                # qstate_V: the V part of qstate_UV 
                qstate_V = np.zeros((N,), dtype=int)
                qstate_V[zpos+2:] = qstate_UV[zpos+2:]
                
                # encode qstate_V -- encoding is done in place
                codec.revpolarenc(qstate_V)
                
                # add measurement resuts (data qubits, measured after state preparation)
                # print(meas[N-1::-1], (meas[N-1::-1])[::-1])
                logical_bit = meas[N-1::-1]
                # logical_bit = (meas[N-1::-1])[::-1]
                qstate_V = np.mod(qstate_V + logical_bit, 2)
                
                # run polar decoder (logical information encoded at position zpos+1)
                # print(1-2*qstate_V, qstate_V)
                v_ipos = codec.revpolardec(1-2*qstate_V, zpos+1)
                
                if v_ipos == -1:
                    # undecided value (llr = 0): we count half an error, since a 
                    # random choice would give an error with probability 1/2
                    count_logerror = count_logerror+0.5; # count 1/2 logical error
                    count_undecided = count_undecided + 1; 
                    # print(" undecided ... ")
                elif v_ipos != qstate_UV[zpos+1]:
                    # logical error (the decoded value is not the correct one)
                    count_logerror = count_logerror+1;   # count a logical error
            
            else:
                raise TypeError("Illegal 'lstate' value")
            
    tmp_end_time = time.perf_counter()
    decoding_time = tmp_end_time - tmp_start_time - detection_time

    print("number of discarded states (invalid measurement results) = ", count_discard)
    print(" number of accepted states   (valid measurement results) = ", count_accept)
    print("        number of logical errors on the accepted states  = ", round(count_logerror))

    fidelity = 0
    if count_accept > 0:
        fidelity = ((count_accept - round(count_logerror)) / count_accept)

    return count_accept, round(count_logerror), count_undecided, fidelity, detection_time, decoding_time

