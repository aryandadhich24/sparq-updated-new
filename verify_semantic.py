import sys
import os

# Add backend to path
sys.path.append(os.path.join(os.getcwd(), "backend"))

try:
    from app.services.matching import SemanticMatcher
except ImportError as e:
    print(f"Import Error: {e}")
    sys.exit(1)

def test_pairs():
    matcher = SemanticMatcher() # This will trigger model load
    
    pairs = [
        ("LinkedIn Ads Campaign", "Leads from LinkedIn"),
        ("Hiring Head of Sales", "New Enterprise Contract Closed"),
        ("Office Coffee Supply", "Enterprise Contract Closed"),
        ("ZoomInfo License", "Outbound Lead Gen"),
        ("Google Ads", "Organic Traffic"), # Should be somewhat low
        ("Google Ads", "Paid Search Revenue"), # Should be high
    ]

    print("\n--- Semantic Similarity Test ---")
    for text1, text2 in pairs:
        score = matcher.compute_similarity(text1, text2)
        print(f"'{text1}' vs '{text2}' => {score:.4f}")

if __name__ == "__main__":
    test_pairs()
