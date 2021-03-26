## About
The code repository for paper 
"Simulation-Based Optimization as a Service for Dynamic Data-Driven Applications Systems"

## Simulation Service
To start simulation service:
`python simulation_service.py`

## Configuration
See conf/cloudsim.conf

## Create new simulation task
To create your own simulation task:
1. Implement the `Simulation` class defined in `simulation.py`, where the examples are provided.
2. Create the configuration for your task by creating conf file under `conf/sumulations`, where you need to indicate the location of the simulator environment (the docker container).