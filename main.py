import time
from ingestion import run_ingestion
from features import process_all_files
from model import train_and_evaluate

def main():
    print("="*50)
    print("NBA Player Props Predictive Model Pipeline")
    print("="*50)
    
    # Phase 1: Data Ingestion
    print("\n[PHASE 1] Data Ingestion")
    start_time = time.time()
    run_ingestion()
    print(f"Phase 1 completed in {time.time() - start_time:.2f} seconds.")
    
    # Phase 2: Feature Engineering
    print("\n[PHASE 2] Feature Engineering")
    start_time = time.time()
    process_all_files()
    print(f"Phase 2 completed in {time.time() - start_time:.2f} seconds.")
    
    # Phase 3: Machine Learning
    print("\n[PHASE 3] Machine Learning & Validation")
    start_time = time.time()
    train_and_evaluate(target='PTS')
    print(f"Phase 3 completed in {time.time() - start_time:.2f} seconds.")
    
    print("\nPipeline execution finished successfully.")

if __name__ == "__main__":
    main()
