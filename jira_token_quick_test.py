from src.jira_client import LiveJiraClient
import requests
jira = LiveJiraClient()

# print("Base URL:", jira.base_url)
# print("Email:", jira.email)
# print("Token loaded:", bool(jira.api_token))
# print("Token length:", len(jira.api_token) if jira.api_token else 0)

result = jira._fetch_page(
    jql="project = OPS ORDER BY created DESC",
    page_size=1,
    next_page_token=None,
)
print("\n===== JIRA REQUEST =====")
print("URL:", f"{jira.base_url}/rest/api/3/search/")
print(result)
# print("PARAMS:", result['params'])