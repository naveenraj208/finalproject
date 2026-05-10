from llm_client import call_model

class SwarmOrchestrator:
    def __init__(self):
        self.agents = [
            {
                "name": "Infrastructure Analyst",
                "role": "You are the Infrastructure Analyst. Focus strictly on traffic flow, power grids, structural integrity, and physical logistics. Analyze the user's request from this lens."
            },
            {
                "name": "Environmental Analyst",
                "role": "You are the Environmental Analyst. Focus strictly on air quality, ecological sustainability, weather impacts, and biological health. Analyze the user's request from this lens."
            },
            {
                "name": "Security & Risk Assessor",
                "role": "You are the Security & Risk Assessor. Focus strictly on operational hazards, public safety, cyber threats, and compliance. Analyze the user's request from this lens."
            }
        ]

    def needs_swarm(self, query: str) -> bool:
        """Heuristic to determine if a query is complex enough for a Swarm."""
        complex_keywords = ["optimize", "plan", "crisis", "emergency", "strategy", "comprehensive", "solve", "dilemma", "how should we"]
        return any(k in query.lower() for k in complex_keywords) and len(query) > 20

    def execute_swarm(self, query: str, context_block: str) -> dict:
        """
        Executes a multi-agent debate sequentially (to save local RAM/VRAM).
        Returns the individual thoughts and the final synthesized response.
        """
        swarm_reports = []
        
        # Phase 1: Individual Analysis
        for agent in self.agents:
            prompt = (
                f"{agent['role']}\n\n"
                f"CONTEXT:\n{context_block}\n\n"
                f"USER REQUEST: {query}\n\n"
                "Provide a brief, focused analysis (1 paragraph) addressing the request from your unique perspective. Do not attempt to solve the whole problem."
            )
            try:
                # Max tokens limited to keep it fast
                response = call_model(prompt, max_tokens=150).strip()
                swarm_reports.append({"agent": agent["name"], "report": response})
            except Exception as e:
                swarm_reports.append({"agent": agent["name"], "report": f"Signal lost: {str(e)}"})

        # Phase 2: Synthesis
        synthesis_prompt = (
            "You are the Prime Synthesizer. You must combine the perspectives of your three sub-agents into a cohesive, actionable, and final response for the user.\n\n"
            f"USER REQUEST: {query}\n\n"
            "--- SUB-AGENT REPORTS ---\n"
        )
        for rep in swarm_reports:
            synthesis_prompt += f"[{rep['agent']}]: {rep['report']}\n"
        
        synthesis_prompt += "\n--- END REPORTS ---\nGenerate the final, comprehensive response in your primary persona's voice."

        try:
            final_response = call_model(synthesis_prompt)
        except Exception as e:
            final_response = f"Swarm Synthesis Failed. Critical error: {str(e)}"

        return {
            "swarm_reports": swarm_reports,
            "final_response": final_response
        }
