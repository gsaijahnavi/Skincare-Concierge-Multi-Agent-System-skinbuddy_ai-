from typing import List, Dict
import pandas as pd
from google.adk.tools import AgentTool, ToolContext

class EvidenceSearchTool(AgentTool):
    name: str = "evidence_search_tool"
    description: str = "Searches ingredient evidence from database."

    def __init__(self, excel_path: str):
        super().__init__(agent=self)  # Provide self as the agent parameter
        self.excel_path = excel_path
        self.df = pd.read_excel(excel_path)

    def run(self, context: ToolContext, query: str, ingredient: str) -> Dict:
        matches = self.df[self.df["ingredient"].str.lower() == ingredient.lower()]

        if matches.empty:
            return {"chunks": []}

        chunks = []
        for _, row in matches.iterrows():
            chunks.append({
                "title": row.get("study_title", ""),
                "url": row.get("source_url", ""),
                "snippet": row.get("key_findings_snippet", ""),
                "tags": str(row.get("tags", "")).split(";")
            })

        return {"chunks": chunks}
