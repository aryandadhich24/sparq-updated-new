import sys
import os

sys.path.append(os.path.join(os.getcwd(), "backend"))
from app.services.matching import SemanticMatcher

def test_demo_pairs():
    matcher = SemanticMatcher()
    
    pairs = [
        # Sanity
        ("This is a happy person", "This person is joyful"),
        
        # Demo attempts
        ("Google Ads Experiment", "Online Advertising Revenue"),
        ("Google Ads Experiment", "Search Engine Marketing"),
        
        ("SaaStr Conference Booth", "Tech Expo Deal"),
        ("SaaStr Conference Booth", "Trade Show Lead"),
        
        ("Senior AE Hire (Sarah)", "New Account Executive Deal"),
        ("Senior AE Hire (Sarah)", "Sales Staff Revenue"),
        
        ("LinkedIn Q1 Campaign", "Social Media Advertising"),
    ]

    print("\n--- Demo Simulation Pairs (Round 2) ---")
    for d, o in pairs:
        score = matcher.compute_similarity(d, o)
        print(f"'{d}' vs '{o}' => {score:.4f}")

if __name__ == "__main__":
    test_demo_pairs()
