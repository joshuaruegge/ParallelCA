"""
=============================================================================
Title : main.py
Description : This is a parallelized Python program capable of simulating a 
modified cellular automata simulation, according to the specifications in
the Final Project document.
Author : Joshua Ruegge
Date : 04/16/2024
Version : 1.6
Usage : python3 main.py -i (input file path)
-o (output file path) -p (number of parallel processes, optional)
Notes : The -i option must be given a path to a valid input file containing 
a representation of a matrix, as specified in the Final Project document. 
The program will write the output - a document in the same format
representing the initial matrix after 100 generations - at the path supplied
to the -o option. The file at the path need not exist (and will be
overwritten if it does), but the path to the file must be valid. In order to
run the program with more than the default number of processes (namely, 1,
or serial execustion), the desired number of processes may optionally be
specified using -p. 
Python Version: 3.12.1
=============================================================================
"""

import argparse
import os
import multiprocessing as mp

#function to process and handle arguments
def parse_args(): 
    # configure parser to accept args as specified in project document
    parser = argparse.ArgumentParser()
    parser.add_argument("-i", dest="input_path", required=True)
    parser.add_argument("-o", dest="output_path", required=True)
    parser.add_argument("-p", type=int, dest="process_count", default=1)

    # fetch and verify arguments
    args = parser.parse_args()
    if not(os.path.isfile(args.input_path)):
        raise IOError("A valid path to the input file must be specified using the -i option.")
    outputdir = os.path.dirname(args.output_path)
    if not(outputdir == '' or os.path.isdir(outputdir)):
        raise IOError("A valid directory to place the output file in must be specified using the -o option.")
    if args.process_count <= 0:
        raise IOError("The process count must be a value greater than zero.")    

    input_file = open(args.input_path,"r")
    output_file = open(args.output_path,"w")
    pcount = args.process_count
    return input_file,output_file,pcount

#read matrix from inlines, created as global variable to calculate matrix dims
def initialize_matrix():
    #use readIndex variable to flatten/linearize 2d input into 1d array
    readindex=0
    for line in inlines:
        for char in line.strip():
            if char == 'O':
                matrix[readindex]=1
            else:
                matrix[readindex]=0
            readindex+=1

#fetch value at 2d index [row][column] from 1d array nMatrix
#nMatrix stores a copy of initial state of matrix, and as such
#is referenced to perform calculations while matrix is actively modified
def lookup(r,c):
    r %= rowLength
    c %= colLength
    return nMatrix[r*colLength+c]
    
#performs a single generation calculate on a subset of rows in the matrix
#begins at row [init] and then increments by (num of processses) rows till out of bounds
#by initializing processes with init values from 0 to num of procesess - 1, this ensures 
#parallel processes can work on the same matrix without risking collision and requiring locks
#ex: for 4 processes, 19 row matrix, chart of processes and rows handled:
#process:   |		rows handled:
#	1   |	1	5	9	13	17
#	2   |	2	6	10	14	18
#	3   |	3	7	11	15	19
#	4   |	4	8	12	16

def calcRows(init):
    for r in range(init,rowLength,pcount):
        for c in range(colLength):
            index = r*colLength+c
            count = lookup(r-1,c-1)+lookup(r-1,c)+lookup(r-1,c+1)+lookup(r,c-1)+lookup(r,c+1)+lookup(r+1,c-1)+lookup(r+1,c)+lookup(r+1,c+1)
            if(matrix[index]):
                if(count==0 or count==1 or count==4 or count==6 or count==8):
                    matrix[index]=0
            else:
                if(count&1 == 0 and count != 0):
                    matrix[index]=1

#write current state of matrix to output file, converting from 1 dimension back to 2
def writeOutput():
    for row in range(0,totLength,colLength):
        for col in range(0,colLength):
            output_file.write("O" if matrix[row+col] == 1 else ".")
        output_file.write("\n")


#Parent process tasks
if __name__ == "__main__":
    #verify and process args
    input_file, output_file, pcount = parse_args()

    #create global variables (matrix dims, matrix, spare matrix)
    inlines = input_file.readlines()
    #initialize dims
    rowLength = len(inlines)
    #strip in case of newline
    colLength = len(inlines[0].strip())
    totLength = rowLength * colLength

    #initialize matrix, and a spare matrix nMatrix to buffer data during calculation steps
    #these multiprocessing lib Array objects exist in shared memory, and are accessible by
    #all child processes at once. as the row calculation method is hardcoded to avoid row
    #collisions between processes, an access lock is unnecessary, reducing parallel overhead
    matrix = mp.Array('B', totLength, lock=False)
    nMatrix = mp.Array('B', totLength, lock=False)
    initialize_matrix()
    
    #get rid of file lines (to avoid fork() copying entire file contents unnecessarily?)
    del(inlines)
    
    #initialize parallel processes pool
    #this copies all global variables present currently into the memory space of the child processes (?)
    pool = mp.Pool(pcount)    

    #perform 100 rounds of calculation
    for n in range(100):
        #Store copy of current matrix state in nMatrix
        #This will be referenced for lookups during calculation,
        #while matrix itself is modified with results in-place
        nMatrix[:] = mp.sharedctypes.copy(matrix)
        #dispatch processes with starting rows [0...pcount-1] (see calcRows function above)
        #pool.map blocks until all processes have returned with this round's calculations
        pool.map(calcRows,range(pcount))

    #save output
    writeOutput()
