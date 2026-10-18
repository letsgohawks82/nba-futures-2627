"""Write the final Tier 1 card (from pricing_table.csv + player_pricing_table.csv) to a CSV. Usage: python scripts/write_final_card.py OUT.csv"""
import os, sys
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT)
from src.release import checks as K
out = sys.argv[1]; os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
K.card_from_tables().to_csv(out, index=False, float_format="%.10g"); print("wrote", out)
