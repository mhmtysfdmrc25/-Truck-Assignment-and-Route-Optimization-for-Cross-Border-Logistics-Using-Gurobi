Vehicle Routing Optimization with Gurobi

📌 Project Description

This project solves a Vehicle Routing Problem (VRP) using the Gurobi Optimizer in Python.
It determines the most cost-efficient routes for trucks considering:
	•	Fixed cost per truck
	•	Distance-based transportation cost
	•	Capacity constraints
	•	Mandatory transit points (e.g., customs locations)

The goal is to minimize the total cost while ensuring all delivery points are served.

⸻

⚙️ Features
	•	Reads distance matrix from an Excel file
	•	Supports multiple transit/customs points
	•	Considers truck capacity and demands
	•	Objective function includes fixed + variable cost
	•	Produces optimized route sequences for each truck

 Project Structure
├── proje kodu(güncel vrp ile).py   # Main Python script
├── distances matrix.xlsx           # Distance matrix input file
└── README.md                       # Project description (this file)

📊 Input Data
	•	distances matrix.xlsx
	•	Square matrix with distances between locations
	•	Row and column names must match exactly
	•	Demand list for delivery points (defined inside the code)

⸻

🛠 Requirements
	•	Python 3.8+
	•	Gurobi Optimizer (with a valid license)
	•	pandas

 📌 Notes
	•	Mandatory transit points (e.g., Istanbul, Kapıkule, Strasbourg) must exist in the distance matrix.
	•	Demand values and truck capacities can be adjusted directly inside the Python file.
