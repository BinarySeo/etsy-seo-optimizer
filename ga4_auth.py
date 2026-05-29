"""
ga4_auth.py
-----------
OAuth 인증으로 GA4 데이터 접근 테스트
한 번만 실행하면 token.json 생성됨

Usage:
    python ga4_auth.py
"""

import os
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google.analytics.data_v1beta import BetaAnalyticsDataClient
from google.analytics.data_v1beta.types import (
    RunReportRequest, DateRange, Metric, Dimension
)
from dotenv import load_dotenv

load_dotenv()

SCOPES = ['https://www.googleapis.com/auth/analytics.readonly']
TOKEN_PATH = 'token.json'
CREDENTIALS_PATH = 'ga4-credentials-oauth.json'


def get_credentials():
    creds = None

    if os.path.exists(TOKEN_PATH):
        creds = Credentials.from_authorized_user_file(TOKEN_PATH, SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                CREDENTIALS_PATH, SCOPES
            )
            creds = flow.run_local_server(port=0)

        with open(TOKEN_PATH, 'w') as token:
            token.write(creds.to_json())

    return creds


def test_ga4():
    creds = get_credentials()
    client = BetaAnalyticsDataClient(credentials=creds)
    property_id = os.getenv('GA4_PROPERTY_ID')

    request = RunReportRequest(
        property=f"properties/{property_id}",
        date_ranges=[DateRange(start_date='30daysAgo', end_date='today')],
        dimensions=[Dimension(name='pagePath')],
        metrics=[
            Metric(name='sessions'),
            Metric(name='screenPageViews'),
        ],
        limit=10,
    )

    response = client.run_report(request)

    print("\n--- Top 10 Pages (Last 30 days) ---")
    for row in response.rows:
        print(f"{row.dimension_values[0].value}: {row.metric_values[0].value} sessions")


if __name__ == "__main__":
    test_ga4()