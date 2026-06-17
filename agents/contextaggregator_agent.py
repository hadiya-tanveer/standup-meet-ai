import re
import os
import json
from crewai import Agent
from rapidfuzz import fuzz

from utils.jira_service import JiraService
from utils.global_variables import CREWAI_LLM, ISSUE_HISTORY_FILE, PRODUCT_BACKLOG_FILE

from datetime import date

today = date.today().isoformat()

class ContextAggregatorAgent(Agent):
    def __init__(self, name, *args, **kwargs):
        super().__init__(
            name=name,
            role="Context Aggregator",
            goal="Fetch, summarize, and categorize project management data for LLM reasoning and decision making.",
            backstory="This agent prepares all relevant context from a JSON file before the meeting, enabling the LLM to reason about project status, potential failures, and new work assignments."
        )
        
        self.llm = CREWAI_LLM
        
        self._jira_service = JiraService()  

    def fetch_jira_data(self):
        self._jira_service.run()

    def llm_reasoning(self, issues, today, product_backlog):
        messages = [
            {
                "role": "system",
                "content": (
                    "You are an intelligent assistant reviewing a team member's recent Jira activity. "
                    "You will be given a list of multiple tasks. Evaluate **each task independently**.\n\n"
                    "Your job is to detect and summarize key concerns from the provided task list. "
                    "Return a JSON array where each item is a list with exactly three elements:\n"
                    "1. Task ID (e.g., ABC-123)\n"
                    "2. Task summary (short title)\n"
                    "3. A short explanation of why the task needs attention\n\n"
                    "Apply the following rules:\n"
                    "1. Only analyze tasks created or updated within the last 14 days.\n"
                    "2. Skip tasks that are missing either a start date or a due date.\n"
                    "3. Only flag each task for **one** issue, based on the following priority:\n"
                    "   a. If the task is overdue (due date has passed and it is not done), flag as 'Overdue'.\n"
                    "   b. If the task is in 'In Progress' or 'Blocked' state for more than 7 days, flag as 'Stuck'.\n"
                    "   c. If the task hasn't been updated in more than 3 days, flag as 'Inactive'.\n\n"
                    "If you find that a person has no tasks (i.e., no valid tasks), then:\n"
                    "- Read the product backlog list.\n"
                    "- Choose **one task** from the backlog that seems relevant.\n"
                    "- Add it to the JSON array.\n"
                    "- In the explanation, clearly mention: \"No active tasks found; assigning new work: [Task Name] (ID: [Task ID]).\"\n"
                    "Format:\n"
                    "[\n"
                    "  [\"ABC-123\", \"Fix broken login\", \"Task is overdue; the due date has passed and it is not completed.\"],\n"
                    "  [\"DEF-456\", \"Integrate Stripe\", \"No active tasks found; assigning new work.\"]\n"
                    "]\n\n"
                    "You must return ONLY a valid JSON array, with no commentary or extra explanation."
                )
            },
            {
                "role": "user",
                "content": (
                    f"Today's date is: {today}\n\n"
                    "### User Task List ###\n"
                    f"{json.dumps(issues, indent=2)}\n\n"
                    "### Product Backlog ###\n"
                    f"{json.dumps(product_backlog, indent=2)}\n\n"
                    "Respond ONLY with the JSON array as specified."
                )
            }
        ]

        output = self.llm.call(messages=messages)
        return json.loads(output) if output else []

    def make_issues_conversational(self, issues_dict):
        summaries = {}

        for name, issues in issues_dict.items():
            # Convert the [ID, Summary, LLM Response] format to readable bullet points
            formatted_issues = []
            for issue in issues:
                task_id = issue[0]
                task_summary = issue[1]
                llm_response = issue[2]
                formatted_issues.append(f"Task {task_id}: {task_summary} - {llm_response}")

            messages = [
                {
                    "role": "system",
                    "content": (
                        "You are a project manager preparing for a standup meeting. "
                        "First, read the issues section carefully (pay special attention to the third line). "
                        "Based on that, create a short, conversational spoken summary that sounds professional. "
                        "Try to keep it concise."
                        "Mention each issue clearly and naturally, but keep it brief. "
                        "Keep the tone simple, professional, and direct, without being overly enthusiastic or too frank. "
                        "Make sure the message is phrased as if you are addressing the person directly. "
                        "Do not include any analysis, reasoning steps, or explanation about how you formed the response. "
                        "Just return the final message to be read out loud. "
                        "Do not make it a third-person message."
                    )
                },
                {
                    "role": "user",
                    "content": (
                        f"Here are the issues for {name}:\n"
                        f"{json.dumps(formatted_issues, indent=2)}"
                    )
                }
            ]

            output = self.llm.call(messages=messages)
            summaries[name] = output.strip() if output else ""

        return summaries


    def issues_to_conversational_json(self, issues_dict):
        conversations = self.make_issues_conversational(issues_dict)
        result = []
        for name, issues in issues_dict.items():
            result.append({
                'name': name,
                'issues': issues,
                'conversation': conversations[name]
            })
        return result

    def store_conversations_json(self, conversations_json, filename="test/output/meeting_conversations.json"):
        if os.path.exists(filename):
            with open(filename, "r") as f:
                try:
                    existing = json.load(f)
                except json.JSONDecodeError:
                    existing = []
        else:
            existing = []

        existing.extend(conversations_json)

        with open(filename, "w") as f:
            json.dump(existing, f, indent=2)

    # Process all user files from the contextaggregator directory.
    def process_user_files(self, issue_history, product_backlog):
        issues_dict = {}
        context_dir = "test/output/"
        
        if not os.path.exists(context_dir):
            print(f"Directory {context_dir} does not exist")
            return issues_dict
            
        for filename in os.listdir(context_dir):
            if filename.endswith('.json') and filename.startswith('jira_tasks_'):
                file_path = os.path.join(context_dir, filename)
                try:
                    with open(file_path, 'r') as f:
                        user_data = json.load(f)
                    
                    # Extract user information
                    name = user_data.get('name', '')
                    
                    # Pass the raw issues list directly to LLM reasoning
                    raw_issues = user_data.get('issues', [])
                    issues = self.llm_reasoning(raw_issues, today, product_backlog)
                    
                    unresolved_issues = self.filter_resolved_issues(issues, name, issue_history)
                    
                    if unresolved_issues:
                        issues_dict[name] = unresolved_issues
                    
                except Exception as e:
                    print(f"Error processing file {filename}: {e}")
                    continue
                    
        return issues_dict

    def load_json_file(self, file_path):
        if os.path.exists(file_path):
            with open(file_path, 'r') as f:
                return json.load(f)
        else:
            return []

    # Filter out resolved issues to avoid speaking about the same issue multiple times.
    def filter_resolved_issues(self, issues, name, issue_history):
        unresolved_issues = []
        for issue in issues:
            # Extract the task ID and summary from the new format [ID, Summary, LLM Response]
            if isinstance(issue, list) and len(issue) >= 2:
                task_id = issue[0]
                task_summary = issue[1]
                found = False
                for hist in issue_history:
                    if (
                        hist.get('person') == name and
                        (hist.get('responded') is True or str(hist.get('responded')).lower() == 'yes')
                    ):
                        # Handle issue_text as either string or list format
                        issue_text = hist.get('issue_text', '')
                        if isinstance(issue_text, list) and len(issue_text) >= 2:
                            # If issue_text is a list [task_id, task_summary, llm_response]
                            hist_task_id = issue_text[0]
                            hist_task_summary = issue_text[1]
                            if (hist_task_id == task_id or 
                                fuzz.token_set_ratio(hist_task_summary, task_summary) > 85):
                                found = True
                                break
                        elif isinstance(issue_text, str):
                            # If issue_text is a string (legacy format)
                            if (fuzz.token_set_ratio(issue_text, task_summary) > 85 or
                                issue_text.find(task_id) != -1):
                                found = True
                                break
                if not found:
                    unresolved_issues.append(issue)
            else:
                # If the format is not as expected, consider it unresolved
                unresolved_issues.append(issue)
        return unresolved_issues

    def assign_new_tasks(self, meeting_conversations_file):
        assignments = []
        if not os.path.exists(meeting_conversations_file):
            print(f"File not found: {meeting_conversations_file}")
            return assignments
        
        with open(meeting_conversations_file, 'r') as f:
            conversations = json.load(f)
        
        for entry in conversations:
            name = entry.get('name')
            issues = entry.get('issues', [])
            for issue in issues:
                # Check if explanation indicates a new assignment
                if (
                    isinstance(issue, list) and len(issue) == 3 and
                    "No active tasks found; assigning new work" in issue[2]
                ):
                    explanation = issue[2]

                    # Extract Task Name and Task ID from explanation
                    match = re.search(r"assigning new work: (.+?) \(ID:\s*([^)]+)\)", explanation)
                    if match:
                        task_name = match.group(1).strip()
                        task_id = match.group(2).strip()
                        assignments.append((name, task_id, task_name))
                    else:
                        print(f"⚠️ Could not parse task info for {name}: {explanation}")
        
        return assignments

    def run(self, issue_history_file=ISSUE_HISTORY_FILE, product_backlog_file=PRODUCT_BACKLOG_FILE):
        self.fetch_jira_data()
        issue_history = self.load_json_file(issue_history_file)
        product_backlog = self.load_json_file(product_backlog_file)

        issues_dict = self.process_user_files(issue_history, product_backlog)

        conversations_json = self.issues_to_conversational_json(issues_dict)
        self.store_conversations_json(conversations_json)

        assignments = self.assign_new_tasks("test/output/meeting_conversations.json")
        if assignments:
            self._jira_service.assign_task_to_user(assignments[0][1], assignments[0][0])

    
