#!/usr/bin/env python3
import sys
sys.path.append('mvp')

from app.core.database import get_db
from app.models.qa_pair import QAPair
from app.models.dataset import Dataset

db = next(get_db())
try:
    # Check dataset 30
    dataset = db.query(Dataset).filter(Dataset.id == 30).first()
    if dataset:
        print(f'Dataset 30: {dataset.filename}')
        
        # Check QA pairs for dataset 30
        qa_pairs = db.query(QAPair).filter(QAPair.dataset_id == 30).all()
        print(f'QA pairs in dataset 30: {len(qa_pairs)}')
        
        # Show first few QA pairs
        for i, qa in enumerate(qa_pairs[:5]):
            print(f'{i+1}. Q: {qa.question}')
            print(f'   A: {qa.answer}')
            print(f'   Type: {qa.question_type}')
            print()
    else:
        print('Dataset 30 not found')
finally:
    db.close()