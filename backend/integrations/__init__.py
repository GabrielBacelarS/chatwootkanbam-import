# CRM Integrations
from backend.integrations.base_crm import BaseCRM, CRMContact, CRMDeal
from backend.integrations.hubspot import HubSpotCRM
from backend.integrations.pipedrive import PipedriveCRM

__all__ = [
    "BaseCRM",
    "CRMContact",
    "CRMDeal",
    "HubSpotCRM",
    "PipedriveCRM"
]
