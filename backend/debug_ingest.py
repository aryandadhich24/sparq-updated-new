
from app.database import SessionLocal
from app import models
from app.integrations.hubspot import HubSpotConnector
from app.engine import engine as attribution_engine
import sys
import os

# Add backend to path
sys.path.append(os.path.join(os.getcwd(), "backend"))

db = SessionLocal()

# Get the last user created
user = db.query(models.User).order_by(models.User.id.desc()).first()
if not user:
    print("No user found")
    sys.exit(1)

print(f"User: {user.email}, Org: {user.organization_id}")

# Mock token matches what verify_integration.py does?
# verify_integration.py calls endpoint. The endpoint looks up Integration.
integration = db.query(models.Integration).filter(
    models.Integration.organization_id == user.organization_id,
    models.Integration.provider == "HUBSPOT"
).first()

if not integration:
    print("No integration found")
    # Create one if missing for debugging
    integration = models.Integration(organization_id=user.organization_id, provider="HUBSPOT", access_token="mock_token")
    db.add(integration)
    db.commit()

token = integration.access_token
print(f"Token: {token}")

print("Syncing...")
connector = HubSpotConnector(access_token=token)
results = connector.sync_outcomes(db, organization_id=user.organization_id)
print("Sync Results:", results)

print("Running Attribution...")
try:
    attribution_engine.run_full_attribution(db, organization_id=user.organization_id)
    print("Attribution done.")
except Exception as e:
    print("CAUGHT EXCEPTION:")
    import traceback
    traceback.print_exc()

db.close()
