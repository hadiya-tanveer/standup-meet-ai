from collections import deque

class FacilitatorAgent:
    def __init__(self, name):
        self.name = name
        self.queue = deque()
        self.absentees = set()  

    # Set participants in a random order.
    def set_participants(self, participants):
        names = [p["name"] for p in participants]
        # random.shuffle(names)
        self.queue = deque(names)
        self.absentees.clear()

    # Update the queue based on current participants.
    def update_queue(self, current_participants):
        if not self.queue:
            return None

        current_names = {p["name"] for p in current_participants}
        first = self.queue[0]

        if first in current_names:
            self.absentees.discard(first)
            self.queue.popleft()
            return first
        elif first in self.absentees:
            self.queue.popleft()  
        else:
            self.absentees.add(first)
            self.queue.rotate(-1)
        
        return None

    def has_participants(self):
        return bool(self.queue)
