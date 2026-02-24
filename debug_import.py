import sys
import traceback

print("Python path:", sys.path)

try:
    print("Importing aboa.core.exceptions...")
    from aboa.core.exceptions import DataIngestionError, ExternalIntegrationError, RetryableError
    print("✓ Core exceptions imported")
    
    print("Importing aboa.models.revenue_entities...")
    from aboa.models.revenue_entities import Deal, Lead, SalesActivity, SalesRep, ContactInfo
    print("✓ Revenue entities imported")
    
    print("Importing aboa.models.enums...")
    from aboa.models.enums import LeadStatus, DealStage, ActivityType
    print("✓ Enums imported")
    
    print("Importing aboa.core.config...")
    from aboa.core.config import get_settings
    print("✓ Config imported")
    
    print("Now importing connectors module...")
    import aboa.data_ingestion.connectors
    print("✓ Connectors module imported")
    
except Exception as e:
    print("Error during import:")
    traceback.print_exc()