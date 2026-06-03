import time
from typing import Any, Dict, List, Optional
import threading

class WorkflowTracer:
    """
    A thread-safe singleton workflow tracer that keeps track of the execution
    of LangGraph nodes, agents, and tool calls.
    """
    _instance = None
    _lock = threading.RLock()

    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(WorkflowTracer, cls).__new__(cls)
                cls._instance._traces = {}
        return cls._instance

    def start_run(self, run_id: str, query: str, dataset_name: Optional[str] = None):
        """
        Initialize a new tracing session for a run.
        """
        with self._lock:
            self._traces[run_id] = {
                "run_id": run_id,
                "query": query,
                "dataset_name": dataset_name or "None",
                "start_time": time.time(),
                "end_time": None,
                "duration": None,
                "status": "IN_PROGRESS",
                "steps": []
            }

    def start_step(self, run_id: str, agent_name: str, input_data: Any = None):
        """
        Record the start of an agent/node execution.
        """
        with self._lock:
            if run_id not in self._traces:
                self.start_run(run_id, "Unknown run triggered dynamically")
                
            step = {
                "step_index": len(self._traces[run_id]["steps"]) + 1,
                "agent_name": agent_name,
                "start_time": time.time(),
                "end_time": None,
                "duration": None,
                "input": str(input_data)[:500] if input_data else None,
                "output": None,
                "status": "RUNNING"
            }
            self._traces[run_id]["steps"].append(step)
            return step["step_index"]

    def complete_step(self, run_id: str, agent_name: str, output_data: Any = None, status: str = "SUCCESS"):
        """
        Record the completion of an agent/node execution.
        """
        with self._lock:
            if run_id not in self._traces:
                return
                
            steps = self._traces[run_id]["steps"]
            # Find the running step with this agent name
            for step in reversed(steps):
                if step["agent_name"] == agent_name and step["end_time"] is None:
                    step["end_time"] = time.time()
                    step["duration"] = round(step["end_time"] - step["start_time"], 3)
                    step["output"] = str(output_data)[:1000] if output_data else None
                    step["status"] = status
                    break

    def fail_step(self, run_id: str, agent_name: str, error_message: str):
        """
        Record a step failure.
        """
        self.complete_step(run_id, agent_name, output_data=error_message, status="FAILED")

    def complete_run(self, run_id: str, status: str = "COMPLETED"):
        """
        Complete the entire trace run.
        """
        with self._lock:
            if run_id not in self._traces:
                return
            run = self._traces[run_id]
            run["end_time"] = time.time()
            run["duration"] = round(run["end_time"] - run["start_time"], 3)
            run["status"] = status

    def get_trace(self, run_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve trace logs for a specific run_id.
        """
        with self._lock:
            return self._traces.get(run_id)

    def list_runs(self) -> List[Dict[str, Any]]:
        """
        Get all trace summaries.
        """
        with self._lock:
            return [
                {
                    "run_id": r["run_id"],
                    "query": r["query"],
                    "dataset_name": r["dataset_name"],
                    "duration": r["duration"],
                    "status": r["status"],
                    "steps_count": len(r["steps"]),
                    "start_time": r["start_time"]
                }
                for r in self._traces.values()
            ]

# Singleton instance
tracer = WorkflowTracer()
