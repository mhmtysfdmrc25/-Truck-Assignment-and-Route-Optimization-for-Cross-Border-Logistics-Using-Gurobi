Project Description
:
This project aims to develop a Gurobi-based optimization tool for improving the efficiency of international freight shipments between France and Turkey. The model will determine (1) how to assign shipment loads to available trucks under capacity constraints, and (2) the most cost-effective delivery sequence of multiple destinations per truck, starting from a customs checkpoint and proceeding to multiple delivery points. The goal is to minimize the total transportation cost by considering both fixed costs per truck and distance-based variable costs. The model will ensure that shipments heading to the same destination are assigned to the same truck and that each truck’s route is optimized to reduce total kilometers traveled.

Suggested Method/Tool/Techniques(s) of Approach
:
- Python programming with Gurobi solver.
- Binary decision variables for load-truck assignment and routing.
- Data input through Excel files: distance matrix.
- Cost function combining fixed cost per truck and variable cost per kilometer. 
- Route optimization using shortest path evaluation over delivery point permutations.
- Scenario testing for different truck numbers, capacities, and destination clusters.

Results And Deliverables Expected 
:
- A fully functional Python-based optimization tool using Gurobi - Automated output: truck assignments, optimized delivery routes, and total cost - Reduction in total cost through better truck utilization and route planning - Decision support framework to minimize the number of trucks used per shipment cycle
