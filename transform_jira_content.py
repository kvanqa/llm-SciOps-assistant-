import os
import pandas as pd

# Load your Jira export
df = pd.read_excel('/Users/kamva.vanqa/Downloads/Jira_CAM_ISSUES.xlsx')

# Clean column names (adjust these to match your Excel sheet exactly)
df.columns = df.columns.str.strip().str.lower()

output_dir = 'docs/jira'
os.makedirs(output_dir, exist_ok=True)

for index, row in df.iterrows():
    ticket_id = str(row.get('issue key', row.get('id', index)))
    summary = str(row.get('summary', 'No Summary'))
    description = str(row.get('description', 'No Description'))
    resolution = str(row.get('resolution', row.get('comments', 'No Resolution Stated')))
    status = str(row.get('status', 'Unknown'))
    
    # We only care about resolved/closed issues that actually fixed a problem
    if 'done' in status.lower() or 'resolved' in status.lower() or 'closed' in status.lower():
        
        # Structure the text specifically for vector search matches
        document_content = f"""# JIRA TICKET: {ticket_id}
SUMMARY / ERROR SYMPTOM: 
{summary}

DETAILED SYSTEM LOGS AND DESCRIPTION:
{description}

VERIFIED RESOLUTION AND FIX STEPS:
{resolution}
"""
        # Save each ticket as a separate file for your chunking script
        file_path = os.path.join(output_dir, f"{ticket_id}.txt")
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(document_content)

print(f"Successfully processed {len(df)} Jira tickets into {output_dir}")
