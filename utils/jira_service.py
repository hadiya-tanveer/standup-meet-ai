import requests

from jira import JIRA

from utils.global_variables import SPRINT_BACKLOG_FILE
from utils.global_variables import JIRA_URL, JIRA_USERNAME, JIRA_API_TOKEN

from utils.helper import save_json

# NOTE: It is must to include the 'Update Date' custom field in the Jira project manually.

class JiraService:
    def __init__(self, jira_url=None, username=None, api_token=None):
        self.jira_url = JIRA_URL
        self.username = JIRA_USERNAME
        self.api_token = JIRA_API_TOKEN
        
        # Initialize Jira client
        self.jira = JIRA(server=self.jira_url,  basic_auth=(self.username, self.api_token))

        self.projectkey = self.get_projectkey()
        
        self.updatedate_key = self._find_customfield_id_('update_date')
        self.startdate_key = self._find_customfield_id_('Start date')

    # Fetch data from API URL and return response
    def make_get_request(self, role_url, params=None, payload=None):
        response = requests.get(role_url, auth=(self.username, self.api_token), params=params, json=payload)
        response.raise_for_status()
        return response.json()
    
    # Extract domain from URL and fetch project key from Jira API
    def get_projectkey(self):
        api_url = f"{self.jira_url}/rest/api/3/project"
        projects = self.make_get_request(api_url)
        
        if projects:    return projects[0]['key']

    # Fetch custom fields ID from Jira API.
    def _find_customfield_id_(self, field_name):
        api_url = f"{self.jira_url}/rest/api/3/field"
        fields = self.make_get_request(api_url)
        
        for field in fields:
            if field.get('name') == field_name: return field['id']

    # Fetch users assigned to a specific project
    def fetch_users(self):
        api_url = f"{self.jira_url}/rest/api/3/project/{self.projectkey}/role"    
        roles = self.make_get_request(api_url)
        
        users = []
        
        for role_name, role_url in roles.items():
            if role_name not in ['Member', 'Administrator']:    continue

            role_data = self.make_get_request(role_url)
            
            actors = role_data.get('actors', [])
            for actor in actors:
                if actor.get('type') == 'atlassian-user-role-actor':
                    users.append({
                        'accountId': actor.get('actorUser', {}).get('accountId', ''),
                        'name': actor.get('displayName', '')
                    })
        
        return users
    
    # Fetch all issues assigned to a user by account ID
    def fetch_user_issues(self, account_id):
        jql = f'assignee = {account_id} AND project = "{self.projectkey}"'

        api_url = f"{self.jira_url}/rest/api/3/search/jql"

        fields_list = [
            'summary',
            'status',
            'priority',
            'assignee',
            'updated',
            'duedate',
            'description',
            'issuetype'
        ]

        if self.updatedate_key:
            fields_list.append(self.updatedate_key)

        if self.startdate_key:
            fields_list.append(self.startdate_key)

        params = {
            'jql': jql,
            'maxResults': 100,
            'fields': ','.join(fields_list)
        }

        try:
            data = self.make_get_request(api_url, params)
            issues = data.get('issues', [])

            return [
                {
                    'id': issue['key'],
                    'summary': issue['fields']['summary'],
                    'status': issue['fields']['status']['name'],
                    'priority': issue['fields']['priority']['name']
                        if issue['fields']['priority'] else 'Medium',
                    'startdate': issue['fields'].get(self.startdate_key, '')[:10]
                        if issue['fields'].get(self.startdate_key) else 'NO_DATE',
                    'duedate': issue['fields'].get('duedate', '')[:10]
                        if issue['fields'].get('duedate') else 'NO_DATE',
                    'update_date': issue['fields'].get(self.updatedate_key, '')[:10]
                        if issue['fields'].get(self.updatedate_key) else 'NO_DATE'
                }
                for issue in issues
            ]

        except requests.exceptions.HTTPError as e:
            print(f"Error fetching issues for account {account_id}: {e}")
            print(f"Request URL: {api_url}")
            print(f"Request params: {params}")

            if e.response is not None:
                print("Response Body:", e.response.text)

            return []

    # Fetch the sprint backlog of the ongoing sprint for a project.
    def fetch_sprint_backlog(self, unassigned_only=False):        
        api_url = f"{self.jira_url}/rest/agile/1.0/board"
        boards = self.make_get_request(api_url)
        
        # Find the board for this project
        project_board = None
        for board in boards.get('values', []):
            if board.get('location', {}).get('projectKey') != self.projectkey: continue
            
            project_board = board
            break
        
        board_id = project_board['id']
        
        # Get active sprint
        sprint_api_url = f"{self.jira_url}/rest/agile/1.0/board/{board_id}/sprint"
        sprints = self.make_get_request(sprint_api_url, {'state': 'active'})
        
        active_sprint = None
        for sprint in sprints.get('values', []):
            if sprint.get('state') != 'active': continue
            
            active_sprint = sprint
            break      
    
        sprint_id = active_sprint['id']
        
        # Get all issues in the active sprint
        issues_api_url = f"{self.jira_url}/rest/agile/1.0/sprint/{sprint_id}/issue"
        sprint_issues = self.make_get_request(issues_api_url, {'maxResults': 1000})  
        
        # Build fields list for sprint backlog
        fields_list = [
            'summary',
            'status',
            'priority',
            'assignee',
            'issuetype'
        ]
        
        if self.updatedate_key:
            fields_list.append(self.updatedate_key)
        if self.startdate_key:
            fields_list.append(self.startdate_key)
        
        # Process issues
        backlog_items = []
        for issue in sprint_issues.get('issues', []):
            # Check if issue is unassigned
            assignee = issue['fields'].get('assignee')
            is_unassigned = assignee is None
            
            # If unassigned_only is True, skip assigned issues
            if unassigned_only and not is_unassigned:   continue
                
            backlog_items.append({
                'id': issue['key'],
                'summary': issue['fields']['summary'],
                'status': issue['fields']['status']['name'],
                'priority': issue['fields']['priority']['name'] if issue['fields']['priority'] else 'Medium',
                'assignee': assignee['displayName'] if assignee else 'Unassigned',
                'startdate': issue['fields'].get(self.startdate_key, '')[:10] if issue['fields'].get(self.startdate_key) else 'NO_DATE',
                'duedate': issue['fields'].get('duedate', '')[:10] if issue['fields'].get('duedate') else 'NO_DATE',
                'update_date': issue['fields'].get(self.updatedate_key, '')[:10] if issue['fields'].get(self.updatedate_key) else 'NO_DATE',
                'sprint_id': sprint_id,
                'is_unassigned': is_unassigned
            })
        
        return backlog_items 

    # Assign a task to a user.
    def assign_task_to_user(self, task_id, assignee_name):        
        # Fetch all users for the project
        users = self.fetch_users()
        # Find the user with the matching display name
        account_id = None
        for user in users:
            if user['name'].strip().lower() == assignee_name.strip().lower():
                account_id = user['accountId']
                break
        
        # Make the Jira API call to assign the issue (must use PUT)
        api_url = f"{self.jira_url}/rest/api/3/issue/{task_id}/assignee"
        payload = {"accountId": account_id}
        response = requests.put(api_url, auth=(self.username, self.api_token), json=payload)

    # Store user issues in a JSON file.
    def store_user_issues(self, output_file):
        for user in self.fetch_users():
            filename = f"test/output/{output_file.removesuffix('.json')}_{user['name'].replace(' ', '')}.json"
            data = {'name': user['name'], 'issues': self.fetch_user_issues(user['accountId'])}
            save_json(data, filename)
    
    # Main function to run the complete workflow
    def run(self):
        # Get all users in the project
        users = self.fetch_users()
        print(f"Found {users} users in the project '{self.projectkey}'.")
        
        # Export data for each user
        print(f"Exporting data for {len(users)} users...")
        self.store_user_issues("jira_tasks.json")

        print("Exporting sprint backlog...")
        sprint_file_path = SPRINT_BACKLOG_FILE
        backlog_items = self.fetch_sprint_backlog(unassigned_only=True)
        save_json(backlog_items, sprint_file_path)