import google.generativeai as genai
import os
import logging

logger = logging.getLogger(__name__)

class LLMService:
    def __init__(self):
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            logger.warning("GEMINI_API_KEY not set. AI Insights will be disabled/mocked.")
            self.model = None
        else:
            genai.configure(api_key=api_key)
            self.model = genai.GenerativeModel('gemini-pro')

    def generate_insight(self, decision_data: dict) -> str:
        """
        Generates a qualitative insight for a decision.
        """
        if not self.model:
            return "AI Insights are disabled (GEMINI_API_KEY missing)."

        prompt = self._construct_prompt(decision_data)
        
        try:
            response = self.model.generate_content(prompt)
            return response.text
        except Exception as e:
            logger.error(f"Gemini API Error: {e}")
            return "Unable to generate insight at this time."

    def _construct_prompt(self, data: dict) -> str:
        outcomes_text = "\n".join([
            f"- {o['description']} (${o['value']})" for o in data.get('related_outcomes', [])[:5]
        ])
        
        return f"""
        You are a strategic ROI analyst. Analyze the following business decision and provide a 2-sentence insight on why it was successful or unsuccessful.
        
        Decision: {data['description']} ({data['type']})
        Cost: ${data['cost']}
        ROI: {data['roi']}x
        Attributed Revenue: ${data['value']}
        
        Key Outcomes:
        {outcomes_text}
        
        If ROI > 3, explain what drove the high leverage.
        If ROI < 1, suggest what went wrong or if it needs more time.
        Keep it professional, concise, and actionable. Do not use markdown formatting.
        """

llm_service = LLMService()
