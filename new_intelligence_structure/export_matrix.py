import os
import numpy as np
import pandas as pd
import json

BASE_DIR = r'C:\Users\DELL\Desktop\Code More\CEI_platform\new_intelligence_structure\similarity_results\llm_experiment'

def export_to_csv():
    # Load index mapping for row/column labels
    with open(os.path.join(BASE_DIR, 'index_mapping.json'), 'r') as f:
        idx_map = json.load(f)
        
    labels = [idx_map[str(i)] for i in range(len(idx_map))]
    
    # Load the final weighted similarity matrix
    matrix_path = os.path.join(BASE_DIR, 'llm_sim_matrix.npy')
    sim_matrix = np.load(matrix_path)
    
    # Create a DataFrame for easy Excel viewing
    df = pd.DataFrame(sim_matrix, index=labels, columns=labels)
    
    # Save to CSV
    csv_path = os.path.join(BASE_DIR, 'llm_similarity_matrix.csv')
    df.to_csv(csv_path)
    print(f"Exported final similarity matrix to {csv_path}")
    print("You can easily open this CSV file directly in Excel!")

if __name__ == "__main__":
    export_to_csv()
