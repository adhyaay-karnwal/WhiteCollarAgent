import json
from datetime import datetime
from typing import Dict, List, Literal, Optional
from core.state.types import AgentProperties, ConversationMessage
from core.state.agent_state import STATE
from core.event_stream.event_stream_manager import EventStreamManager
from core.logger import logger


class StateManager:
    """Manages conversation snapshots, task state, and runtime session data."""

    def __init__(self, event_stream_manager: EventStreamManager):

        # We have two types of state, persistant and session state
        # Persistant state are state that will not be changed frequently,
        # e.g. agent properties
        # Session state are states that is short-termed, one time used
        # e.g. current conversation, conversation state, action state
        self.tasks: Dict[str, dict] = {}
        self.event_stream_manager = event_stream_manager
        self._conversation: List[ConversationMessage] = []

    async def start_session(self, session_id: str = "default", gui_mode: bool = False):

        conversation_state = await self.get_conversation_state()

        logger.debug(f"[SESSION ID]: this is the session id: {session_id}")

        current_task = self.get_current_task_state(session_id)

        logger.debug(f"[CURRENT TASK]: this is the current_task: {current_task}")

        event_stream = self.get_event_stream_snapshot(session_id)

        STATE.refresh(
            session_id=session_id
            conversation_state=conversation_state,
            current_task=current_task,
            event_stream=event_stream,
            gui_mode=gui_mode
        )

    
    def end_session(self):
        """
        End the session, clearing session context so the next user input starts fresh.
        """
        STATE.refresh()

    def clear_conversation_history(self) -> None:
        """Drop all stored conversation messages for the active user."""
        self._conversation.clear()
        self._update_session_conversation_state()

    def reset(self) -> None:
        """Fully reset runtime state, including tasks and session context."""
        self.tasks.clear()
        STATE.agent_properties: AgentProperties = AgentProperties(current_task_id="", action_count=0, token_count=0)
        self.clear_conversation_history()
        if self.event_stream_manager:
            self.event_stream_manager.clear_all()
        self.end_session()
        
    def _format_conversation_state(self) -> str:
        if not self._conversation:
            return ""

        lines: List[str] = []
        for message in self._conversation[-25:]:
            timestamp = message["timestamp"]
            role = message["role"]
            content = message["content"]
            lines.append(f"{timestamp}: {role}: \"{content}\"")

        return "\n".join(lines)

    async def get_conversation_state(self) -> str:
        return self._format_conversation_state()

    def _append_conversation_message(self, role: Literal["user", "agent"], content: str) -> None:
        self._conversation.append(
            {
                "role": role,
                "content": content,
                "timestamp": datetime.utcnow().isoformat(),
            }
        )

    def _update_session_conversation_state(self) -> None:
        STATE.update_conversation_state(self._format_conversation_state())

    def record_user_message(self, content: str) -> None:
        self._append_conversation_message("user", content)
        self._update_session_conversation_state()

    def record_agent_message(self, content: str) -> None:
        self._append_conversation_message("agent", content)
        self._update_session_conversation_state()
    
    def get_current_step(self, session_id: str) -> Optional[dict]:
        wf = self.tasks.get(session_id)
        if not wf:
            return None
        for st in wf["steps"]:
            if st["status"] == "current":
                return st
        for st in wf["steps"]:
            if st["status"] == "pending":
                return st
        return None
    
    def get_event_stream_snapshot(self, session_id: str, *, max_events: int = 60) -> str:
        return self.event_stream_manager.snapshot(session_id, max_events=max_events)
        
    def get_current_task_state(self, session_id: str) -> Optional[str]:
        wf = self.tasks.get(session_id)

        logger.debug(f"[TASK] wf in StateManager: {wf}, session id: {session_id}")

        if wf is None:
            logger.debug("[TASK] task not found in StateManager")
            return None

        # Build minimal per-step representation
        steps_summary: List[Dict[str, str]] = []
        for step in wf['steps']:
            item = {
                "step_index": step['step_index'],
                "step_name": step['step_name'],
                "description": step['description'],
                "action_instruction": step['action_instruction'],
                "validation_instruction": step['validation_instruction'],
                "status": step['status'],
            }
            if step['failure_message']:
                item["failure_message"] = step['failure_message']
            steps_summary.append(item)

        payload = {
            "instruction": wf['instruction'],
            "goal": wf['goal'],
            "inputs_params": wf['inputs_params'],
            "context": wf['context'],
            "steps": steps_summary
        }

        # Return prettified JSON string
        return json.dumps(payload, indent=2)

    def bump_task_state(self, session_id: str) -> None:
        STATE.update_current_task(
                self.get_current_task_state(session_id)
            )
            
    def bump_event_stream(self, session_id: str) -> None:
        STATE.update_event_stream(self.get_event_stream_snapshot(session_id))
            
    async def bump_conversation_state(self) -> None:
        STATE.update_conversation_state(await self.get_conversation_state())

    def is_running_task_with_id(self, session_id: str) -> bool:
        wf = self.tasks.get(session_id)
        if not wf:
            return False
        return True
        
    def is_running_task(self) -> bool:
        if self.tasks:
            return True
        else:
            return False
    
    def add_to_active_task(self, task_id: str, task: dict):
        self.set_active_task(task_id, task)

    # TODO remove duplicate
    def set_active_task(self, task_id: str, task: dict):
        self.tasks[task_id] = task
        self.bump_task_state(task_id)

    def remove_active_task(self, task_id: str) -> None:
        self.tasks.pop(task_id, None)
        STATE.update_current_task(None)
    
    def get_all_task_state(self) -> List[str]:
        pass    

    def set_agent_property(self, key, value):
        """
        Sets a global agent property (not specific to any task).
        """
        STATE.agent_properties.set_property(key, value)

    def get_agent_property(self, key, default=None):
        """
        Retrieves a global agent property.
        """
        return STATE.agent_properties.get_property(key, default)

    def get_agent_properties(self):
        """
        Retrieves all global agent properties.
        """
        return STATE.agent_properties.to_dict()